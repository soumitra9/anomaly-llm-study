"""Regenerate results/tables/*.csv from results/raw/ (deterministic; PLAN §10).

Aggregates every experiment dir found under results/raw/ (or the ones named on the CLI).
Usage:  uv run python scripts/make_tables.py [exp1_repro exp2_odds ...]
"""
from __future__ import annotations

import sys
from pathlib import Path

from anodet.analysis.aggregate import build

RESULTS = "results"


def main(argv: list[str]) -> int:
    raw = Path(RESULTS) / "raw"
    experiments = argv or sorted(p.name for p in raw.glob("*") if p.is_dir() and p.name != "smoke")
    if not experiments:
        print("no experiment dirs under results/raw/ — nothing to aggregate")
        return 0
    for exp in experiments:
        out = build(RESULTS, exp)
        print(f"[tables] {exp} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
