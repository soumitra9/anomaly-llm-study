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
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--device", default="cuda")
    p.add_argument("--full", action="store_true", help="all 30 ODDS x 5 splits x {smol,smol-360}")
    a = p.parse_args()

    from anodet.eval.exp1 import reproduce_cell

    if a.full:
        datasets, models, n = ODDS_30, ["smol", "smol-360"], 5
    else:
        datasets = [d.strip() for d in a.datasets.split(",")]
        models = [m.strip() for m in a.models.split(",")]
        n = a.splits

    rows = []
    for model in models:
        for ds in datasets:
            for split in range(n):
                try:
                    m = reproduce_cell(ds, model, split_idx=split, n_splits=5, max_steps=a.max_steps,
                                       r=a.r, batch_size=a.batch_size, device=a.device)
                    rows.append((model, ds, split, m["auroc"], m["auprc"]))
                    print(f"[ok] {model} {ds} split{split}: AUROC={m['auroc']:.3f} AUPRC={m['auprc']:.3f}",
                          flush=True)
                except Exception as e:  # one cell failing must not abort the sweep
                    print(f"[FAIL] {model} {ds} split{split}: {type(e).__name__}: {e}", flush=True)

    print("\n=== summary ===")
    for model, ds, split, au, ap in rows:
        print(f"  {model:10s} {ds:18s} split{split}  AUROC={au:.3f}  AUPRC={ap:.3f}")
    print(f"\n{len(rows)} cells complete. Per-cell JSON in results/raw/exp1_repro/.")
    return 0 if rows else 1


if __name__ == "__main__":
    sys.exit(main())
