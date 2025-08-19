[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)


# Soccer-Match-Analytics
Sports analytics pipeline: CSV → metrics → static HTML report
[Soccer Match Analytics](https://alex-gorman.github.io/Soccer-Match-Analytics/)


## Features
- Ingest multi-tournament CSV; validate & normalize schema.
- Aggregations by opponent, map, home/away, optional tournament and phase.
- Percent columns (P1/P2 goal share).
- Elo engine with --elo-k and --elo-home-adv controls.
- Pre-match win probability shown for each recent game.
- Recent matches card with mini probability bars and Δ (upsets/favored losses highlighted).
- Calibration section: Brier score + reliability bins table (how predicted win% matched reality).
- Opponent scouting (last N) mini table (N defaults to 10).
- Report (Jinja) with KPIs, Opponents, Maps, Home/Away, Tournaments, Stages, Elo & Recent, Calibration, Scouting.
- Artifacts to `out/`:
  - `report.html`
  - `matches.parquet`
  - `summary_opponents.csv`, `summary_maps.csv`, `summary_tournaments.csv`


## What the report shows
- KPIs: games, wins, win%, goal diff, goals per game, P1/P2 goal share.
- Opponents / Maps / Home vs Away / Tournaments / Group Stage vs Knockout: summary tables.
- Elo & Win Probabilities: current rating, recent 10 with pre-match p(win), and upset highlights.
- Calibration: Brier score and reliability bins:
  - Mean p = average predicted win% in the bin.
  - Emp. rate = actual win rate in that bin.
  - Gap = Emp. rate − Mean p (positive = under-confident; negative = over-confident).
- Opponent scouting (last N): count, wins, win%, last result vs each opponent in the recent window.


## Quick start

### Option A — one command (recommended)

```bash
make
```

### Option B — manual

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -e .
soccer --input data/tournament_01.csv --out out/ \
  --use-elo --elo-k 20 --elo-home-adv 50
# macOS:
open out/report.html
```


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



## Project structure
```
src/soccer/
  io_csv.py        # CSV loader & schema validation
  clean.py         # normalization (types, W/L, OT, dates, H/A, phase, goal_diff)
  metrics.py       # aggregations and % columns
  calibration.py   # Brier score + reliability bins
  elo.py           # Elo + p(win)
  report.py        # Jinja render (copies/links static CSS)
  cli.py           # `soccer` entrypoint
templates/
  report.html
  static/styles.css
data/
  tournament_01.csv
```

## Testing
```bash
# run everything
pytest -q

# only unit tests
pytest tests/unit -q

# only integration tests
pytest tests/integration -q

# only smoke tests
pytest tests/smoke -q
```


## Stage 3 Future Work
- Win-prob ML model
- Experiment Tracking
- feature store (DuckDB/Parquet)


## Releases
- [Unreleased](https://github.com/Alex-Gorman/Soccer-Match-Analytics/compare/v0.1.0...HEAD)
- [0.1.0](https://github.com/Alex-Gorman/Soccer-Match-Analytics/releases/tag/v0.1.0)





