"""Exp 6 — Two-stage IForest -> LLM triage (RQ7).

Re-scores each security test split with IForest (classical shortlist) and Qwen2.5-3B prompted (LLM re-rank),
then evaluates the two-stage system at k = {1%, 5%, 10%} of the test set within each cell.

Grid: datasets x seeds = 9 cells (no per-k axis — k-sweep runs inside each cell to avoid re-scoring).

Metric storage: percentage-keyed scalar fields (k1pct_*, k5pct_*, k10pct_*) for aggregate.py compatibility.
All dataset-vs-dataset comparisons use the same column names. Full evaluate_triage dicts stored in extra.

Classical detector: IForest only. KNN excluded — O(n^2) on UNSW (~300k rows) is hours or OOM.
Prompted model: Qwen2.5-3B instruct (frozen, single forward pass per row).

Split reuse: same (dataset, seed) loader kwargs as exp3_security, so test sets match. The drop_time=True
for creditcard matches the corrected T3 protocol (all M4 cells use this; M3 cells used drop_time=False).
"""
from __future__ import annotations

import argparse
import time
from typing import Callable, Optional

import numpy as np

from anodet.metrics import auprc, auprc_gain, auroc, recall_at_fpr
from anodet.triage.two_stage import evaluate_triage


def _load_security(dataset: str, seed: int, data_dir: str = "data") -> dict:
    """Load security dataset for exp6; uses same parameters as exp3_security for split reuse."""
    if dataset == "creditcard-temporal":
        from anodet.data.creditcard import load_creditcard
        return load_creditcard(
            f"{data_dir}/creditcard.csv",
            split="temporal", seed=seed, drop_time=True,
        )
    if dataset == "creditcard-random":
        from anodet.data.creditcard import load_creditcard
        return load_creditcard(
            f"{data_dir}/creditcard.csv",
            split="random", seed=seed, drop_time=True,
        )
    if dataset == "unsw":
        import pandas as pd
        from anodet.data.unsw import prepare_unsw
        return prepare_unsw(pd.read_parquet(f"{data_dir}/unsw.parquet"), seed=seed)
    raise ValueError(
        f"unknown security dataset {dataset!r} "
        "(expected: creditcard-temporal, creditcard-random, unsw)"
    )


def run_one(
    dataset: str,
    model: str,
    mode: str,
    *,
    seed: int = 0,
    classical_detector: str = "iforest",
    prompted_model: str = "qwen2.5-3b",
    n_levels: int = 10,
    batch_size: int = 16,
    device: Optional[str] = None,
    data_dir: str = "data",
) -> tuple[dict, str, dict]:
    """Run one Exp 6 cell: IForest + prompted scoring + k-sweep triage evaluation.

    `model` and `mode` from the grid are written into RunMetadata for provenance;
    the actual execution uses `classical_detector` and `prompted_model` from the config.
    Returns (metrics, status, extra) per the grid run_cell contract.
    """
    from anodet.baselines.classical import run_baseline
    from anodet.scoring.prompted import run_prompted

    start = time.time()

    data = _load_security(dataset, seed, data_dir=data_dir)
    y = np.asarray(data["y_test"]).astype(int)
    sample_weight = data.get("sample_weight")
    n_test = len(y)

    # Classical scoring (CPU, seconds)
    classical = run_baseline(
        classical_detector, data["X_train"], data["X_test"], seed=seed
    )

    # Prompted scoring (single forward pass)
    llm_out = run_prompted(
        f"{prompted_model}-instruct", data["X_test"],
        n_levels=n_levels, batch_size=batch_size, device=device,
    )
    llm = llm_out["scores"]

    # k-sweep: evaluate at 1%, 5%, 10% of test set (within this cell, no re-scoring)
    k_pcts = [
        (1,  max(1, int(0.01 * n_test))),
        (5,  max(1, int(0.05 * n_test))),
        (10, max(1, int(0.10 * n_test))),
    ]

    flat_metrics: dict = {}
    full_results: dict = {}

    for pct, k in k_pcts:
        res = evaluate_triage(y, classical, llm, k=k, sample_weight=sample_weight)
        flat_metrics[f"k{pct}pct_recall_at_fpr"]  = res["two_stage"]["recall_at_fpr"]
        flat_metrics[f"k{pct}pct_uplift_recall"]   = res["uplift_two_stage_vs_classical"]["recall_at_fpr"]
        flat_metrics[f"k{pct}pct_precision_at_k"]  = res["two_stage"]["precision_at_k"]
        flat_metrics[f"k{pct}pct_recall_at_k"]     = res["two_stage"]["recall_at_k"]
        # baseline comparisons for the paper
        flat_metrics[f"k{pct}pct_classical_recall_at_fpr"] = res["classical"]["recall_at_fpr"]
        flat_metrics[f"k{pct}pct_llm_recall_at_fpr"]       = res["llm"]["recall_at_fpr"]
        full_results[pct] = res

    # Standalone LLM metrics for reference (auroc/auprc of the prompted scorer alone)
    llm_auroc = auroc(y, llm)
    classical_auroc = auroc(y, classical)
    flat_metrics["llm_auroc"]       = llm_auroc
    flat_metrics["classical_auroc"] = classical_auroc
    flat_metrics["llm_auprc_gain"]  = auprc_gain(y, llm)

    extra = {
        "full_triage_results": full_results,
        "k_integers": {pct: k for pct, k in k_pcts},
        "n_test": n_test,
        "wall_seconds": time.time() - start,
        "classical_detector": classical_detector,
        "prompted_model": prompted_model,
        "device_used": llm_out.get("device"),
        "content_hash": data.get("content_hash"),
        "run_metadata": {
            "checkpoint_kind": "instruct",
            "dataset_content_hash": data.get("content_hash"),
        },
    }
    return flat_metrics, "complete", extra


def make_run_cell(cfg: dict, **hparams) -> Callable[[dict], tuple[dict, str, dict]]:
    """Bind config + hyperparameters into a grid run_cell(cell) closure."""
    classical_detector = cfg.get("classical_detector", "iforest")
    prompted_model = cfg.get("prompted_model", "qwen2.5-3b")
    data_dir = hparams.pop("data_dir", "data")

    def run_cell(cell: dict) -> tuple[dict, str, dict]:
        return run_one(
            cell["dataset"], cell["model"], cell["mode"],
            seed=int(cell["seed"]),
            classical_detector=classical_detector,
            prompted_model=prompted_model,
            data_dir=data_dir,
            **hparams,
        )

    return run_cell


def run(config_path: str, results_root: str = "results", **hparams) -> int:
    """Run all pending cells from a YAML config; returns number of cells run."""
    from anodet.eval import grid
    cfg = grid.load_config(config_path)
    return grid.run_grid(cfg, results_root, make_run_cell(cfg, **hparams))


def _cli():
    p = argparse.ArgumentParser(description="Exp 6 — two-stage IForest+LLM triage on security data")
    p.add_argument("--config", default="configs/exp6_triage.yaml", help="YAML config path")
    p.add_argument("--dataset", default=None, help="single dataset (skips --config sweep)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--classical-detector", default="iforest")
    p.add_argument("--prompted-model", default="qwen2.5-3b")
    p.add_argument("--n-levels", type=int, default=10)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--device", default=None)
    p.add_argument("--results-root", default="results")
    p.add_argument("--data-dir", default="data")
    a = p.parse_args()

    hparams = dict(n_levels=a.n_levels, batch_size=a.batch_size,
                   device=a.device, data_dir=a.data_dir)

    if a.dataset is None:
        # classical_detector and prompted_model come from the YAML via cfg in make_run_cell.
        # Do NOT pass them here — they would land in hparams and be passed twice to run_one.
        n = run(a.config, a.results_root, **hparams)
        print(f"[exp6] ran {n} pending cell(s) from {a.config}")
        return

    metrics, status, extra = run_one(
        a.dataset, "qwen2.5-3b", "triage",
        seed=a.seed,
        classical_detector=a.classical_detector,
        prompted_model=a.prompted_model,
        **hparams,
    )

    from anodet.utils.run_metadata import RunMetadata, write_result
    meta = RunMetadata(
        experiment="exp6_triage",
        model=a.prompted_model, mode="triage",
        dataset=a.dataset, seed=a.seed,
        **extra.get("run_metadata", {}),
    )
    write_result(
        a.results_root, meta, metrics=metrics, status=status,
        n_rows_scored=extra["n_test"], n_rows_expected=extra["n_test"],
        extra={k: v for k, v in extra.items()
               if k not in {"run_metadata", "n_test"}},
    )
    for pct in (1, 5, 10):
        r = metrics.get(f"k{pct}pct_recall_at_fpr", float("nan"))
        u = metrics.get(f"k{pct}pct_uplift_recall", float("nan"))
        print(f"[exp6] k={pct}%: recall@1%FPR={r:.3f}  uplift={u:+.3f}")


if __name__ == "__main__":
    _cli()
