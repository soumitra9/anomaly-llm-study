"""Analysis layer: deterministic aggregation, stats, and figures built from results/raw/ only.

`make tables` / `make figures` regenerate every table/figure from the per-cell JSON system of record
(PLAN §10), so committed artifacts are diffable against a fresh regen. No GPU; no external tracker.
"""
