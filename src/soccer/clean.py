from __future__ import annotations
import pandas as pd
from typing import Any, Optional

# Normalization

"""
Normalize the raw CSV into a clean DataFrame the rest of the pipeline can trust
- result: "W"/"L"
- numeric columns: cast to nullable integers (Int64)
- ot: normalize to nullable boolean (True/False/<NA>)
- date: to datetime (NaT on failure)
- home_or_away: "H"/"A"
- phase: "Group" vs "Knockout" (derived from round)
- goal_diff: goals_for - goals_against
"""

_KNOCKOUT_ROUNDS = {"SF", "SEMIFINAL", "SEMI-FINAL", "FINAL", "F"}
_TRUE_SET = {"YES", "Y", "1", "OT", "O/T", "T", "TRUE"}
_FALSE_SET = {"NO", "N", "0", "F", "FALSE"}

def _normalize_result(val: Any) -> Optional[str]:
    """Return 'W' or 'L' if win_or_loss looks like "win" or "loss"; else None"""
    if pd.isna(val):
        return None
    s = str(val).strip().upper()
    if s.startswith("W"):
        return "W"
    if s.startswith("L"):
        return "L"
    return None

def _derive_phase(r: Any) -> str:
    """Map round to 'Group' or 'Knockout'"""
    if pd.isna(r):
        # default to Group stage game if round is missing
        return "Group"
    round = str(r).strip().upper()
    return "Knockout" if round in _KNOCKOUT_ROUNDS else "Group"

def normalize(df: pd.DataFrame) -> pd.DataFrame:
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

# from __future__ import annotations
# import pandas as pd
# from typing import Any, Optional

# """
# Normalize raw CSV into a clean DataFrame the rest of the pipeline can trust.
# - result: "W"/"L" (infer from goals if missing)
# - numeric columns: cast to nullable integers (Int64)
# - ot: normalize to nullable boolean (True/False/<NA>)
# - date: to datetime (NaT on failure)
# - home_or_away: "H"/"A"
# - phase: "Group" vs "Knockout" (derived from round)
# - goal_diff: goals_for - goals_against
# """

# # Accept both long/short labels for knockout rounds
# _KNOCKOUT_ROUNDS = {
#     "QF", "QUARTERFINAL",
#     "SF", "SEMIFINAL", "SEMI-FINAL",
#     "F", "FINAL",
# }

# _TRUE_SET  = {"Y", "YES", "OT", "O/T", "1", "TRUE", "T"}
# _FALSE_SET = {"N", "NO", "0", "FALSE", "F"}

# def _normalize_result(val: Any) -> Optional[str]:
#     """Return 'W' or 'L' if win_or_loss looks like win/loss; else None."""
#     if pd.isna(val):
#         return None
#     s = str(val).strip().upper()
#     if s.startswith("W"):
#         return "W"
#     if s.startswith("L"):
#         return "L"
#     return None

# def _derive_phase(r: Any) -> str:
#     """Map round to 'Group' or 'Knockout'."""
#     if pd.isna(r):
#         return "Group"
#     base = str(r).strip().upper()
#     return "Knockout" if base in _KNOCKOUT_ROUNDS else "Group"

# def normalize(df: pd.DataFrame) -> pd.DataFrame:
#     d = df.copy()

#     # --- RESULT: W/L, infer from goals if missing ---
#     d["result"] = d["win_or_loss"].apply(_normalize_result).astype("string")
#     mask = d["result"].isna()
#     if mask.any():
#         # Only infer where both scores are present
#         gf = pd.to_numeric(d.loc[mask, "goals_for"], errors="coerce")
#         ga = pd.to_numeric(d.loc[mask, "goals_against"], errors="coerce")
#         # three-way: W/L/<NA> (if either score missing)
#         inferred = pd.Series(pd.NA, index=gf.index, dtype="string")
#         inferred[gf > ga] = "W"
#         inferred[gf < ga] = "L"
#         d.loc[mask, "result"] = inferred

#     # --- NUMERIC CASTS (nullable Int64 to preserve missing) ---
#     int_cols = [
#         "tournament_no", "game_no",
#         "goals_for", "goals_against",
#         "player_1_goals", "player_2_goals",
#         "shots_for", "shots_against",
#     ]
#     for c in int_cols:
#         d[c] = pd.to_numeric(d[c], errors="coerce").astype("Int64")

#     # --- OT -> nullable boolean ---
#     s = d["ot"].astype("string").str.strip().str.upper()
#     # Map known truthy/falsey, keep others as <NA>
#     mapped = pd.Series(pd.NA, index=d.index, dtype="boolean")
#     mapped[s.isin(_TRUE_SET)] = True
#     mapped[s.isin(_FALSE_SET)] = False
#     d["ot"] = mapped

#     # --- DATE ---
#     d["date"] = pd.to_datetime(d["date"], errors="coerce")  # NaT on failure

#     # --- HOME/AWAY -> "H"/"A" ---
#     d["home_or_away"] = (
#         d["home_or_away"]
#         .astype("string").str.strip().str[0].str.upper()
#         .map({"H": "H", "A": "A"})
#         .astype("string")
#     )

#     # --- DERIVED FIELDS ---
#     d["goal_diff"] = (d["goals_for"].astype("Int64") - d["goals_against"].astype("Int64")).astype("Int64")
#     d["phase"] = d["round"].apply(_derive_phase).astype("string")

#     return d








