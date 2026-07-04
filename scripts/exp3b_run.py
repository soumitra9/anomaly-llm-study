"""M3 Exp-3b runner (RQ3b: semantic vs anonymized column names) — small, resumable.

6 cells: arm in {semantic, anon} x seeds x 1 model (Qwen2.5-3B), prompted, on pima (breastw backup).
Gated on the Pima UCI-order verification (done 2026-07-04, see anodet/data/odds_names.py). Tiny/cheap.
  python -m scripts.exp3b_run --model qwen2.5-3b --seeds 0,1,2 --device cuda
"""
from __future__ import annotations

import argparse
import sys

EXPERIMENT = "exp3b_names"


def main():
    p = argparse.ArgumentParser(description="M3 Exp-3b semantic-vs-anon runner")
    p.add_argument("--dataset", default="pima")
    p.add_argument("--model", default="qwen2.5-3b")
    p.add_argument("--arms", default="semantic,anon")
    p.add_argument("--seeds", default="0,1,2")
    p.add_argument("--n-levels", type=int, default=10)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--device", default="cuda")
    p.add_argument("--results-root", default="results")
    a = p.parse_args()

    from anodet.eval.exp3b_names import run_one
    from anodet.utils.run_metadata import RunMetadata, cell_key, cell_path, is_complete, write_result

    arms = [x.strip() for x in a.arms.split(",")]
    seeds = [int(s) for s in a.seeds.split(",")]
    n_new = n_skip = n_fail = 0
    for seed in seeds:
        for arm in arms:
            key = cell_key(a.model, arm, a.dataset, seed)  # mode slot = arm
            if is_complete(cell_path(a.results_root, EXPERIMENT, key)):
                n_skip += 1
                continue
            try:
                metrics, status, extra = run_one(a.dataset, arm=arm, model=a.model, split_idx=seed,
                                                 n_levels=a.n_levels, batch_size=a.batch_size, device=a.device)
                meta = RunMetadata(experiment=EXPERIMENT, model=a.model, mode=arm,
                                   dataset=a.dataset, seed=seed, **extra.get("run_metadata", {}))
                write_result(a.results_root, meta, metrics=metrics, status=status,
                             n_rows_scored=extra.get("n_rows_scored"),
                             extra={k: v for k, v in extra.items() if k not in {"run_metadata", "n_rows_scored"}})
                n_new += 1
                print(f"[ok] {a.model} {arm} {a.dataset} seed{seed}: AUROC={metrics['auroc']:.3f}", flush=True)
            except Exception as e:
                n_fail += 1
                print(f"[FAIL] {arm} {a.dataset} seed{seed}: {type(e).__name__}: {e}", flush=True)
    print(f"\n[exp3b] {n_new} new, {n_skip} skipped, {n_fail} failed -> {a.results_root}/raw/{EXPERIMENT}/")
    return 0 if (n_new or n_skip) else 1


if __name__ == "__main__":
    sys.exit(main())
