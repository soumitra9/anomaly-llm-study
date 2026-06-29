"""Regenerate results/figures/* from aggregated tables + results/raw/ (deterministic; PLAN §10).

Best-effort: builds whatever figures the available tables support (e.g. exp2 CD diagram once exp2_odds.csv
exists). Safe to run early — it skips figures whose inputs are not present yet.
Usage:  uv run python scripts/make_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from anodet.analysis.figures import cd_diagram

RESULTS = "results"


def main() -> int:
    figdir = Path(RESULTS) / "figures"
    exp2 = Path(RESULTS) / "tables" / "exp2_odds.csv"
    made = 0
    if exp2.exists():
        df = pd.read_csv(exp2)
        # CD diagram over methods = model x mode, scored by per-dataset auroc_mean
        if {"dataset", "model", "mode", "auroc_mean"} <= set(df.columns):
            df = df.assign(method=df["model"] + ":" + df["mode"])
            pivot = df.pivot_table(index="dataset", columns="method", values="auroc_mean")
            if pivot.shape[1] >= 2 and pivot.shape[0] >= 2:
                out = cd_diagram(pivot.dropna(), str(figdir / "exp2_cd_diagram.png"))
                print(f"[figures] {out}"); made += 1
    if not made:
        print("[figures] no inputs ready yet (run `make tables` after results land)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
