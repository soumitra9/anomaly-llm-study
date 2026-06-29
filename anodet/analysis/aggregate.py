"""Aggregate per-cell result JSON into tidy tables (the deterministic results/raw/ -> tables step).

Loads `results/raw/<experiment>/*.json` (the system of record), flattens scalar metrics into one row per
cell, and aggregates over seeds -> mean ± std per (dataset, model, mode, metric). Optionally refuses to
build if a grid config is supplied and the grid is incomplete (`grid.assert_grid_complete`), so a published
table can never be built from a partial sweep.
"""
from __future__ import annotations

import glob
from pathlib import Path
from typing import Optional

import pandas as pd

from anodet.utils.io import read_json


def load_rows(results_root: str = "results", experiment: str = "exp1_repro") -> pd.DataFrame:
    """One row per complete cell; scalar metrics flattened to columns (dict-valued metrics dropped)."""
    rows = []
    for p in glob.glob(str(Path(results_root) / "raw" / experiment / "*.json")):
        d = read_json(p)
        if d.get("status") != "complete":
            continue
        rm = d.get("run_metadata", {})
        row = {"dataset": rm.get("dataset"), "model": rm.get("model"),
               "mode": rm.get("mode"), "seed": rm.get("seed")}
        for k, v in d.get("metrics", {}).items():
            if isinstance(v, (int, float)):  # skip nested (e.g. r_sensitivity_auroc)
                row[k] = float(v)
        rows.append(row)
    return pd.DataFrame(rows)


def aggregate(rows: pd.DataFrame) -> pd.DataFrame:
    """Mean ± std over seeds per (dataset, model, mode); columns flattened to <metric>_mean/<metric>_std."""
    if rows.empty:
        return rows
    keys = ["dataset", "model", "mode"]
    metric_cols = [c for c in rows.columns if c not in keys + ["seed"]]
    g = rows.groupby(keys)[metric_cols].agg(["mean", "std"])
    g.columns = [f"{m}_{stat}" for m, stat in g.columns]
    g["n_seeds"] = rows.groupby(keys).size()
    return g.reset_index()


def write_table(df: pd.DataFrame, results_root: str = "results", experiment: str = "exp1_repro") -> Path:
    out = Path(results_root) / "tables" / f"{experiment}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    return out


def build(results_root: str = "results", experiment: str = "exp1_repro",
          config_path: Optional[str] = None) -> Path:
    """Aggregate `experiment` -> results/tables/<experiment>.csv. If config_path given, refuse on incomplete grid."""
    if config_path:
        from anodet.eval import grid
        grid.assert_grid_complete(grid.load_config(config_path), results_root)
    return write_table(aggregate(load_rows(results_root, experiment)), results_root, experiment)
