# tests/test_metrics.py

"""Unit tests for `metrics.build_summary`.

Covers:
  - Opponent-level totals and goal-share percentages
  - Safe handling of zero-division for goal share
  - Overall KPIs aggregation
  - Grouped breakdowns (opponents, maps, phases, home/away)

Run all unit tests:
    pytest tests/unit -q
Run this file:
    pytest tests/unit/test_metrics.py -q
"""

import pandas as pd
from soccer.metrics import build_summary
import pytest


def test_goal_share_percentages_and_totals():
    """Opponent aggregation computes totals and p1/p2 goal-share correctly.

    Dataset: two games vs Mario (1 win, 1 loss), total GF=5, GA=4.
    p1 scored 3 of 5 (60%), p2 scored 2 of 5 (40%).
    """

    # ---------- Arrange ----------
    df = pd.DataFrame([
        {"result":"W","opponent":"Mario","map":"Underground","tournament_no":1,
         "goals_for":4,"goals_against":2,"player_1_goals":3,"player_2_goals":1,
         "shots_for":8,"shots_against":6,"home_or_away":"H","date":"2025-08-01"},
        {"result":"L","opponent":"Mario","map":"Underground","tournament_no":1,
         "goals_for":1,"goals_against":2,"player_1_goals":0,"player_2_goals":1,
         "shots_for":5,"shots_against":7,"home_or_away":"A","date":"2025-08-02"},
    ])

    # ---------- Act ----------
    s = build_summary(df)
    opp = s["opponents"]
    row = opp.loc[opp["opponent"]=="Mario"].iloc[0]

    # ---------- Assert ----------
    assert row["games"] == 2
    assert row["wins"] == 1
    assert row["losses"] == 1
    assert row["goals_for"] == 5
    assert row["goals_against"] == 4
    # p1/p2 goal share
    assert abs(row["p1_goal_pct"] - 60.0) < 1e-9
    assert abs(row["p2_goal_pct"] - 40.0) < 1e-9


def test_goal_share_handles_zero_division():
    """When GF=0, goal-share percentages should be 0.0 (not NaN or inf)."""

    # ---------- Arrange ----------
    df = pd.DataFrame([
        {"result":"L","opponent":"Luigi","map":"Battle Dome","tournament_no":1,
         "goals_for":0,"goals_against":1,"player_1_goals":0,"player_2_goals":0,
         "shots_for":3,"shots_against":9,"home_or_away":"H","date":"2025-08-03"},
    ])

    # ---------- Act ----------
    s = build_summary(df)
    row = s["opponents"].loc[s["opponents"]["opponent"]=="Luigi"].iloc[0]
    # no NaN/Inf; both should be 0.0

    # ---------- Assert ----------
    assert float(row["p1_goal_pct"]) == 0.0
    assert float(row["p2_goal_pct"]) == 0.0


@pytest.fixture
def df_small():
    """Small fixture: 4 matches across two opponents/maps/tournaments and phases.

    Layout:
      - vs Mario (Underground), tournament 1: W then L (Group)
      - vs Luigi (Battle Dome), tournament 2: W then L (Knockout)
      - 2 home, 2 away
    """

    return pd.DataFrame([
        # vs Mario (Underground), tourney 1
        {"result":"W","opponent":"Mario","map":"Underground","tournament_no":1,
         "goals_for":3,"goals_against":1,"player_1_goals":2,"player_2_goals":1,
         "shots_for":9,"shots_against":6,"home_or_away":"H","date":"2025-08-01","phase":"Group"},
        {"result":"L","opponent":"Mario","map":"Underground","tournament_no":1,
         "goals_for":0,"goals_against":2,"player_1_goals":0,"player_2_goals":0,
         "shots_for":5,"shots_against":8,"home_or_away":"A","date":"2025-08-02","phase":"Group"},
        # vs Luigi (Battle Dome), tourney 2
        {"result":"W","opponent":"Luigi","map":"Battle Dome","tournament_no":2,
         "goals_for":2,"goals_against":0,"player_1_goals":1,"player_2_goals":1,
         "shots_for":7,"shots_against":4,"home_or_away":"H","date":"2025-08-03","phase":"Knockout"},
        {"result":"L","opponent":"Luigi","map":"Battle Dome","tournament_no":2,
         "goals_for":1,"goals_against":2,"player_1_goals":1,"player_2_goals":0,
         "shots_for":6,"shots_against":7,"home_or_away":"A","date":"2025-08-04","phase":"Knockout"},
    ])


def test_overall_kpis(df_small):
    """Overall KPIs (games, wins/losses, GF/GA, diff, win%, GPG, goal share)."""
    # ---------- Act ----------
    sample_test = build_summary(df_small)
    overall = sample_test["overall"]

    # ---------- Assert ----------
    assert overall["games"] == 4
    assert overall["wins"] == 2
    assert overall["losses"] == 2
    assert overall["goals_for"] == 6
    assert overall["goals_against"] == 5
    assert overall["goal_diff"] == 1
    assert overall["win_pct"] == pytest.approx(0.5, 1e-9)
    assert overall["goals_per_game"] == pytest.approx(1.50, 1e-9)
    assert overall["player_1_goal_share_percentage"] == pytest.approx(66.67, abs=0.05)
    assert overall["player_2_goal_share_percentage"] == pytest.approx(33.33, abs=0.05)


def test_opponents_group_and_goal_share(df_small):
    """Opponent breakdown contains expected columns and sensible values."""

    # ---------- Act ----------
    sample_test = build_summary(df_small)
    opp = sample_test["opponents"]

    # ---------- Assert ----------
    assert not opp.empty
    mario = opp.loc[opp["opponent"] == "Mario"].iloc[0]
    luigi = opp.loc[opp["opponent"] == "Luigi"].iloc[0]

    # Mario: 2 games, 1W/1L, GF=3, GA=3
    assert mario["games"] == 2
    assert mario["wins"] == 1
    assert mario["losses"] == 1
    assert mario["goals_for"] == 3
    assert mario["goals_against"] == 3
    assert mario["win_pct"] == pytest.approx(0.5, 1e-9)
    assert mario["p1_goal_pct"] == pytest.approx(66.7, abs=0.05)
    assert mario["p2_goal_pct"] == pytest.approx(33.3, abs=0.05)

    # Luigi: 2 games, 1W/1L, GF=3, GA=2
    assert luigi["games"] == 2
    assert luigi["wins"] == 1
    assert luigi["losses"] == 1
    assert luigi["goals_for"] == 3
    assert luigi["goals_against"] == 2
    assert luigi["p1_goal_pct"] == pytest.approx(66.7, abs=0.05)
    assert luigi["p2_goal_pct"] == pytest.approx(33.3, abs=0.05)


def test_phases_present_when_column_exists(df_small):
    """Phase breakdown exists and includes both Group and Knockout."""

    # ---------- Act ---------- 
    sample_test = build_summary(df_small)
    phases = sample_test["phases"]

    # ---------- Assert ----------
    assert not phases.empty
    assert set(phases["phase"]) == {"Group", "Knockout"}


def test_maps_and_home_away_groups(df_small):
    """Map and home/away breakdowns exist with expected columns/values."""

    # ---------- Act ---------- 
    sample_test = build_summary(df_small)
    maps = sample_test["maps"]
    ha = sample_test["home_away"]

    # ---------- Assert ----------
    assert not maps.empty and set(maps.columns) >= {
        "map","games","wins","losses","goals_for","goals_against","p1_goal_pct","p2_goal_pct"
    }
    assert not ha.empty and set(ha["home_or_away"]) == {"H", "A"}
    # 2 home + 2 away in our fixture
    counts = ha.set_index("home_or_away")["games"].to_dict()
    assert counts["H"] == 2 and counts["A"] == 2


def _toy_df():
    """Synthetic mini-dataset to exercise Stage-2 code paths.

    Contains 5 matches spanning multiple opponents, maps, home/away flags,
    phases (Group + Knockout), and a pre-match probability column `p_win_pre`.
    This is intentionally small but varied so `build_summary` produces
    tournaments/phases groups, calibration blocks, and scouting output.
    """
    return pd.DataFrame(
        [
            # date, opp, map, H/A, result, gf, ga, p1, p2, t, phase, p
            ("2025-08-01","Luigi","Crater Field","H","W",3,1,2,1,1,"Group",0.65),
            ("2025-08-02","Yoshi","Underground","A","L",1,2,1,0,1,"Group",0.45),
            ("2025-08-03","Luigi","Bowser Stadium","H","W",2,0,1,1,1,"Knockout",0.70),
            ("2025-08-04","DK","Konga Coliseum","A","W",1,0,1,0,2,"Group",0.55),
            ("2025-08-05","Yoshi","Crater Field","H","W",2,1,1,1,2,"Group",0.60),
        ],
        columns=[
            "date","opponent","map","home_or_away","result",
            "goals_for","goals_against","player_1_goals","player_2_goals",
            "tournament_no","phase","p_win_pre",
        ],
    )


@pytest.mark.filterwarnings("ignore:.*observed=False is deprecated.*:FutureWarning")
def test_build_summary_includes_stage2_blocks():
    """Ensure `build_summary` returns all Stage-2 sections and sane values.

    Verifies:
      • Overall KPIs exist and game count matches input size.
      • Grouped tables exist: opponents, maps, home/away, tournaments, phases.
      • Calibration dict includes a Brier score in [0,1] and the requested
        number of reliability bins with expected fields.
      • Scouting list exists with rows containing expected keys.
    The warning filter silences a pandas future warning unrelated to behavior.
    """
    df = _toy_df()
    summary = build_summary(
        df,
        per_tournament=True,
        split_phase=True,
        calibration_bins=5,
        scout_recent=4,
    )

    # Overall exists
    assert summary["overall"]["games"] == len(df)

    # Grouped tables exist
    assert not summary["opponents"].empty
    assert not summary["maps"].empty
    assert not summary["home_away"].empty
    assert not summary["tournaments"].empty
    assert not summary["phases"].empty

    # Calibration present and sane
    cal = summary["calibration"]
    assert isinstance(cal, dict) and "brier" in cal and "bins" in cal
    assert 0.0 <= cal["brier"] <= 1.0
    assert cal["bins_count"] == 5
    assert {"n","mean_p","emp_rate","gap"}.issubset(cal["bins"][0].keys())

    # Scouting present
    scouting = summary["scouting"]
    assert isinstance(scouting, list) and len(scouting) > 0
    # keys in scouting rows
    assert {"opponent","n","wins","last_result","win_pct"}.issubset(scouting[0].keys())



