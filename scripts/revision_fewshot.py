"""Revision RV2 — few-shot prompted fleet runner (GATE_SPEC.md §RV2).

Runs Qwen2.5-3B-Instruct with k normals-only few-shot exemplars on the 8 DA1 ODDS datasets,
seeds {0,1,2}. Results land in `results/raw/exp2_fewshot/` (mode `prompted-fewshot`) and never
touch M2 zero-shot cells in `exp2_odds/`.

Example (CPU smoke):
  uv run python -m scripts.revision_fewshot --datasets breastw --seeds 0 --n-shots 3 --device cpu
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import time

EXPERIMENT = "exp2_fewshot"
# GATE_SPEC §RV2 — same 8 datasets as DA1 dissolving arm
RV2_DATASETS = [
    "arrhythmia", "breastw", "cardio", "ionosphere",
    "shuttle", "speech", "vertebral", "yeast",
]
DEFAULT_MODEL = "qwen2.5-3b"
DEFAULT_MODE = "prompted-fewshot"
_SERIALIZE_FMT = "col is value , ..."


def _h(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def build_cells(datasets, seeds):
    return [{"dataset": d, "model": DEFAULT_MODEL, "mode": DEFAULT_MODE, "seed": s}
            for d in datasets for s in seeds]


def main():
    p = argparse.ArgumentParser(description="RV2 few-shot prompted fleet runner")
    p.add_argument("--datasets", default=",".join(RV2_DATASETS),
                   help="comma list of ODDS datasets (default: GATE_SPEC §RV2 8-set)")
    p.add_argument("--seeds", default="0,1,2", help="comma list of ODDS split indices")
    p.add_argument("--n-shots", type=int, default=3, help="normals-only exemplar count (RV2 pre-reg k=3)")
    p.add_argument("--n-splits", type=int, default=5)
    p.add_argument("--n-levels", type=int, default=10)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--device", default="cuda")
    p.add_argument("--results-root", default="results")
    p.add_argument("--time-budget-secs", type=int, default=0)
    p.add_argument("--max-cells", type=int, default=0)
    a = p.parse_args()

    from anodet.data.odds import load_odds
    from anodet.metrics import auprc, auprc_gain, auroc, recall_at_fpr
    from anodet.scoring.prompted import run_prompted
    from anodet.utils.run_metadata import RunMetadata, cell_key, cell_path, is_complete, write_result
    from anodet.utils.seeding import seed_everything

    datasets = RV2_DATASETS if a.datasets.strip() == "all" else [d.strip() for d in a.datasets.split(",")]
    seeds = [int(s) for s in a.seeds.split(",")]
    cells = build_cells(datasets, seeds)
    print(f"[rv2] {len(cells)} cells datasets={datasets} n_shots={a.n_shots}; "
          f"results-root={a.results_root}", flush=True)

    t0 = time.time()
    n_new, n_skip, n_fail, stopped = 0, 0, 0, False
    for c in cells:
        key = cell_key(c["model"], c["mode"], c["dataset"], c["seed"])
        if is_complete(cell_path(a.results_root, EXPERIMENT, key)):
            n_skip += 1
            continue
        elapsed = time.time() - t0
        if a.time_budget_secs and elapsed > a.time_budget_secs:
            print(f"[budget] time {a.time_budget_secs}s exceeded — stopping cleanly.", flush=True)
            stopped = True
            break
        if a.max_cells and n_new >= a.max_cells:
            print(f"[budget] max-cells {a.max_cells} reached — stopping cleanly.", flush=True)
            stopped = True
            break
        try:
            seed_everything(c["seed"])
            data = load_odds(c["dataset"], split_idx=c["seed"], n_splits=a.n_splits)
            start = time.time()
            out = run_prompted(
                f"{c['model']}-instruct", data["X_test"],
                X_train=data["X_train"], y_train=data["y_train"],
                n_shots=a.n_shots, shot_seed=c["seed"],
                n_levels=a.n_levels, batch_size=a.batch_size, device=a.device,
            )
            y = data["y_test"]
            scores = out["scores"]
            metrics = {
                "auroc": auroc(y, scores),
                "auprc": auprc(y, scores),
                "auprc_gain": auprc_gain(y, scores),
                "recall_at_1pct_fpr": recall_at_fpr(y, scores, 0.01),
            }
            rm = {
                "dataset_content_hash": data["content_hash"],
                "split_index_hash": data["split_index_hash"],
                "checkpoint_kind": "instruct",
                "precision": "bf16" if out["device"] == "cuda" else "fp32",
                "decode_config": {
                    "scorer": "expected_value",
                    "n_levels": a.n_levels,
                    "temperature": 0,
                    "n_shots": a.n_shots,
                    "shot_seed": c["seed"],
                },
                "serialization_template_hash": _h(_SERIALIZE_FMT),
                "rendered_prompt_hash": _h(f"{_SERIALIZE_FMT}|n_levels={a.n_levels}|n_shots={a.n_shots}"),
            }
            meta = RunMetadata(
                experiment=EXPERIMENT, model=c["model"], mode=c["mode"],
                dataset=c["dataset"], seed=c["seed"], **rm,
            )
            write_result(
                a.results_root, meta, metrics=metrics, status="complete",
                n_rows_scored=int(len(y)), n_rows_expected=int(len(y)),
                extra={"device_used": out["device"], "distinct_levels": out["distinct_levels"],
                       "wall_seconds": time.time() - start},
            )
            n_new += 1
            print(f"[ok] {c['model']} {c['mode']} {c['dataset']} seed{c['seed']} "
                  f"AUROC={metrics['auroc']:.3f} ({n_new} new, {elapsed:.0f}s)", flush=True)
        except Exception as e:
            n_fail += 1
            print(f"[FAIL] {c['dataset']} seed{c['seed']}: {type(e).__name__}: {e}", flush=True)

    print(f"\n[rv2] this session: {n_new} new, {n_skip} skipped, {n_fail} failed. "
          f"Per-cell JSON in {a.results_root}/raw/{EXPERIMENT}/.")
    return 0 if (n_new or n_skip or stopped) else 1


if __name__ == "__main__":
    sys.exit(main())
