# tests/test_smoke.py

"""Smoke tests: fast end-to-end checks for the Stage-1 pipeline and CLI.

These tests verify that:
  1) The in-memory pipeline (normalize → build_summary → build_html_report) can
     render a valid HTML report.
  2) The CLI entrypoint (`main`) accepts file paths, produces artifacts, and
     writes the report without parsing sys.argv.

Run all smoke tests:
    pytest tests/smoke -q
Run only this file:
    pytest tests/smoke/test_smoke.py -q
"""


from pathlib import Path
import pandas as pd
import pytest

from soccer.clean import normalize
from soccer.metrics import build_summary
from soccer.report import build_html_report
from soccer.cli import main

@pytest.mark.smoke
def test_smoke_pipeline(tmp_path: Path):
    """End-to-end smoke test for the in-memory pipeline.

    Uses a minimal DataFrame row that satisfies the schema, then verifies the
    HTML report is written and contains expected text. `tmp_path` is a pytest
    fixture that provides an isolated temp directory for each test run.
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
        "shots_for":7,
        "shots_against":6
    }])

    # ---------- Act ----------
    # Normalize to the trusted schema (types, derived fields, etc.).
    clean = normalize(raw)

    # Compute summary dict (overall KPIs + breakdowns).
    summary = build_summary(clean)

    # Destination for the rendered HTML (inside pytest's temp dir).
    out_html = tmp_path / "report.html"

    # Render the Jinja template with computed metrics to disk.
    build_html_report(clean, summary, out_html)

    # ---------- Assert ----------
    # 1) File was created.
    assert out_html.exists()
    text = out_html.read_text(encoding="utf-8")
    assert "Soccer Analytics — Report" in text
    assert "Games" in text

@pytest.mark.smoke
def test_smoke_cli(tmp_path: Path):
    """Smoke test for the Typer-backed CLI (`main` function).

    Writes a tiny CSV to the temp dir, invokes `main()` with explicit keyword
    args, and asserts that expected artifacts are created.
    """

    # ---------- Arrange ----------
    # tiny CSV input
    csv = tmp_path / "data.csv"
    csv.write_text(
        "date,tournament_no,round,game_no,map,opponent,home_or_away,win_or_loss,ot,score,goals_for,goals_against,player_1_goals,player_2_goals,shots_for,shots_against\n"
        "2025-08-01,1,Group,1,Battle Dome,Yoshi,H,W,no,2-1,2,1,1,1,7,6\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    # ---------- Act ----------
    # call your Typer-backed function directly with kwargs (no arg parsing)
    main(input=csv, out=out_dir, per_tournament=True, split_phase=True)

    # ---------- Assert ----------
    assert (out_dir / "report.html").exists()
    assert (out_dir / "matches.parquet").exists()
