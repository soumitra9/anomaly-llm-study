"""M2 Exp 2 fleet runner — shardable, resumable, per-dataset-batch-aware.

The production driver for the M2 same-model A/B (likelihood vs prompted) across a multi-pod A40 fleet.
Mirrors `scripts/kaggle_gate.py`'s hard-won machinery (skip-complete resume, time/​cell budgets, one-cell
failure isolation) and adds the two things the fleet needs that `exp2.py --config` lacks:

  1. **Dataset sharding** — `--datasets` restricts this process to a disjoint subset so N pods run in
     parallel with zero cross-pod collision (each pod owns whole datasets × all its models/modes/seeds).
  2. **Per-(model,dataset) batch lookup** — SmolLM-360M batches from configs/anollm_hparams.yaml, Qwen2.5-3B
     from configs/qwen_hparams.yaml. run_likelihood/run_prompted still OOM-retry beneath this, so an
     under-estimate self-corrects and is recorded; a cell can never hard-fail on memory.

RESUME (balance-loss safe): a cell whose per-cell JSON is already status=='complete' is skipped. The JSON
is the durable checkpoint (atomic write). To resume after any halt: rsync local results UP to the pod,
then re-run the same command — completed cells are skipped, only the pending remainder runs.

Examples:
  # pod A owns 6 datasets, both models, both modes, 3 seeds:
  python -m scripts.exp2_fleet --datasets wine,breastw,cardio,ecoli,lymphography,vertebral
  # single-cell smoke:
  python -m scripts.exp2_fleet --datasets breastw --models smol-360 --modes likelihood --seeds 0 --max-steps 5 --r 2 --device cpu
"""
from __future__ import annotations

import argparse
import sys
import time

import yaml

# Full ODDS-30 grid (exp2.yaml order). --datasets defaults to ALL; shard by naming a subset per pod.
ODDS_30 = [
    "wine", "breastw", "cardio", "ecoli", "lymphography", "vertebral", "wbc", "yeast", "heart",
    "glass", "ionosphere", "letter_recognition", "mammography", "pendigits", "pima", "satellite",
    "satimage-2", "thyroid", "vowels", "shuttle", "seismic", "optdigits", "annthyroid", "http",
    "smtp", "mulcross", "covertype", "musk", "arrhythmia", "speech",
]
EXPERIMENT = "exp2_odds"
# per-model batch config: model alias -> hparams YAML
BATCH_CONFIG = {"smol-360": "configs/anollm_hparams.yaml", "qwen2.5-3b": "configs/qwen_hparams.yaml"}
DEFAULT_BATCH = 16  # fallback when a (model,dataset) isn't in its table; OOM-retry protects it


def _load_batch_tables() -> dict:
    """model -> {dataset -> batch_size}. Missing files/models yield an empty table (falls back to DEFAULT_BATCH)."""
    tables = {}
    for model, path in BATCH_CONFIG.items():
        try:
            with open(path) as f:
                cfg = yaml.safe_load(f)
            tables[model] = {d: int(v["batch_size"]) for d, v in cfg["hparams"].items()}
        except FileNotFoundError:
            tables[model] = {}
    return tables


def _batch_for(tables: dict, model: str, dataset: str) -> int:
    return tables.get(model, {}).get(dataset, DEFAULT_BATCH)


def main():
    p = argparse.ArgumentParser(description="M2 Exp 2 fleet runner (shardable, resumable)")
    p.add_argument("--datasets", default="all", help="comma list to shard this pod, or 'all' (ODDS-30)")
    p.add_argument("--models", default="smol-360,qwen2.5-3b", help="comma list")
    p.add_argument("--modes", default="likelihood,prompted", help="comma list")
    p.add_argument("--seeds", default="0,1,2", help="comma list of ODDS split indices")
    p.add_argument("--n-splits", type=int, default=5)
    p.add_argument("--max-steps", type=int, default=2000)
    p.add_argument("--r", type=int, default=10)
    p.add_argument("--n-levels", type=int, default=10)
    p.add_argument("--batch-size", type=int, default=None,
                   help="override the per-dataset batch table (use only for smokes)")
    p.add_argument("--device", default="cuda")
    p.add_argument("--results-root", default="results")
    p.add_argument("--time-budget-secs", type=int, default=0,
                   help="stop launching NEW cells once elapsed exceeds this (0 = no limit)")
    p.add_argument("--max-cells", type=int, default=0, help="stop after this many NEW cells (0 = no limit)")
    a = p.parse_args()

    from anodet.eval.exp2 import run_one
    from anodet.utils.run_metadata import RunMetadata, cell_key, cell_path, is_complete, write_result

    datasets = ODDS_30 if a.datasets.strip() == "all" else [d.strip() for d in a.datasets.split(",")]
    models = [m.strip() for m in a.models.split(",")]
    modes = [m.strip() for m in a.modes.split(",")]
    seeds = [int(s) for s in a.seeds.split(",")]
    tables = _load_batch_tables()

    n_total = len(models) * len(modes) * len(datasets) * len(seeds)
    print(f"[fleet] grid: {len(models)} models x {len(modes)} modes x {len(datasets)} datasets x "
          f"{len(seeds)} seeds = {n_total} cells; results-root={a.results_root}", flush=True)

    t0 = time.time()
    rows, n_new, n_skip, n_fail, stopped = [], 0, 0, 0, False
    # order: model -> mode -> dataset -> seed (seeds innermost => a dataset's 3 seeds land together)
    for model in models:
        for mode in modes:
            for ds in datasets:
                for seed in seeds:
                    key = cell_key(model, mode, ds, seed)
                    if is_complete(cell_path(a.results_root, EXPERIMENT, key)):
                        n_skip += 1
                        continue
                    elapsed = time.time() - t0
                    if a.time_budget_secs and elapsed > a.time_budget_secs:
                        print(f"[budget] time {a.time_budget_secs}s exceeded ({elapsed:.0f}s) — stopping "
                              f"cleanly; resume with the same command.", flush=True)
                        stopped = True
                        break
                    if a.max_cells and n_new >= a.max_cells:
                        print(f"[budget] max-cells {a.max_cells} reached — stopping cleanly.", flush=True)
                        stopped = True
                        break
                    bs = a.batch_size if a.batch_size is not None else _batch_for(tables, model, ds)
                    try:
                        metrics, status, extra = run_one(
                            ds, model, mode, split_idx=seed, n_splits=a.n_splits,
                            max_steps=a.max_steps, r=a.r, n_levels=a.n_levels,
                            batch_size=bs, device=a.device,
                        )
                        meta = RunMetadata(experiment=EXPERIMENT, model=model, mode=mode,
                                           dataset=ds, seed=seed, **extra["run_metadata"])
                        write_result(a.results_root, meta, metrics=metrics, status=status,
                                     n_rows_scored=extra["n_rows_scored"],
                                     n_rows_expected=extra["n_rows_expected"],
                                     extra={k: v for k, v in extra.items()
                                            if k not in {"run_metadata", "n_rows_scored", "n_rows_expected"}})
                        rows.append((model, mode, ds, seed, metrics["auroc"]))
                        n_new += 1
                        print(f"[ok] {model} {mode} {ds} seed{seed} (bs={bs}): "
                              f"AUROC={metrics['auroc']:.3f} ({n_new} new, {elapsed:.0f}s)", flush=True)
                    except Exception as e:  # one cell failing must not abort the shard
                        n_fail += 1
                        print(f"[FAIL] {model} {mode} {ds} seed{seed}: {type(e).__name__}: {e}", flush=True)
                if stopped:
                    break
            if stopped:
                break
        if stopped:
            break

    print("\n=== summary ===")
    for model, mode, ds, seed, au in rows:
        print(f"  {model:12s} {mode:10s} {ds:18s} seed{seed}  AUROC={au:.3f}")
    print(f"\nthis session: {n_new} new, {n_skip} skipped, {n_fail} failed. "
          f"Per-cell JSON in {a.results_root}/raw/{EXPERIMENT}/.")
    return 0 if (n_new or n_skip or stopped) else 1


if __name__ == "__main__":
    sys.exit(main())
