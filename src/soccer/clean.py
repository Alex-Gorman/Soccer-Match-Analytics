# src/soccer/clean.py

"""
Data normalization for match CSVs.

This module converts the raw, sometimes messy CSV into a consistent `pandas.DataFrame`
that the rest of the pipeline can trust.

Input expectations (selected columns):
    - date: ISO date string (e.g., "2025-08-01")
    - tournament_no: int-like
    - round: e.g., "Group", "QF", "Semifinal", "Final"
    - game_no: int-like
    - map: str
    - opponent: str
    - home_or_away: one of {"H","A","Home","Away",...}
    - win_or_loss: e.g., "W","L","Win","Loss"
    - ot: various truthy/falsey representations ("yes","no","OT","1","0",...)
    - score: "x-y" (not used for math, kept for display)
    - goals_for, goals_against, player_1_goals, player_2_goals, shots_for, shots_against: int-like

Post-conditions / invariants set by `normalize`:
    - `result`: "W" or "L" (derived from `win_or_loss`)
    - Numerics are cast to nullable integers (pandas "Int64")
    - `ot`: nullable boolean (True/False/<NA>)
    - `date`: pandas datetime64[ns] (NaT on failure)
    - `home_or_away`: "H" or "A" (others -> <NA>)
    - `phase`: "Group" or "Knockout" (derived from `round`)
    - `goal_diff`: Int64 = goals_for - goals_against

Example:
    >>> import pandas as pd
    >>> from soccer.clean import normalize
    >>> df = pd.DataFrame([{
    ...     "date":"2025-08-01","tournament_no":1,"round":"Semifinal","game_no":1,
    ...     "map":"Battle Dome","opponent":"Yoshi","home_or_away":"home",
    ...     "win_or_loss":"Win","ot":"yes","score":"2-1",
    ...     "goals_for":2,"goals_against":1,"player_1_goals":1,"player_2_goals":1,
    ...     "shots_for":10,"shots_against":7
    ... }])
    >>> out = normalize(df)
    >>> out.loc[0, "result"]
    'W'
    >>> bool(out.loc[0, "ot"])
    True
    >>> out.loc[0, "home_or_away"]
    'H'
"""


from __future__ import annotations
import pandas as pd
from typing import Any, Optional


# Accepted labels for knockout rounds (normalized to uppercase before comparison).
_KNOCKOUT_ROUNDS = {"SF", "SEMIFINAL", "SEMI-FINAL", "FINAL", "F"}


# Sets for normalizing OT values to a nullable boolean.
_TRUE_SET = {"YES", "Y", "1", "OT", "O/T", "T", "TRUE"}
_FALSE_SET = {"NO", "N", "0", "F", "FALSE"}


def _normalize_result(val: Any) -> Optional[str]:
    """Map a free-form win/loss value to 'W' or 'L'.

    Args:
        val: Anything that might encode a win or loss (e.g., "W", "Win", "Loss").

    Returns:
        "W" or "L" if recognizable, else None (so the caller can decide what to do).
    """

    if pd.isna(val):
        return None
    s = str(val).strip().upper()
    if s.startswith("W"):
        return "W"
    if s.startswith("L"):
        return "L"
    return None


def _derive_phase(r: Any) -> str:
    """Return 'Group' for non-knockout rounds, else 'Knockout'.

    Args:
        r: The raw round label.

    Returns:
        "Group" or "Knockout". Missing/unknown rounds default to "Group".
    """
    if pd.isna(r):
        # default to Group stage game if round is missing
        return "Group"
    round = str(r).strip().upper()
    return "Knockout" if round in _KNOCKOUT_ROUNDS else "Group"


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize a raw match dataframe into a consistent schema.

    Args:
        df: Raw matches as read from CSV.

    Returns:
        A copy of `df` with:
            - new/clean columns (`result`, `phase`, `goal_diff`, etc.)
            - numeric columns coerced to pandas nullable integers
            - `ot` as a nullable boolean
            - `date` as datetime64[ns]
    """

    d = df.copy()

    # --- RESULT: W/L, infer from goals if missing ---
    d["result"] = d["win_or_loss"].apply(_normalize_result).astype("string")

    # --- NUMERIC CASTS (nullable Int64 to preserve missing) ---
    int_cols = ["tournament_no", "game_no", "goals_for", "goals_against", "player_1_goals", "player_2_goals", "shots_for", "shots_against"]
    for c in int_cols:
        # Convert text → numbers "5" → 5, if value is invalid, it becomes NaN instead of crashing
        d[c] = pd.to_numeric(d[c], errors="coerce").astype("Int64")
    
    # --- OT -> nullable boolean
    s = d["ot"].astype("string").str.strip().str.upper()
    map_t_or_f = pd.Series(pd.NA, index = d.index, dtype="boolean")
    map_t_or_f[s.isin(_TRUE_SET)] = True
    map_t_or_f[s.isin(_FALSE_SET)] = False
    d["ot"] = map_t_or_f

    # --- DATE ---
    d["date"] = pd.to_datetime(d["date"], errors="coerce") #NaT on failure

    # --- HOME/AWAY -> "H"/"A" ---
    d["home_or_away"] = (
        d["home_or_away"]
        .astype("string").str.strip().str[0].str.upper()
        .map({"H": "H", "A": "A"})
        .astype("string")
    )

    # --- DERIVED FIELDS ---
    d["goal_diff"] = (d["goals_for"].astype("Int64") - d["goals_against"].astype("Int64")).astype("Int64")
    d["phase"] = d["round"].apply(_derive_phase).astype("string")


    return d









