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
from typing import Annotated
import typer

from .io_csv import load_csv
from .clean import normalize
from .metrics import build_summary
from .report import build_html_report

from .elo import run_elo


def main(
    input: Annotated[Path, typer.Option(help="CSV input", exists=True, dir_okay=False, path_type=Path)],
    out: Annotated[Path, typer.Option(help="Output dir", file_okay=False, dir_okay=True)] = Path("out"),
    per_tournament: Annotated[bool, typer.Option(help="Breakdown per tournament")] = False,
    split_phase: Annotated[bool, typer.Option(help="Split group/knockout")] = False,
    use_elo: Annotated[bool, typer.Option(help="Compute Elo ratings")] = True,
    elo_k: Annotated[float, typer.Option(help="Elo K-factor")] = 20.0,
    elo_home_adv: Annotated[float, typer.Option(help="Home-advantage points")] = 50.0,
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

    # Stage 2 — add Elo columns and final ratings
    final_ratings = None
    if use_elo:
        df, final_ratings = run_elo(df, k=elo_k, base=1500.0, home_adv=elo_home_adv)
        if final_ratings is not None:
            final_ratings.to_csv(out / "ratings.csv", header=["rating"])

    # Persist the cleaned matches for later analysis / debugging.
    df.to_parquet(out / "matches.parquet")

    # Build summary dict with overall KPIs and optional breakdowns.
    summary = build_summary(df, per_tournament=per_tournament, split_phase=split_phase)

    # pass small Elo block to the template
    if final_ratings is not None:
        summary["elo"] = {
            "team_player": round(float(final_ratings.get("you", 1500.0)), 1),
            "table": final_ratings.reset_index().rename(columns={"index": "entity", "final_ratings": "rating"}).to_dict(orient="records"),
        }
    
    # Prepare a “recent matches” section for the template, take the 10 most recent rows
    recent = (
        df.sort_values(["date", "tournament_no", "game_no"])
        .tail(10)
        .copy()
    )

    # display date with format YYYY-MM-DD
    recent["date_str"] = recent["date"].dt.strftime("%Y-%m-%d")

    # numeric result (1 for W, 0 for L; tweak if you ever have draws)
    recent["result_num"] = (recent["result"] == "W").astype(float)

    # delta = result - p(win)
    recent["delta"] = recent["result_num"] - recent["p_win_pre"].astype(float)

    # upset flags
    recent["favored_loss"] = (recent["result"] == "L") & (recent["p_win_pre"] > 0.5)
    recent["underdog_win"] = (recent["result"] == "W") & (recent["p_win_pre"] < 0.5)

    recent["p_win_pre"] = pd.to_numeric(recent["p_win_pre"], errors="coerce").fillna(0.0).clip(0, 1)
    recent["p_win_pct"] = (recent["p_win_pre"] * 100).round().astype(int)

    # keep whatever fields you already render + the new ones
    keep_cols = [
        "date_str","opponent","home_or_away","result",
        "p_win_pre","delta","favored_loss","underdog_win",
        "map","score","ot","goals_for","goals_against",
    ]

    summary["recent"] = recent[keep_cols].to_dict("records")
    
    wins = int(recent["result_num"].sum())
    n = len(recent)
    summary_line = {
        "n": n,
        "wins": wins,
        "losses": n - wins,
        "avg_p": float(recent["p_win_pre"].mean()),
        "exp_wins": float(recent["p_win_pre"].sum()),
        "over_under": float(wins - recent["p_win_pre"].sum()),
    }
    summary.setdefault("elo", {})["recent_summary"] = summary_line



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



