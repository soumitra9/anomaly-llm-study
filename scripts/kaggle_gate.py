"""Kaggle reproduction runner — loops `anodet.eval.exp1.reproduce_cell` over datasets on GPU.

Same code path validated locally on Mac (CPU); here it runs on Kaggle's CUDA GPU. Designed so the
TRIAL and the FULL gate differ only by arguments:

  TRIAL (validate the CUDA path, ~small quota):
    python -m scripts.kaggle_gate --datasets lympho,wine,breastw --models smol-360 --splits 1
  FULL gate (all 30 ODDS x 5 splits x SmolLM-135M/360M):
    python -m scripts.kaggle_gate --full

Writes per-cell JSON under results/raw/exp1_repro/ (the system of record) and prints a summary table.
Resumable: cells already complete are skipped (manifest-backed).
"""
from __future__ import annotations

import argparse
import sys
import time

# 30 ODDS datasets (exp2-odds run_anollm.sh order). Trial uses the small/fast ones first.
ODDS_30 = [
    "wine", "breastw", "cardio", "ecoli", "lymphography", "vertebral", "wbc", "yeast", "heart",
    "glass", "ionosphere", "letter_recognition", "mammography", "pendigits", "pima", "satellite",
    "satimage-2", "thyroid", "vowels", "shuttle", "seismic", "optdigits", "annthyroid", "http",
    "smtp", "mulcross", "covertype", "musk", "arrhythmia", "speech",
]
TRIAL = ["lymphography", "wine", "breastw"]  # tiny, fast — validates the CUDA path cheaply


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--datasets", default=",".join(TRIAL), help="comma list, or use --full")
    p.add_argument("--models", default="smol-360", help="comma list of smol / smol-360")
    p.add_argument("--splits", type=int, default=1, help="number of splits (0..n-1); gate uses 5")
    p.add_argument("--max-steps", type=int, default=2000)
    p.add_argument("--r", type=int, default=21)
    p.add_argument("--batch-size", type=int, default=None,
                   help="override per-dataset (micro) batch from configs/anollm_hparams.yaml (default: use config)")
    p.add_argument("--grad-accum", type=int, default=1,
                   help="gradient accumulation steps; effective batch = per-dataset batch * grad_accum. "
                        "AnoLLM published ODDS used 4 GPUs -> pass 4 to reproduce their effective batch.")
    p.add_argument("--device", default="cuda")
    p.add_argument("--full", action="store_true", help="all 30 ODDS x 5 splits x {smol,smol-360}")
    p.add_argument("--results-root", default="results")
    p.add_argument("--time-budget-secs", type=int, default=0,
                   help="stop launching NEW cells once elapsed exceeds this (0 = no limit). "
                        "Keeps a session under the 12h wall so SaveAndRunAll commits its output.")
    p.add_argument("--max-cells", type=int, default=0, help="stop after this many NEW cells (0 = no limit)")
    a = p.parse_args()

    from anodet.eval.exp1 import reproduce_cell
    from anodet.utils.run_metadata import cell_key, cell_path, is_complete

    if a.full:
        datasets, models, n = ODDS_30, ["smol", "smol-360"], 5
    else:
        datasets = [d.strip() for d in a.datasets.split(",")]
        models = [m.strip() for m in a.models.split(",")]
        n = a.splits

    t0 = time.time()
    rows, n_new, n_skip, n_fail, stopped = [], 0, 0, 0, False
    for model in models:
        for ds in datasets:
            for split in range(n):
                # resumption: a cell whose JSON is already 'complete' is reused (survives 12h limit)
                key = cell_key(model, "likelihood", ds, split)
                if is_complete(cell_path(a.results_root, "exp1_repro", key)):
                    n_skip += 1
                    continue
                # clean stop BEFORE starting a new cell, so the session ends and output commits
                elapsed = time.time() - t0
                if a.time_budget_secs and elapsed > a.time_budget_secs:
                    print(f"[budget] time budget {a.time_budget_secs}s exceeded ({elapsed:.0f}s) — "
                          f"stopping cleanly; resume next session.", flush=True)
                    stopped = True
                    break
                if a.max_cells and n_new >= a.max_cells:
                    print(f"[budget] max-cells {a.max_cells} reached — stopping cleanly.", flush=True)
                    stopped = True
                    break
                try:
                    m = reproduce_cell(ds, model, split_idx=split, n_splits=5, max_steps=a.max_steps,
                                       r=a.r, batch_size=a.batch_size, grad_accum=a.grad_accum, device=a.device,
                                       results_root=a.results_root)
                    rows.append((model, ds, split, m["auroc"], m["auprc"]))
                    n_new += 1
                    print(f"[ok] {model} {ds} split{split}: AUROC={m['auroc']:.3f} AUPRC={m['auprc']:.3f} "
                          f"({n_new} new, {elapsed:.0f}s elapsed)", flush=True)
                except Exception as e:  # one cell failing must not abort the sweep
                    n_fail += 1
                    print(f"[FAIL] {model} {ds} split{split}: {type(e).__name__}: {e}", flush=True)
            if stopped:
                break
        if stopped:
            break

    print("\n=== summary ===")
    for model, ds, split, au, ap in rows:
        print(f"  {model:10s} {ds:18s} split{split}  AUROC={au:.3f}  AUPRC={ap:.3f}")
    print(f"\nthis session: {n_new} new, {n_skip} skipped (already complete), {n_fail} failed. "
          f"Per-cell JSON in {a.results_root}/raw/exp1_repro/.")
    # exit 0 whenever we made progress or cleanly hit a budget, so Kaggle commits the output
    return 0 if (n_new or n_skip or stopped) else 1


if __name__ == "__main__":
    sys.exit(main())
