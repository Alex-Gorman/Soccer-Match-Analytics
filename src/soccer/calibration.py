# src/soccer/calibration.py

"""Calibration utilities: Brier score and reliability (bin) table.

This module exposes two helpers used to evaluate probability forecasts:

- ``brier_score``: mean squared error between predicted probabilities and
  binary outcomes (0/1). Lower is better; perfect calibration + discrimination
  yields 0.0, and a maximally bad constant predictor (e.g., always 1.0 when
  outcomes are 0) approaches 1.0.

- ``reliability_table``: bins probabilities into equal-width buckets across
  [0, 1] and computes, per bucket, the sample size (``n``), the mean predicted
  probability (``mean_p``), the empirical outcome rate (``emp_rate``), and
  their difference (``gap = emp_rate - mean_p``). This is useful for building
  reliability diagrams / calibration tables.

Both functions treat inputs as floats and do not align by index; they operate
positionally. Callers should ensure ``y_true`` and ``p`` correspond row-for-row.
"""


from __future__ import annotations
import numpy as np
import pandas as pd



def brier_score(y_true: pd.Series, p: pd.Series) -> float:
    """Compute the Brier score: mean((p - y)^2).

    Parameters: 
        y_true : pd.Series
            Binary outcomes encoded as 0/1 (truthy values are coerced to float).
        p : pd.Series
            Predicted probabilities for the positive class in [0, 1] (coerced to float).

    Returns:
        float
            The Brier score (mean squared error between ``p`` and ``y_true``).

    Raises:
        ValueError
            If the inputs have different lengths.
    """
    y = y_true.astype(float).to_numpy()
    q = p.astype(float).to_numpy()
    return float(np.mean((q - y) ** 2))



def reliability_table(y_true: pd.Series, p: pd.Series, bins: int = 10) -> pd.DataFrame:
    """Build a reliability (calibration) table over equal-width probability bins.

    The probability range [0, 1] is divided into ``bins`` equal-width intervals.
    Each prediction is assigned to a bin, and per-bin metrics are computed:

    - ``n``:       number of samples in the bin
    - ``mean_p``:  average predicted probability in the bin
    - ``emp_rate``:empirical outcome rate (mean of y) in the bin
    - ``gap``:     ``emp_rate - mean_p`` (positive → under-confident; negative → over-confident)

    Parameters:
        y_true : pd.Series
            Binary outcomes encoded as 0/1 (will be coerced to float).
        p : pd.Series
            Predicted probabilities in [0, 1] (will be coerced to float).
        bins : int, default 10
            Number of equal-width bins to create across [0, 1].

    Returns:
        pd.DataFrame
            A DataFrame with columns ``['bin', 'n', 'mean_p', 'emp_rate', 'gap']``.
            ``bin`` is a pandas ``Interval`` (Categorical with ordered intervals).
            Empty bins are retained (``n == 0``) to make plotting consistent.

    Raises:
        ValueError
            If inputs have different lengths or ``bins < 1``.
    """

    # Equal-width edges across [0, 1].
    edges = np.linspace(0.0, 1.0, bins + 1)

    # Assign each probability to a bin. The first bin includes 0.0.
    bucket = pd.cut(p, edges, include_lowest=True, right=True)

    # Group by the categorical Interval bin. Use observed=False to keep empty bins.
    g = pd.DataFrame({"y": y_true, "p": p, "bin": bucket}).groupby("bin", dropna=False)

    # Aggregate per bin.
    out = g.agg(n=("y", "size"), mean_p=("p", "mean"), emp_rate=("y", "mean")).reset_index()

    # Calibration gap: empirical rate minus mean predicted probability.
    out["gap"] = out["emp_rate"] - out["mean_p"]
    return out
