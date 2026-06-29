# Deterministic regeneration of tables/figures from results/raw/ (the system of record). PLAN §10.
.PHONY: tables figures test verdict

tables:        ## results/raw/ -> results/tables/*.csv
	uv run python scripts/make_tables.py

figures:       ## results/tables/ + results/raw/ -> results/figures/*
	uv run python scripts/make_figures.py

verdict:       ## judge the M1 reproduction gate against configs/anollm_reference.yaml
	uv run python -m anodet.eval.verdict

test:          ## full pytest suite
	uv run pytest -q
