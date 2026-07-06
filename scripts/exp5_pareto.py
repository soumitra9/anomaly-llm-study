"""Exp 5 — Practicality / Pareto analysis (RQ6).

No new GPU runs. Reads wall_seconds from M4 result JSONs (exp4 + exp6), uses RUNLOG-derived
averages for prior experiments (M1/M2/M3), and builds a Pareto table (AUROC vs cost/time).

Usage:
    uv run python scripts/exp5_pareto.py [--results-root results] [--output-dir results]

Outputs:
    results/tables/exp5_pareto.csv   -- one row per (experiment, model, mode, dataset_group)
    results/figures/exp5_pareto.png  -- Pareto scatter (wall_seconds/1k rows vs mean AUROC)

Timing coverage:
    M4 cells (exp4, exp6): wall_seconds read from JSON extra field (structured, per-cell).
    M1/M2/M3 cells: approximated from RUNLOG.md pod-uptime / n_cells (hardcoded below).
    Limitation: M1-M3 timing is pod-level average, not per-cell; noted in paper.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# RUNLOG-derived timing estimates for M1/M2/M3 (pod_uptime / n_cells).
# These are documented in RUNLOG.md and approximate; only M4 cells have
# per-cell wall_seconds. Update these constants after each major campaign.
# ---------------------------------------------------------------------------
_RUNLOG_TIMING = {
    # (experiment, mode): avg_wall_seconds_per_1k_rows
    # M1 — SmolLM-360M likelihood, 90 cells (30 datasets x 3 seeds)
    # Pod uptime ~13h, 90 cells, ~900 avg rows/dataset => ~52s/cell / 0.9 => ~58s/1k rows
    ("exp1_smol", "likelihood"): 58.0,
    # M2 — exp2_odds: SmolLM + Qwen2.5-3B x {likelihood, prompted}, 360 cells
    # Pod uptime ~20h, 360 cells => ~200s/cell; avg ~900 rows => ~222s/1k rows for likelihood
    # Prompted is faster (~30s/cell for 900 rows => ~33s/1k rows)
    ("exp2_odds", "likelihood"): 222.0,
    ("exp2_odds", "prompted"):    33.0,
    # M3 — exp3_security: 60 cells (3 datasets x 4 modes x 5 models)
    # creditcard ~21k test rows, UNSW ~190k test rows => wide variance; use median
    ("exp3_security", "prompted"):           45.0,
    ("exp3_security", "classical:iforest"):   5.0,
    ("exp3_security", "classical:pca"):       3.0,
    ("exp3_security", "classical:knn"):     600.0,   # UNSW KNN is slow (O(n^2))
    ("exp3_security", "classical:ecod"):      4.0,
    ("exp3_security", "likelihood"):        180.0,
}


def _load_json_dir(directory: Path) -> list[dict]:
    """Load all result JSONs from a directory (non-recursive, one level)."""
    rows = []
    for p in sorted(directory.glob("*.json")):
        if p.name.startswith("MANIFEST"):
            continue
        try:
            rows.append(json.loads(p.read_text()))
        except Exception:
            continue
    return rows


def _n_rows(row: dict) -> int:
    return int(row.get("n_rows_scored") or row.get("extra", {}).get("n_test") or 1)


def _wall_seconds(row: dict) -> float | None:
    return (row.get("extra") or {}).get("wall_seconds")


def build_pareto_table(results_root: Path) -> pd.DataFrame:
    """Build a flat DataFrame with one row per result JSON (M4 only for timing; M1-M3 approximated)."""
    records = []

    # M4 cells — structured wall_seconds per JSON
    for exp in ("exp4_serialization", "exp6_triage"):
        exp_dir = results_root / "raw" / exp
        if not exp_dir.exists():
            continue
        for row in _load_json_dir(exp_dir):
            if row.get("status") != "complete":
                continue
            meta = row.get("run_metadata", {})
            ws = _wall_seconds(row)
            n = _n_rows(row)
            records.append({
                "experiment": exp,
                "model": meta.get("model", row.get("run_metadata", {}).get("model", "")),
                "mode": meta.get("mode", ""),
                "dataset": meta.get("dataset", ""),
                "seed": meta.get("seed", 0),
                "auroc": row.get("metrics", {}).get("auroc") or row.get("metrics", {}).get("llm_auroc"),
                "wall_seconds": ws,
                "n_rows": n,
                "wall_per_1k": (ws / n * 1000) if (ws and n) else None,
                "timing_source": "per_cell",
            })

    # M1/M2/M3 cells — per-experiment timing approximations
    for exp in ("exp1_smol", "exp2_odds", "exp3_security"):
        exp_dir = results_root / "raw" / exp
        if not exp_dir.exists():
            continue
        for row in _load_json_dir(exp_dir):
            if row.get("status") != "complete":
                continue
            meta = row.get("run_metadata", {})
            mode = meta.get("mode", "")
            key = (exp, mode)
            approx_ws_per_1k = _RUNLOG_TIMING.get(key)
            n = _n_rows(row)
            records.append({
                "experiment": exp,
                "model": meta.get("model", ""),
                "mode": mode,
                "dataset": meta.get("dataset", ""),
                "seed": meta.get("seed", 0),
                "auroc": row.get("metrics", {}).get("auroc"),
                "wall_seconds": (approx_ws_per_1k * n / 1000) if approx_ws_per_1k else None,
                "n_rows": n,
                "wall_per_1k": approx_ws_per_1k,
                "timing_source": "runlog_approx",
            })

    df = pd.DataFrame(records)
    return df


def summarize_pareto(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to mean AUROC and mean wall_per_1k per (experiment, model, mode)."""
    agg = (
        df.dropna(subset=["auroc", "wall_per_1k"])
        .groupby(["experiment", "model", "mode"], as_index=False)
        .agg(
            mean_auroc=("auroc", "mean"),
            std_auroc=("auroc", "std"),
            mean_wall_per_1k=("wall_per_1k", "mean"),
            n_cells=("auroc", "count"),
            timing_source=("timing_source", "first"),
        )
        .sort_values("mean_wall_per_1k")
    )
    return agg


def main():
    ap = argparse.ArgumentParser(description="Exp 5 — Pareto practicality analysis")
    ap.add_argument("--results-root", default="results")
    ap.add_argument("--output-dir", default="results")
    args = ap.parse_args()

    results_root = Path(args.results_root)
    output_dir = Path(args.output_dir)

    print("[exp5] Building Pareto table from result JSONs ...")
    df = build_pareto_table(results_root)
    if df.empty:
        print("[exp5] No result JSONs found — run Exp 4 + Exp 6 first.")
        return

    summary = summarize_pareto(df)

    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    out_csv = tables_dir / "exp5_pareto.csv"
    summary.to_csv(out_csv, index=False)
    print(f"[exp5] Wrote Pareto table: {out_csv} ({len(summary)} rows)")
    print(summary.to_string(index=False))

    # Generate figure
    try:
        from anodet.analysis.figures import pareto as pareto_fig
        figs_dir = output_dir / "figures"
        figs_dir.mkdir(parents=True, exist_ok=True)
        out_fig = figs_dir / "exp5_pareto.png"
        pareto_fig(summary, out_fig)
        print(f"[exp5] Wrote Pareto figure: {out_fig}")
    except Exception as e:
        print(f"[exp5] Figure generation failed (non-fatal): {e}")
        print("[exp5] Install matplotlib or check anodet/analysis/figures.py")


if __name__ == "__main__":
    main()
