SHELL := /bin/bash

# Defaults (override like: make INPUT=data/tournament_02.csv OUT=build)
# INPUT ?= data/raw/tournament_01.csv
INPUT ?= data/tournament_01.csv
OUT   ?= out

PY   := .venv/bin/python
PIP  := .venv/bin/pip
CLI  := .venv/bin/soccer

.PHONY: all venv install report open clean

# Run `make` -> build report and open it
all: report open
.DEFAULT_GOAL := all

venv:
	@if [ ! -d .venv ]; then \
		echo "→ Creating venv"; \
		python3 -m venv .venv; \
	fi

install: venv
	@$(PY) -m pip install --upgrade pip
	@$(PY) -m pip install -e .

report: install
	@$(CLI) --input $(INPUT) --out $(OUT)

open:
	@{ command -v open >/dev/null && open $(OUT)/report.html; } \
	 || { command -v xdg-open >/dev/null && xdg-open $(OUT)/report.html; } \
	 || echo "Report at: $(OUT)/report.html"

clean:
	@rm -f $(OUT)/*.html $(OUT)/*.parquet