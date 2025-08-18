# tests/unit/test_elo.py

"""Unit tests for `elo.expected` & `elo.run_elo`.

Covers:
  - Elo expected score for A vs B
  - Compute elo per match for team_player vs each opponent


This verifies:
    1) `expected()`: With equal ratings, each side should have a 0.5 expected score.
    2) `run_elo()`: Adds the expected per-match columns and returns a final rating
    for the focal "team_player".

Run all unit tests:
    pytest tests/unit -q
Run this file:
    pytest tests/unit/test_elo.py -q
"""


import pandas as pd
from soccer.elo import expected, run_elo


def test_expected_symmetry():
    """Equal ratings should produce a 0.5 expected score for A."""
    assert expected(1500, 1500) == 0.5


def test_run_elo_adds_columns():
    """Smoke test: `run_elo` augments the frame and returns final ratings.

    Asserts that:
      - Per-row columns 'elo_pre', 'elo_post', 'p_win_pre' are added.
      - The returned ratings include an entry for 'team_player'.
    """

    # ---------- Arrange ----------
    # Minimal single-row dataset that satisfies the expected schema.
    df = pd.DataFrame([
        {"date":"2025-08-01","tournament_no":1,"round":"Group","game_no":1,
         "map":"Battle Dome","opponent":"Yoshi","home_or_away":"H",
         "win_or_loss":"W","ot":"no","score":"2-1",
         "goals_for":2,"goals_against":1,"player_1_goals":1,"player_2_goals":1,
         "shots_for":7,"shots_against":6,"result":"W"}
    ])

    # ---------- Act ----------
    # Small K and a modest home advantage are fine for a smoke test.
    out, ratings = run_elo(df, k=20, base=1500, home_adv=50)

    # ---------- Assert ----------
    # 1) New columns were added.
    for col in ["elo_pre","elo_post","p_win_pre"]:
        assert col in out.columns

    # 2) Final ratings include the focal player.
    assert "team_player" in ratings.index
