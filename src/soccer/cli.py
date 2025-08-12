# src/soccer/cli.py
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
    """Compute metrics and build a static HTML report from match CSVs."""
    # Validate paths
    if not input.exists():
        raise typer.BadParameter(f"Input not found: {input}")

    out = Path(out)  # ensure Path
    out.mkdir(parents=True, exist_ok=True)

    # Load → clean → summarize
    raw = load_csv(str(input))
    df = normalize(raw)
    df.to_parquet(out / "matches.parquet")

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

    # Build static report
    build_html_report(df, summary, out / "report.html")
    typer.echo(f"Report written to {out / 'report.html'}")

def run():
    """Console-script entrypoint that lets Typer parse CLI options."""
    typer.run(main)

if __name__ == "__main__":
    run()



