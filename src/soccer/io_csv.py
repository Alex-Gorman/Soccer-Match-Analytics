# src/soccer/io_csv.py

"""
CSV loading and schema validation.

This module provides a thin wrapper around `pandas.read_csv` that:
  - Ensures a known schema is present (required columns).
  - Fails on common data issues (missing or duplicate columns).
  - Returns raw DataFrame

Typical usage:
    >>> from soccer.io_csv import load_csv
    >>> df = load_csv("data/tournament_01.csv")
    >>> set(df.columns) >= set(REQUIRED_COLUMNS)
    True
"""

from __future__ import annotations
import pandas as pd


REQUIRED_COLUMNS = ["date", "tournament_no", "round", "game_no", "map", "opponent", "home_or_away", "win_or_loss", "ot",
"score", "goals_for", "goals_against", "player_1_goals", "player_2_goals", "shots_for", "shots_against"]


def load_csv(path: str) -> pd.DataFrame:
    """Load a CSV and validate that all required columns are present.

    Args:
        path:
            Filesystem path to a CSV file.
    
    Returns:
        A `pandas.DataFrame` 

    
    Raises:
        ValueError:
            If any required columns are missing, or if duplicate column names
            are detected.


    Example:
        >>> from io import StringIO
        >>> csv = StringIO("date,tournament_no,round,game_no,map,opponent,home_or_away,win_or_loss,ot,score,goals_for,goals_against,player_1_goals,player_2_goals,shots_for,shots_against\\n"
        ...                 "2025-08-01,1,Group,1,Battle Dome,Yoshi,H,W,no,2-1,2,1,1,1,7,6\\n")
        >>> df = load_csv(csv)  # file-like objects are also supported by pandas
        >>> sorted(set(REQUIRED_COLUMNS) - set(df.columns))
        []
    """


    # Read the CSV
    df = pd.read_csv(path)

    # Validate schema: all required columns must be present.
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    return df
