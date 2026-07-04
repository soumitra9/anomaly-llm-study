"""M3 Exp-3 (security) fleet runner — shardable, resumable. Mirrors scripts/exp2_fleet.py.

Exp 3 has a less-uniform cell structure than Exp 2, so cells are built explicitly (not a pure Cartesian):
  - **likelihood** (mode A): Qwen2.5-3B ONLY, credit-card ONLY (both splits) × seeds — the expensive arm.
  - **prompted** (mode B): both models × {credit-card temporal, credit-card random, unsw} × seeds.
  - **classical** (model-independent): {iforest,pca,knn,ecod} × all task-datasets × seeds — CPU, ~free.

A "task-dataset" encodes the split so cell keys stay unique: `creditcard-temporal`, `creditcard-random`, `unsw`.
The real loader dataset + split are recovered and passed to `anodet.eval.exp3_security.run_one` via load_kw.
Classical cells use model tag `classical` (model-independent). Resume = skip cells whose per-cell JSON is
status=='complete' (`run_metadata.is_complete`), identical to exp2_fleet. Per-cell JSON is the system of record.

Examples:
  # everything (one pod can hold the whole security grid — it's small):
  python -m scripts.exp3_fleet
  # shard by task-dataset:
  python -m scripts.exp3_fleet --task-datasets creditcard-temporal,creditcard-random
  # single-cell smoke (CPU):
  python -m scripts.exp3_fleet --task-datasets unsw --modes prompted --models smol-360 --seeds 0 --device cpu
"""
from __future__ import annotations

import argparse
import sys
import time

EXPERIMENT = "exp3_security"
# task-dataset -> (real loader dataset, split kwarg or None)
TASKS = {
    "creditcard-temporal": ("creditcard", "temporal"),
    "creditcard-random": ("creditcard", "random"),
    "unsw": ("unsw", None),
}
CLASSICAL = ["iforest", "pca", "knn", "ecod"]
LIKELIHOOD_MODEL = "qwen2.5-3b"          # mode-A: one model, credit-card only (cost)
LIKELIHOOD_TASKS = ["creditcard-temporal", "creditcard-random"]
# per-(model,task) batch for the GPU modes; OOM-retry beneath this. Security test sets are ~20-40k rows.
DEFAULT_BATCH = 16


def build_cells(task_datasets, models, modes, seeds):
    """Return the explicit M3 security cell list: dicts {model, mode, task, dataset, split, seed}."""
    cells = []
    for task in task_datasets:
        dataset, split = TASKS[task]
        for seed in seeds:
            if "classical" in modes:
                for det in CLASSICAL:  # model-independent
                    cells.append({"model": "classical", "mode": f"classical:{det}",
                                  "task": task, "dataset": dataset, "split": split, "seed": seed})
            if "prompted" in modes:
                for model in models:
                    cells.append({"model": model, "mode": "prompted",
                                  "task": task, "dataset": dataset, "split": split, "seed": seed})
            if "likelihood" in modes and task in LIKELIHOOD_TASKS:
                cells.append({"model": LIKELIHOOD_MODEL, "mode": "likelihood",
                              "task": task, "dataset": dataset, "split": split, "seed": seed})
    return cells


def main():
    p = argparse.ArgumentParser(description="M3 Exp-3 security fleet runner (shardable, resumable)")
    p.add_argument("--task-datasets", default="all", help="comma list of task-datasets, or 'all'")
    p.add_argument("--models", default="smol-360,qwen2.5-3b", help="comma list (prompted arm)")
    p.add_argument("--modes", default="likelihood,prompted,classical", help="comma list")
    p.add_argument("--seeds", default="0,1,2", help="comma list of seeds")
    p.add_argument("--r", type=int, default=10, help="likelihood permutations (r=5 lever if measure-first is tight)")
    p.add_argument("--n-levels", type=int, default=10)
    p.add_argument("--n-top", type=int, default=100, help="Precision/Recall@top-N")
    p.add_argument("--batch-size", type=int, default=None, help="override default per-cell batch (smokes)")
    p.add_argument("--data-dir", default="data")
    p.add_argument("--device", default="cuda")
    p.add_argument("--results-root", default="results")
    p.add_argument("--time-budget-secs", type=int, default=0)
    p.add_argument("--max-cells", type=int, default=0)
    a = p.parse_args()

    from anodet.eval.exp3_security import run_one
    from anodet.utils.run_metadata import RunMetadata, cell_key, cell_path, is_complete, write_result

    tasks = list(TASKS) if a.task_datasets.strip() == "all" else [t.strip() for t in a.task_datasets.split(",")]
    models = [m.strip() for m in a.models.split(",")]
    modes = [m.strip() for m in a.modes.split(",")]
    seeds = [int(s) for s in a.seeds.split(",")]
    cells = build_cells(tasks, models, modes, seeds)
    print(f"[exp3] {len(cells)} cells over tasks={tasks} modes={modes}; results-root={a.results_root}", flush=True)

    t0 = time.time()
    rows, n_new, n_skip, n_fail, stopped = [], 0, 0, 0, False
    for c in cells:
        # cell key: task encodes the split so keys are unique across creditcard temporal/random
        key = cell_key(c["model"], c["mode"], c["task"], c["seed"])
        if is_complete(cell_path(a.results_root, EXPERIMENT, key)):
            n_skip += 1
            continue
        elapsed = time.time() - t0
        if a.time_budget_secs and elapsed > a.time_budget_secs:
            print(f"[budget] time {a.time_budget_secs}s exceeded — stopping cleanly (resume-safe).", flush=True)
            stopped = True; break
        if a.max_cells and n_new >= a.max_cells:
            print(f"[budget] max-cells {a.max_cells} reached — stopping cleanly.", flush=True)
            stopped = True; break
        bs = a.batch_size if a.batch_size is not None else DEFAULT_BATCH
        load_kw = {"seed": c["seed"]}
        if c["split"] is not None:
            load_kw["split"] = c["split"]
        try:
            metrics, status, extra = run_one(
                c["dataset"], c["model"], c["mode"], data_dir=a.data_dir, n_levels=a.n_levels,
                batch_size=bs, device=a.device, n_top=a.n_top, **({"r": a.r} if c["mode"] == "likelihood" else {}),
                **load_kw,
            )
            # record the task (with split) as the dataset identifier so the key round-trips
            rm = dict(extra.get("run_metadata", {}));
            meta = RunMetadata(experiment=EXPERIMENT, model=c["model"], mode=c["mode"],
                               dataset=c["task"], seed=c["seed"], **rm)
            write_result(a.results_root, meta, metrics=metrics, status=status,
                         n_rows_scored=extra.get("n_rows_scored"), n_rows_expected=extra.get("n_rows_expected"),
                         extra={k: v for k, v in extra.items()
                                if k not in {"run_metadata", "n_rows_scored", "n_rows_expected"}})
            au = metrics.get("auprc_gain")
            rows.append((c["model"], c["mode"], c["task"], c["seed"], au)); n_new += 1
            print(f"[ok] {c['model']} {c['mode']} {c['task']} seed{c['seed']} (bs={bs}): "
                  f"auprc_gain={au if au is None else round(au,3)} ({n_new} new, {elapsed:.0f}s)", flush=True)
        except Exception as e:  # one cell failing must not abort the shard
            n_fail += 1
            print(f"[FAIL] {c['model']} {c['mode']} {c['task']} seed{c['seed']}: {type(e).__name__}: {e}", flush=True)

    print(f"\n[exp3] this session: {n_new} new, {n_skip} skipped, {n_fail} failed. "
          f"Per-cell JSON in {a.results_root}/raw/{EXPERIMENT}/.")
    return 0 if (n_new or n_skip or stopped) else 1


if __name__ == "__main__":
    sys.exit(main())
