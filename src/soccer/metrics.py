# src/soccer/metrics.py

"""Aggregate match data into overall and grouped summaries.

This module expects a *normalized* DataFrame (e.g., from `clean.normalize`)
with at least these columns:

- result: "W"/"L"
- goals_for, goals_against: int-like
- player_1_goals, player_2_goals: int-like
- opponent, map, tournament_no, phase, home_or_away: grouping keys

Outputs:
- `_summarize(...)` returns a grouped rollup with games, wins/losses, GF/GA,
  GD, win %, and P1/P2 goal share % for each group.
- `build_summary(...)` returns a dict containing:
    - overall KPIs
    - breakdowns by opponent, map, tournament_no, phase, home_or_away
"""


from __future__ import annotations
import pandas as pd
from typing import Dict, Any


# -----------------------
# Simple helpers (counts)
# -----------------------


def _wins(s: pd.Series) -> int:
    """Count wins in a 'result' series.

    Args:
        s: A pandas Series containing values like "W"/"L".

    Returns:
        The number of elements equal to "W".
    """
    return int((s == "W").sum())


def _losses(s: pd.Series) -> int:
    """Count losses in a 'result' series.

    Args:
        s: A pandas Series containing values like "W"/"L".

    Returns:
        The number of elements equal to "L".
    """
    return int((s == "L").sum())


# -----------------------------------
# Grouped Breakdowns (opponent/map/etc.)
# -----------------------------------


def _summarize(g: pd.core.groupby.generic.DataFrameGroupBy) -> pd.DataFrame:
    """Aggregate wins/losses and goal stats for each group.

    Args:
        g: A pandas DataFrameGroupBy (e.g., df.groupby("opponent")).

    Returns:
        A DataFrame with one row per group containing:
            - games, wins, losses
            - goals_for, goals_against
            - player_1_goals, player_2_goals
            - goal_diff (GF - GA), win_pct (wins/games)
            - p1_goal_pct, p2_goal_pct (share of GF attributable to each player)
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

    # Convert to numeric (nullable Float64) so percentage math is safe and precise.
    gf = pd.to_numeric(out["goals_for"], errors="coerce").astype("Float64")
    p1 = pd.to_numeric(out["player_1_goals"], errors="coerce").astype("Float64")
    p2 = pd.to_numeric(out["player_2_goals"], errors="coerce").astype("Float64")


     # Goal share percentages per group; guard against division-by-zero (GF == 0).
    out["p1_goal_pct"] = ((p1 / gf) * 100).where(gf > 0, 0.0).round(1)
    out["p2_goal_pct"] = ((p2 / gf) * 100).where(gf > 0, 0.0).round(1)

    return out


# -------------------------
# Top-level summary builder
# -------------------------


def build_summary(df: pd.DataFrame, per_tournament: bool = True, split_phase: bool = True) -> Dict[str, Any]:
    """Build overall KPIs and grouped breakdowns.

    Args:
        df: Normalized matches DataFrame.
        per_tournament: If True, include breakdown by `tournament_no`.
        split_phase: If True, include breakdown by `phase` (Group/Knockout).

    Returns:
        A dict with:
            - "overall": dict of overall KPIs (games, wins, GF/GA, win %, etc.)
            - "opponents": grouped rollup by opponent (or empty DataFrame)
            - "maps": grouped rollup by map (or empty DataFrame)
            - "tournaments": grouped rollup by tournament_no (optional)
            - "phases": grouped rollup by phase (optional)
            - "home_away": grouped rollup by home_or_away (H/A, with "Unknown" for missing)
    """
    # OVERALL
    overall = {
        "games": int(len(df)),
        "wins": _wins(df["result"]),
        "losses": _losses(df["result"]),
        # Use to_numeric + sum(skipna=True) to handle stray non-numeric/missing.
        "goals_for": int(pd.to_numeric(df["goals_for"], errors="coerce").sum(skipna=True)),
        "goals_against": int(pd.to_numeric(df["goals_against"], errors="coerce").sum(skipna=True)),
        "player_1_goals": int(pd.to_numeric(df["player_1_goals"], errors="coerce").sum(skipna=True)),
        "player_2_goals": int(pd.to_numeric(df["player_2_goals"], errors="coerce").sum(skipna=True))
    }
    overall["goal_diff"] = overall["goals_for"] - overall["goals_against"]
    overall["win_pct"] = round((overall["wins"] / overall["games"]) if overall["games"] else 0.0, 3)
    overall["goals_per_game"] = round((overall["goals_for"] / overall["games"]) if overall["games"] else 0.0, 2)


    # Compute overall player goal share %; guard against GF == 0.
    gf = overall["goals_for"]
    if gf > 0:
        overall["player_1_goal_share_percentage"] = round((overall["player_1_goals"] / gf) * 100, 2)
        overall["player_2_goal_share_percentage"] = round((overall["player_2_goals"] / gf) * 100, 2)
    else:
        overall["player_1_goal_share_percentage"] = 0.0
        overall["player_2_goal_share_percentage"] = 0.0

    # BREAKDOWNS (each may be empty if the grouping column is absent)
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
        # Replace missing H/A with "Unknown" so it doesn't drop from the groupby.
        ha = df["home_or_away"].fillna("Unknown")
        home_away = _summarize(df.assign(home_or_away=ha).groupby("home_or_away"))

    return {
        "overall": overall,
        "opponents": opponents.sort_values("win_pct", ascending=False) if not opponents.empty else opponents,
        "maps": maps.sort_values("win_pct", ascending=False) if not maps.empty else maps,
        "tournaments": tournaments.sort_values("tournament_no") if not tournaments.empty else tournaments,
        "phases": phases,
        "home_away": home_away,
    }
