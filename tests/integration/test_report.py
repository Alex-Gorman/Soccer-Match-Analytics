# tests/test_report.py

"""Integration test: end-to-end render of the HTML report.

This verifies the Stage-1 pipeline can:
  1) normalize a minimal raw match row,
  2) compute summary metrics, and
  3) render an HTML report to disk that contains the expected heading.

Run all integration tests:
    pytest tests/integration -q
Run only this file:
    pytest tests/integration/test_report.py -q
"""

from pathlib import Path
import pandas as pd
from soccer.clean import normalize
from soccer.metrics import build_summary
from soccer.report import build_html_report

def test_report_writes_file(tmp_path: Path):
    """End-to-end smoke of report rendering using a tiny in-memory dataset.

    The `tmp_path` fixture gives an isolated temp directory for this test run.
    Write the output report there and assert it exists and contains the
    report heading text.
    """

    # ---------- Arrange ----------
    # Minimal, single-row dataset that satisfies the required schema.
    raw = pd.DataFrame([{
        "date":"2025-08-01",
        "tournament_no":1,
        "round":"Group",
        "game_no":1,
        "map":"Battle Dome",
        "opponent":"Yoshi",
        "home_or_away":"H",
        "win_or_loss":"W",
        "ot":"no",
        "score":"2-1",
        "goals_for":2,
        "goals_against":1,
        "player_1_goals":1,
        "player_2_goals":1,
        "shots_for":10,
        "shots_against":7
    }])

    # ---------- Act ----------
    # Normalize to the trusted schema (types, derived fields, etc.).
    clean = normalize(raw)

    # Compute summary dict (overall KPIs + breakdowns).
    summary = build_summary(clean)

    # Destination for the rendered HTML (inside pytest's temp dir).
    out_html = tmp_path/"report.html"

    # Render the Jinja template with computed metrics to disk.
    build_html_report(clean, summary, out_html)

    # ---------- Assert ----------
    # 1) File was created.
    assert out_html.exists()

    # 2) It contains the expected heading from the template.
    html = out_html.read_text(encoding="utf-8")
    assert "Soccer Analytics — Report" in html
