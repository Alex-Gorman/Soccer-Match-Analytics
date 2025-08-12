from __future__ import annotations
import pandas as pd
from typing import Dict, Any

# Stats/aggregations

def _wins(s: pd.Series) -> int:
    return int((s == "W").sum())

def _losses(s: pd.Series) -> int:
    return int((s == "L").sum())

def _summarize(g: pd.core.groupby.generic.DataFrameGroupBy) -> pd.DataFrame:
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

    # Safe % helpers: denom=0 or NA → 0.0%
    denom = out["goals_for"].replace({0: pd.NA})
    out["p1_goal_pct"] = (out["player_1_goals"].div(denom).mul(100)).round(1).fillna(0.0)
    out["p2_goal_pct"] = (out["player_2_goals"].div(denom).mul(100)).round(1).fillna(0.0)

    return out


def build_summary(df: pd.DataFrame, per_tournament: bool = True, split_phase: bool = True) -> Dict[str, Any]:
    # OVERALL
    overall = {
        "games": int(len(df)),
        "wins": _wins(df["result"]),
        "losses": _losses(df["result"]),
        "goals_for": int(pd.to_numeric(df["goals_for"], errors="coerce").sum(skipna=True)),
        "goals_against": int(pd.to_numeric(df["goals_against"], errors="coerce").sum(skipna=True)),
        "player_1_goals": int(pd.to_numeric(df["player_1_goals"], errors="coerce").sum(skipna=True)),
        "player_2_goals": int(pd.to_numeric(df["player_2_goals"], errors="coerce").sum(skipna=True))
    }
    overall["goal_diff"] = overall["goals_for"] - overall["goals_against"]
    overall["win_pct"] = round((overall["wins"] / overall["games"]) if overall["games"] else 0.0, 3)
    overall["goals_per_game"] = round((overall["goals_for"] / overall["games"]) if overall["games"] else 0.0, 2)
    overall["player_1_goal_share_percentage"] = round((overall["player_1_goals"] / overall["goals_for"] * 100), 2)
    overall["player_2_goal_share_percentage"] = round((overall["player_2_goals"] / overall["goals_for"] * 100), 2)

    # BREAKDOWNS
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

    return {
        "overall": overall,
        "opponents": opponents.sort_values("win_pct", ascending=False) if not opponents.empty else opponents,
        "maps": maps.sort_values("win_pct", ascending=False) if not maps.empty else maps,
        "tournaments": tournaments.sort_values("tournament_no") if not tournaments.empty else tournaments,
        "phases": phases,
        "home_away": home_away,
    }
