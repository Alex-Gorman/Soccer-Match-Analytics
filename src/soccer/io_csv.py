from __future__ import annotations
import pandas as pd

# Input validation
# Read CSV, checks required columns, and returns a raw DataFrame

REQUIRED_COLUMNS = ["date", "tournament_no", "round", "game_no", "map", "opponent", "home_or_away", "win_or_loss", "ot",
"score", "goals_for", "goals_against", "player_1_goals", "player_2_goals", "shots_for", "shots_against"]

def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return df
