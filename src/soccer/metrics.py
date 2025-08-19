# src/soccer/metrics.py

"""Aggregate match data into overall and grouped summaries.

This module expects a *normalized* DataFrame (e.g., from `clean.normalize`)
with at least these columns:

- result: "W"/"L"
- goals_for, goals_against: int-like
- player_1_goals, player_2_goals: int-like
- opponent, map, tournament_no, phase, home_or_away: grouping keys
- OPTIONAL for Stage 2 features:
  - p_win_pre: float in [0,1] (pre-match win probability)
  - date: sortable (datetime or ISO string) for “recent” windows

Outputs:
- `_summarize(...)` returns grouped rollups.
- `build_summary(...)` returns a dict containing:
    - overall KPIs
    - breakdowns (opponent, map, tournament, phase, home/away)
    - OPTIONAL:
        - elo: {'you': float|None, 'table': DataFrame} when final ratings provided
        - calibration: { brier, bins[...] } if p_win_pre is present
        - scouting: recent-window opponent form table
"""

from __future__ import annotations

from typing import Dict, Any
import pandas as pd

# Optional external helpers (safe to miss)
try:
    from .calibration import brier_score as _ext_brier_score, reliability_table as _ext_reliability_table
except Exception:
    _ext_brier_score = None
    _ext_reliability_table = None


# -----------------------
# Simple helpers (counts)
# -----------------------

def _wins(s: pd.Series) -> int:
    """Count wins in a 'result' series.

    Args:
        s: Series of "W"/"L" values.

    Returns:
        Number of "W" entries (int).
    """
    return int((s == "W").sum())


def _losses(s: pd.Series) -> int:
    """Count losses in a 'result' series.

    Args:
        s: Series of "W"/"L" values.

    Returns:
        Number of "L" entries (int).
    """
    return int((s == "L").sum())


# -----------------------------------
# Grouped Breakdowns (opponent/map/etc.)
# -----------------------------------

def _summarize(g: pd.core.groupby.generic.DataFrameGroupBy) -> pd.DataFrame:
    """Aggregate wins/losses and goal stats for each group.

    Args:
        g: DataFrameGroupBy (e.g., df.groupby("opponent")).

    Returns:
        DataFrame with one row per group containing:
          - games, wins, losses
          - goals_for, goals_against
          - player_1_goals, player_2_goals
          - goal_diff (GF - GA)
          - win_pct (wins / games, rounded to 3)
          - p1_goal_pct / p2_goal_pct (share of GF; 0.0 if GF == 0)
    """
    out = (
        g.agg(
            games=("result", "count"),
            wins=("result", _wins),
            losses=("result", _losses),
            goals_for=("goals_for", "sum"),
            goals_against=("goals_against", "sum"),
            player_1_goals=("player_1_goals", "sum"),
            player_2_goals=("player_2_goals", "sum"),
        )
        .assign(
            goal_diff=lambda x: x["goals_for"] - x["goals_against"],
            win_pct=lambda x: (x["wins"] / x["games"]).round(3).fillna(0.0),
        )
        .reset_index()
    )

    # Percentages as safe numeric (nullable Float64)
    gf = pd.to_numeric(out["goals_for"], errors="coerce").astype("Float64")
    p1 = pd.to_numeric(out["player_1_goals"], errors="coerce").astype("Float64")
    p2 = pd.to_numeric(out["player_2_goals"], errors="coerce").astype("Float64")

    # Goal share %; guard against GF == 0
    out["p1_goal_pct"] = ((p1 / gf) * 100).where(gf > 0, 0.0).round(1)
    out["p2_goal_pct"] = ((p2 / gf) * 100).where(gf > 0, 0.0).round(1)
    return out


# -----------------------
# Stage 2: Scouting helper
# -----------------------

def _scouting_recent(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Build a mini 'opponent scouting' table over the most recent N matches.

    Requires 'opponent' and 'result' columns. If a 'date' column exists,
    the "recent" window is the last N rows after sorting by date; otherwise,
    it's simply the last N rows as-is.

    Aggregates, per opponent:
      - n: matches in window
      - wins: count of "W"
      - win_pct: wins / n
      - last_result: most recent "W"/"L" within window
      - last_date: (optional) most recent date if 'date' is available

    Returns:
        DataFrame sorted by (n desc, win_pct desc). Empty DataFrame if inputs
        are insufficient.
    """
    if df.empty or "opponent" not in df.columns or "result" not in df.columns:
        return pd.DataFrame()

    recent = df.sort_values("date", na_position="last").tail(n) if "date" in df.columns else df.tail(n)

    scout = (
        recent.groupby("opponent", dropna=False)
        .agg(
            n=("result", "size"),
            wins=("result", lambda s: int((s == "W").sum())),
            last_result=("result", "last"),
        )
        .reset_index()
    )
    scout["win_pct"] = (scout["wins"] / scout["n"]).round(3)

    if "date" in recent.columns:
        last_date = recent.groupby("opponent")["date"].max().reset_index(name="last_date")
        scout = scout.merge(last_date, on="opponent", how="left")

    return scout.sort_values(["n", "win_pct"], ascending=[False, False])


# -----------------------
# Stage 2: Calibration helper (fallback)
# -----------------------

def _fallback_brier_and_bins(df: pd.DataFrame, bins: int = 10) -> Dict[str, Any]:
    """Compute Brier score and reliability bins using only pandas.

    This is used when external helpers from `soccer.calibration` cannot be
    imported. If `p_win_pre` or `result` are missing / entirely null, returns
    an empty calibration dict.

    Args:
        df: Matches DataFrame with 'p_win_pre' (0..1) and 'result' ("W"/"L").
        bins: Number of quantile bins for the reliability table.

    Returns:
        Dict with:
          - 'brier': float or None
          - 'bins': list of records with fields ['bin', 'n', 'p_mean', 'win_rate']
    """
    if df.empty or "p_win_pre" not in df.columns or "result" not in df.columns:
        return {"brier": None, "bins": []}

    p = pd.to_numeric(df["p_win_pre"], errors="coerce")
    y = (df["result"] == "W").astype("Float64")

    mask = p.notna() & y.notna()
    if not mask.any():
        return {"brier": None, "bins": []}

    p = p[mask]
    y = y[mask]

    brier = float(((p - y) ** 2).mean())

    # Quantile bins; drop duplicates when too few unique p's
    bins_df = (
        pd.DataFrame({"p": p, "y": y})
        .assign(bin=lambda x: pd.qcut(x["p"], q=bins, duplicates="drop"))
        .groupby("bin", as_index=False)
        .agg(n=("y", "size"), p_mean=("p", "mean"), win_rate=("y", "mean"))
        .assign(p_mean=lambda x: x["p_mean"].round(3),
                win_rate=lambda x: x["win_rate"].round(3))
    )

    return {
        "brier": round(brier, 4),
        "bins": bins_df.to_dict(orient="records"),
    }


# -------------------------
# Top-level summary builder
# -------------------------

def build_summary(
    df: pd.DataFrame,
    per_tournament: bool = True,
    split_phase: bool = True,
    *,
    # Stage 2 knobs
    final_ratings: pd.Series | None = None,
    calibration_bins: int = 10,
    scout_recent: int = 10,
) -> Dict[str, Any]:
    """Build overall KPIs, grouped breakdowns, and Stage 2 blocks.

    The function is resilient to missing optional inputs:
    - If `final_ratings` is provided (Series), an Elo block is added.
    - If `p_win_pre` exists, a calibration block is computed (using external
      helpers when available, otherwise the internal fallback).
    - A small “opponent scouting (last N)” table is always attempted; if
      required columns are missing, it returns an empty list.

    Args:
        df: Normalized matches DataFrame.
        per_tournament: Include breakdown by `tournament_no` if True.
        split_phase: Include breakdown by `phase` (Group/Knockout) if True.
        final_ratings: Optional Series of final Elo ratings by entity name.
        calibration_bins: Number of reliability bins (2..50 typical).
        scout_recent: Window size for the recent scouting table.

    Returns:
        Dict[str, Any] with keys:
          - overall, opponents, maps, tournaments, phases, home_away
          - (optional) elo, calibration, scouting, scout_recent
    """

    # ---- OVERALL ----
    overall = {
        "games": int(len(df)),
        "wins": _wins(df["result"]),
        "losses": _losses(df["result"]),
        "goals_for": int(pd.to_numeric(df["goals_for"], errors="coerce").sum(skipna=True)),
        "goals_against": int(pd.to_numeric(df["goals_against"], errors="coerce").sum(skipna=True)),
        "player_1_goals": int(pd.to_numeric(df["player_1_goals"], errors="coerce").sum(skipna=True)),
        "player_2_goals": int(pd.to_numeric(df["player_2_goals"], errors="coerce").sum(skipna=True)),
    }
    overall["goal_diff"] = overall["goals_for"] - overall["goals_against"]
    overall["win_pct"] = round((overall["wins"] / overall["games"]) if overall["games"] else 0.0, 3)
    overall["goals_per_game"] = round((overall["goals_for"] / overall["games"]) if overall["games"] else 0.0, 2)

    # Player goal share %
    gf = overall["goals_for"]
    if gf > 0:
        overall["player_1_goal_share_percentage"] = round((overall["player_1_goals"] / gf) * 100, 2)
        overall["player_2_goal_share_percentage"] = round((overall["player_2_goals"] / gf) * 100, 2)
    else:
        overall["player_1_goal_share_percentage"] = 0.0
        overall["player_2_goal_share_percentage"] = 0.0

    # ---- BREAKDOWNS ----
    opponents = _summarize(df.groupby("opponent")) if "opponent" in df.columns else pd.DataFrame()
    maps      = _summarize(df.groupby("map"))      if "map"      in df.columns else pd.DataFrame()

    tournaments = pd.DataFrame()
    if per_tournament and "tournament_no" in df.columns:
        tournaments = _summarize(df.groupby("tournament_no"))

    phases = pd.DataFrame()
    if split_phase and "phase" in df.columns:
        phases = _summarize(df.groupby("phase"))

    home_away = pd.DataFrame()
    if "home_or_away" in df.columns:
        ha = df["home_or_away"].fillna("Unknown")
        home_away = _summarize(df.assign(home_or_away=ha).groupby("home_or_away"))

    result: Dict[str, Any] = {
        "overall": overall,
        "opponents": opponents.sort_values("win_pct", ascending=False) if not opponents.empty else opponents,
        "maps": maps.sort_values("win_pct", ascending=False) if not maps.empty else maps,
        "tournaments": tournaments.sort_values("tournament_no") if not tournaments.empty else tournaments,
        "phases": phases,
        "home_away": home_away,
    }

    # ---- Stage 2: Elo block (if provided) ----
    if isinstance(final_ratings, pd.Series) and not final_ratings.empty:
        elo_table = (
            final_ratings.reset_index()
            .rename(columns={"index": "entity", final_ratings.name or 0: "rating"})
            .sort_values("rating", ascending=False)
        )
        current = float(final_ratings.get("team_player")) if "team_player" in final_ratings.index else None
        result["elo"] = {
            "you": round(current, 1) if current is not None else None,
            "table": elo_table,
        }

    # ---- Stage 2: Calibration ----
    calibration: Dict[str, Any] = {"brier": None, "bins": []}
    if "p_win_pre" in df.columns and "result" in df.columns and not df.empty:
        if _ext_brier_score is not None and _ext_reliability_table is not None:
            # Use external helpers if available
            y = (df["result"] == "W").astype(float)
            p = pd.to_numeric(df["p_win_pre"], errors="coerce")
            mask = p.notna() & y.notna()
            if mask.any():
                brier = float(_ext_brier_score(y[mask], p[mask]))
                bins_df = _ext_reliability_table(y[mask], p[mask], bins=int(calibration_bins))
                calibration = {
                    "brier": round(brier, 4),
                    "bins": bins_df.to_dict(orient="records"),
                    "bins_count": int(calibration_bins),
                }
        else:
            # Fallback implementation
            fb = _fallback_brier_and_bins(df, bins=int(calibration_bins))
            if fb["brier"] is not None:
                calibration = {"brier": fb["brier"], "bins": fb["bins"], "bins_count": int(calibration_bins)}
    result["calibration"] = calibration

    # ---- Stage 2: Opponent scouting (recent window) ----
    scouting_df = _scouting_recent(df, n=int(scout_recent))
    result["scouting"] = scouting_df.to_dict(orient="records") if not scouting_df.empty else []
    result["scout_recent"] = int(scout_recent)

    return result
