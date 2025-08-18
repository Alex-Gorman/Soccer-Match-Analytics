# src/soccer/cli.py


"""Command-line entrypoints for the Soccer Analytics pipeline.

This CLI wires together Stage-1 steps:
  1) Load raw CSV(s) → `io_csv.load_csv`
  2) Normalize into a clean schema → `clean.normalize`
  3) Compute rollups/metrics → `metrics.build_summary`
  4) Persist artifacts (Parquet + CSV summaries)
  5) Render static HTML report → `report.build_html_report`

Usage (examples):
    soccer --input data/tournament_01.csv --out out/
    soccer -i data/tournament_01.csv -o out/ --no-per-tournament --split-phase
"""


from __future__ import annotations
from pathlib import Path
import pandas as pd
import typer

from .io_csv import load_csv
from .clean import normalize
from .metrics import build_summary
from .report import build_html_report

def main(
    input: Path = typer.Option(..., "--input", "-i", help="Path to CSV file (or folder of CSVs)"),
    out: Path = typer.Option(Path("out"), "--out", "-o", help="Output directory"),
    per_tournament: bool = typer.Option(True, "--per-tournament/--no-per-tournament"),
    split_phase: bool = typer.Option(True, "--split-phase/--no-split-phase"),
):
    """Compute metrics and build a static HTML report from match CSVs.

    Orchestrates the end-to-end Stage-1 pipeline:
      • Validates the input path and prepares the output directory
      • Loads raw CSV data
      • Normalizes/cleans the DataFrame into a trusted schema
      • Builds summary metrics and optional breakdowns
      • Writes machine-readable artifacts (Parquet + CSVs)
      • Renders a static HTML report

    Args:
        input: Filesystem path to the source CSV (or folder; current implementation
            expects a single CSV path).
        out: Output directory where artifacts are written (created if missing).
        per_tournament: If True, include a tournament-level breakdown table.
        split_phase: If True, include a Group vs. Knockout breakdown table.

    Raises:
        typer.BadParameter: If the input path does not exist.
    """

    # --- Validate paths / prepare output ---
    if not input.exists():
        # Fail fast with actionable message if the input path is wrong.
        raise typer.BadParameter(f"Input not found: {input}")

    out = Path(out)  # ensure Path
    out.mkdir(parents=True, exist_ok=True)

    # --- Load → clean → compute metrics ---
    # Read raw CSV; basic schema validation happens inside load_csv.
    raw = load_csv(str(input))

    # Normalize into a consistent schema (types, booleans, derived fields, etc.).
    df = normalize(raw)

    # Persist the cleaned matches for later analysis / debugging.
    df.to_parquet(out / "matches.parquet")

    # Build summary dict with overall KPIs and optional breakdowns.
    summary = build_summary(df, per_tournament=per_tournament, split_phase=split_phase)

    # Save some rollups (guard in case any are empty)
    opp = summary.get("opponents", pd.DataFrame())
    if hasattr(opp, "to_csv") and not getattr(opp, "empty", True):
        opp.to_csv(out / "summary_opponents.csv", index=False)

    maps = summary.get("maps", pd.DataFrame())
    if hasattr(maps, "to_csv") and not getattr(maps, "empty", True):
        maps.to_csv(out / "summary_maps.csv", index=False)

    tourn = summary.get("tournaments", pd.DataFrame())
    if hasattr(tourn, "to_csv") and not getattr(tourn, "empty", True):
        tourn.to_csv(out / "summary_tournaments.csv", index=False)

    # --- Render the static HTML report ---
    build_html_report(df, summary, out / "report.html")
    typer.echo(f"Report written to {out / 'report.html'}")


def run():
    """Console-script entrypoint that lets Typer parse CLI options."""
    typer.run(main)

if __name__ == "__main__":
    run()



