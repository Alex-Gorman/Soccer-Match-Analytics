# src/soccer/elo.py

"""
Elo rating utilities for Soccer-Match-Analytics.

This module provides:
- `expected(rating_a, rating_b)`: pre-match win probability for A vs B (0..1).
- `update(ra, rb, score_a, k)`: single Elo update step; returns new ratings.
- `run_elo(df, k=20, base=1500, home_adv=50)`: walk the match log and
  compute match-by-match Elo for the focal 'team_player' against opponents.

Assumptions
----------
- Unseen players start at `base` rating.
- Home advantage is applied *only* to the effective ratings used for the
  expected-score calculation; stored ratings never include home-advantage.

Outputs
-------
`run_elo` adds these columns to the returned DataFrame:
- `elo_pre`: your rating (without home-advantage) before each match
- `elo_post`: your rating (without home-advantage) after each match
- `p_win_pre`: your pre-match win probability (0..1) given home/away

Example
-------
>>> df2, final = run_elo(df)
>>> df2[['elo_pre', 'elo_post', 'p_win_pre']].head()
>>> final.head()  # final ratings for you + opponents (descending)
"""


from __future__ import annotations
from typing import Tuple, Dict
import pandas as pd


def expected(rating_a: float, rating_b: float) -> float:
    """Return Elo expected score for A vs B (in [0, 1]).

    Uses the standard Elo logistic curve:
        E_A = 1 / (1 + 10 ** ((B - A) / 400))

    Args:
        rating_a: Rating of player/team A.
        rating_b: Rating of player/team B.

    Returns:
        Probability (0..1) that A wins.

    Example:
        >>> round(expected(1600, 1500), 3)
        0.640
    """
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def update(ra: float, rb: float, score_a: float, k: float) -> Tuple[float, float]:
    """Perform a single Elo update for players A and B.

    The update is symmetric and conserves the total rating when K is the same
    for both sides:
        ra' = ra + K * (S_A - E_A)
        rb' = rb + K * (S_B - E_B)  with S_B = 1 - S_A and E_B = 1 - E_A

    Args:
        ra: Current rating for A (effective rating if using home-advantage).
        rb: Current rating for B (effective rating if using home-advantage).
        score_a: Actual result for A (1.0 win, 0.0 loss; ties would be 0.5).
        k: K-factor (update step size).

    Returns:
        (ra_new, rb_new): Updated ratings after the match.
    """
    expected_score_team_a = expected(ra, rb)
    expected_score_team_b = 1.0 - expected_score_team_a
    ra2 = ra + k * (score_a - expected_score_team_a)
    rb2 = rb + k * ((1.0 - score_a) - expected_score_team_b)
    return ra2, rb2


def run_elo(df: pd.DataFrame, k: float = 20.0, base: float = 1500.0, home_adv: float = 50.0, mov: str = "none", mov_alpha: float = 0.5) -> tuple[pd.DataFrame, pd.Series]:
    """Compute Elo for the focal 'team_player' across the match log.

    The function iterates chronologically over `df`, keeping a rating for the
    focal 'team_player' and for each named opponent. For pre-match probability
    we temporarily apply `home_adv` to the *effective* ratings, compute
    expectation, perform the update on those effective ratings, then strip the
    advantage back out when storing updated ratings. Stored ratings are always
    “pure” (no home advantage baked in).

    Args:
        df: Match log with at least columns:
            ['date', 'tournament_no', 'game_no', 'opponent',
             'home_or_away', 'result'].
        k: Elo K-factor (typical range 10–40).
        base: Starting rating for unseen players.
        home_adv: Home-advantage value added to the home side’s *effective*
                  rating for expectation + update (removed before storing).

    Returns:
        (df_with_columns, final_ratings):
            df_with_columns: Original `df` with 3 added columns:
              - 'elo_pre'  (your rating before each match; no home-advantage)
              - 'elo_post' (your rating after each match;  no home-advantage)
              - 'p_win_pre' (pre-match win probability 0..1 given home/away)
            final_ratings: pd.Series of final ratings for 'team_player' and
              each opponent, sorted descending.

    Notes:
        - If you later need draws, pass score_a=0.5 where appropriate.
        - `p_win_pre` is rounded to 3 decimals for display; remove `round(...)`
          if you prefer full precision.
    """
    d = df.copy()

    d = d.sort_values(["date", "tournament_no", "game_no"], na_position="last").reset_index(drop=True)

    # Current ratings for team_player and each opponent (stored WITHOUT any home-advantage).
    ratings: Dict[str, float] = {} 

    # Per-row outputs.
    pre, post, pwin = [], [], []

    for _, row in d.iterrows():
        opp = str(row["opponent"])

        # Stored ratings (no home-adv baked in) 
        r_team_player = ratings.get("team_player", base)
        r_opp = ratings.get(opp, base)

        # Apply home-advantage to EFFECTIVE ratings for the probability/update.
        hoa = str(row.get("home_or_away", "")).upper()
        if hoa.startswith("H"):
            r_team_player_eff = r_team_player + home_adv
            r_opp_eff = r_opp
        elif hoa.startswith("A"):
            r_team_player_eff = r_team_player
            r_opp_eff = r_opp + home_adv
        else:
            # Neutral / unknown – no adjustment.
            r_team_player_eff = r_team_player
            r_opp_eff = r_opp


         # Pre-match expectation and record it.
        expected_score_team_player = expected(r_team_player_eff, r_opp_eff)
        pre.append(r_team_player)
        pwin.append(round(expected_score_team_player, 3))

        # Actual result as 1.0/0.0
        score_a = 1.0 if row["result"] == "W" else 0.0


        # Margin of Victory scaling factor g
        if mov == "simple":
            mov_goals = abs(int(row.get("goals_for", 0)) - int(row.get("goals_against", 0)))
            dr = abs(r_team_player_eff - r_opp_eff)
            g = (0.0 if mov_goals == 0 else math.log(mov_goals + 1.0)) * (2.2 / (0.001 * dr + 2.2))
        else:
            g = 1.0

        # scale the update by g
        delta = k * g * (score_a - expected_score_team_player)
        r_team_player_new_eff = r_team_player_eff + delta
        r_opp_new_eff = r_opp_eff - delta


        # Update on EFFECTIVE ratings, then remove home-adv when storing back
        r_team_player_new_eff, r_opp_new_eff = update(r_team_player_eff, r_opp_eff, score_a, k)

        # Initialization
        r_team_player_new, r_opp_new = 0, 0


        if hoa.startswith("H"):
            r_team_player_new = r_team_player_new_eff - home_adv
            r_opp_new = r_opp_new_eff
        elif hoa.startswith("A"):
            r_team_player_new = r_team_player_new_eff
            r_opp_new = r_opp_new_eff - home_adv
        else:
            # Neutral / unknown – no adjustment.
            r_team_player_new = r_team_player_new_eff
            r_opp_new = r_opp_new_eff


        # Persist updated pure ratings and record post value for you.
        ratings["team_player"] = r_team_player_new
        ratings[opp] = r_opp_new
        post.append(r_team_player_new)

    # Attach outputs.
    d["elo_pre"] = pre
    d["elo_post"] = post
    d["p_win_pre"] = pwin  # 0..1

    # Final ratings for you + all opponents (descending).
    return d, pd.Series(ratings, name="final_ratings").sort_values(ascending=False)
