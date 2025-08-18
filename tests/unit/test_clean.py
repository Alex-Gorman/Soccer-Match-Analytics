# tests/test_clean.py

"""Unit tests for `clean.normalize` focusing on basic field normalization.

These tests validate that a single-row DataFrame is transformed correctly:
  - `result` becomes "W"/"L" from free-form win/loss strings
  - `ot` becomes a boolean True/False from truthy/falsey inputs
  - `home_or_away` is reduced to "H"/"A"
  - `phase` is derived as "Knockout" for semifinal/final rounds
  - `goal_diff` is computed as goals_for - goals_against

Run all unit tests:
    pytest tests/unit -q
Run only this file:
    pytest tests/unit/test_clean.py -q
"""


import pandas as pd
from soccer.clean import normalize


def test_normalize_basic_1():
    """Semifinal win; truthy OT; home → H; knockout phase; goal diff positive."""

    # ---------- Arrange ----------
    df = pd.DataFrame([{
        "date":"2025-08-01","tournament_no":1,"round":"Semifinal","game_no":1,
        "map":"Battle Dome","opponent":"Yoshi","home_or_away":"home",
        "win_or_loss":"Win","ot":"yes","score":"2-1",
        "goals_for":2,"goals_against":1,"player_1_goals":1,"player_2_goals":1,
        "shots_for":10,"shots_against":7
    }])

    # ---------- Act ----------
    out = normalize(df)
    row = out.iloc[0]

    # ---------- Assert ----------
    assert row["result"] == "W"
    assert row["ot"] == True 
    assert row["home_or_away"] == "H"
    assert row["phase"] == "Knockout"
    assert row["goal_diff"] == 1


def test_normalize_basic_2():
    """Final loss; falsey OT; away → A; knockout phase; goal diff negative."""

    # ---------- Arrange ----------
    df = pd.DataFrame([{
        "date":"2025-08-02","tournament_no":10,"round":"f","game_no":5,
        "map":"Crater Field","opponent":"Mario","home_or_away":"away",
        "win_or_loss":"L","ot":"n","score":"2-1",
        "goals_for":10,"goals_against":12,"player_1_goals":10,"player_2_goals":0,
        "shots_for":20,"shots_against":25
    }])

    # ---------- Act ----------
    out = normalize(df)
    row = out.iloc[0]

    # ---------- Assert ----------
    assert row["result"] == "L"
    assert row["ot"] == False 
    assert row["home_or_away"] == "A"
    assert row["phase"] == "Knockout"
    assert row["goal_diff"] == -2


