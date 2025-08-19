# tests/test_calibration.py

"""Unit tests for `calibration.brier_score` and calibration.reliability_table focusing on basic field normalization.

These tests validate:
1. `brier_score` matches a manual mean-squared-error calculation.
2. `reliability_table` returns the expected columns and sensible values:
   - the row counts sum to the sample size
   - mean predicted probabilities are in [0, 1] (or NaN for empty bins)
   - the computed `gap` equals (`emp_rate` - `mean_p`) within tolerance.

Run all unit tests:
    pytest tests/unit -q
Run only this file:
    pytest tests/unit/test_calibration -q
"""


import numpy as np
import pandas as pd
import pytest    
from pytest import approx

from soccer.calibration import brier_score, reliability_table


def test_brier_score_matches_manual():
    """
    Compute Brier score manually and ensure the helper returns the same value.

    Example:
      y  = [1, 0, 1, 0]
      p  = [0.90, 0.80, 0.30, 0.20]
      MSE = mean((p - y)^2)
    """
    
    y = pd.Series([1.0, 0.0, 1.0, 0.0], dtype=float)
    p = pd.Series([0.90, 0.80, 0.30, 0.20], dtype=float)
    manual = float(((p - y) ** 2).mean())
    assert float(brier_score(y, p)) == approx(manual, rel=1e-9)


@pytest.mark.filterwarnings("ignore:.*observed=False is deprecated.*:FutureWarning")
def test_reliability_table_shape_and_columns():
    """
    Basic shape/column and identity checks for the reliability table.

    We pass 6 records across a range of probabilities and ask for 5 bins.
    The function should return a DataFrame with at least these columns:
      - bin:      the probability interval (categorical/Interval)
      - n:        count in the bin
      - mean_p:   average predicted probability in the bin
      - emp_rate: empirical win rate in the bin
      - gap:      emp_rate - mean_p
    """

    y = pd.Series([1, 0, 1, 0, 1, 0], dtype=float)
    p = pd.Series([0.15, 0.25, 0.55, 0.65, 0.85, 0.95], dtype=float)
    tbl = reliability_table(y, p, bins=5)

    # Required columns present
    for col in ["bin", "n", "mean_p", "emp_rate", "gap"]:
        assert col in tbl.columns

    # Row counts sum to the sample size
    assert int(tbl["n"].sum()) == len(y)

    # mean_p should stay within [0, 1]
    assert tbl["mean_p"].between(0, 1).all() or tbl["mean_p"].isna().any()

    # gap = emp_rate - mean_p
    non_na = tbl.dropna(subset=["emp_rate", "mean_p"])
    assert (non_na["gap"] - (non_na["emp_rate"] - non_na["mean_p"])).abs().max() < 1e-12
