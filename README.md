# Soccer-Match-Analytics
Sports analytics pipeline: CSV → metrics → static HTML report

---

## Features (Stage 1)
- Ingest multi-tournament CSV
- Validate & normalize schema
- Compute per-tournament, phase (Group vs Knockout), opponent, and map breakdowns
- Percent columns: P1/P2 goal share per group.
- Artifacts written to `out/`:
  - `report.html`
  - `matches.parquet`
  - `summary_opponents.csv`, `summary_maps.csv`, `summary_tournaments.csv`

---

## Data schema (CSV)

Required header row must match these columns:

| column              | example           | notes                                  |
|---------------------|-------------------|----------------------------------------|
| `date`              | `2025-08-01`      | parsed to datetime                     |
| `tournament_no`     | `1`               | integer id                             |
| `round`             | `Group`/`Semifinal`/`Final` | used to derive phase           |
| `game_no`           | `1..16`           | per-tournament                         |
| `map`               | `Battle Dome`     | string                                 |
| `opponent`          | `Yoshi`           | string                                 |
| `home_or_away`      | `H` / `A` / `home` / `away` | normalized to `H`/`A`          |
| `win_or_loss`       | `W` / `L`         | normalized to `W`/`L`                  |
| `ot`                | `yes`/`no`/`OT`/`0`/`1` | → nullable boolean                |
| `score`             | `3-1`             | display-only                           |
| `goals_for`         | `3`               | Int                                    |
| `goals_against`     | `1`               | Int                                    |
| `player_1_goals`    | `2`               | Int                                    |
| `player_2_goals`    | `1`               | Int                                    |
| `shots_for`         | `10`              | Int                                    |
| `shots_against`     | `7`               | Int                                    |

Derived in the pipeline: `result` (`W`/`L`), `phase` (`Group`/`Knockout`), `goal_diff`.

---

## Quick start

### Option A — one command (recommended)

```bash
make
```

### Option B — manual

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -e .
soccer --input data/tournament_01.csv --out out/
# macOS:
open out/report.html
```

---

## Project structure
```
src/soccer/
  io_csv.py      # CSV loader & schema validation
  clean.py       # normalization (types, W/L, OT, dates, H/A, phase, goal_diff)
  metrics.py     # aggregations and % columns (P1/P2 goal share)
  report.py      # Jinja rendering (+ optional static asset copy)
  cli.py         # `soccer` entrypoint
templates/
  report.html    # template used to render the report
  static/style.css  # (optional) external stylesheet
data/
  tournament_01.csv  # sample dataset
```

---

## Roadmap (Stage 2)
- Elo ratings and pre-match win probabilities
- Opponent scouting pages (recent H2H, best maps, tendencies)
- Calibration (Brier score, reliability curve)
- Optional feature store (DuckDB/Parquet)

## Releases
[Unreleased]: https://github.com/Alex-Gorman/Soccer-Match-Analytics/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Alex-Gorman/Soccer-Match-Analytics/releases/tag/v0.1.0




