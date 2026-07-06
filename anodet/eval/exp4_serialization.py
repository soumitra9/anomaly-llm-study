"""Exp 4 — serialization/column-order sensitivity (RQ5).

Prompted scoring of the same rows under different column orders: arbitrary (as-loaded), domain-informed,
and >=2 random-permutation controls. Reports AUROC per ordering (Wilcoxon vs the random controls in analysis).
Labelled an ablation of a domain-informed order — NOT CausalTAD mechanism transfer (PLAN §Exp4).

Grid axes interpretation: `modes` encodes the ordering (arbitrary, domain, random:0, random:1).
Datasets: unsw (semantic named features, real UNSW-NB15) + pima (ODDS; apply_semantic renames int cols before
reorder). creditcard excluded: V1-V28 are PCA features with no semantic ordering by construction.
"""
from __future__ import annotations

import argparse
import time
from typing import Callable, Optional, Sequence

import numpy as np

from anodet.data.odds import load_odds
from anodet.data.serialize import arbitrary_order, random_order, reorder
from anodet.metrics import auprc, auprc_gain, auroc, recall_at_fpr


def _order(X, ordering: str, domain_order: Optional[Sequence[str]]) -> list[str]:
    if ordering == "arbitrary":
        return arbitrary_order(X)
    if ordering == "domain":
        if not domain_order:
            raise ValueError("ordering='domain' requires domain_order in config's domain_orders map")
        return list(domain_order)
    if ordering.startswith("random:"):
        return random_order(X, seed=int(ordering.split(":", 1)[1]))
    raise ValueError(f"unknown ordering {ordering!r} (expected: arbitrary, domain, random:<seed>)")


def _load_data(dataset: str, split_idx: int, n_splits: int = 5, data_dir: str = "data") -> dict:
    """Dispatch to ODDS or security loader based on dataset name."""
    if dataset in ("creditcard-temporal", "creditcard-random"):
        from anodet.data.creditcard import load_creditcard
        split = "temporal" if "temporal" in dataset else "random"
        return load_creditcard(
            f"{data_dir}/creditcard.csv",
            split=split, seed=split_idx, drop_time=True,
        )
    if dataset == "unsw":
        import pandas as pd
        from anodet.data.unsw import prepare_unsw
        return prepare_unsw(pd.read_parquet(f"{data_dir}/unsw.parquet"), seed=split_idx)
    return load_odds(dataset, split_idx=split_idx, n_splits=n_splits)


def _metrics(y, scores) -> dict:
    return {
        "auroc": auroc(y, scores),
        "auprc": auprc(y, scores),
        "auprc_gain": auprc_gain(y, scores),
        "recall_at_1pct_fpr": recall_at_fpr(y, scores, 0.01),
    }


def run_one(
    dataset: str,
    model: str,
    ordering: str = "arbitrary",
    *,
    domain_order: Optional[Sequence[str]] = None,
    split_idx: int = 0,
    n_splits: int = 5,
    n_levels: int = 10,
    batch_size: int = 16,
    device: Optional[str] = None,
    data_dir: str = "data",
) -> tuple[dict, str, dict]:
    """Run one Exp 4 cell. ordering in {arbitrary, domain, random:<seed>}. Returns (metrics, status, extra)."""
    from anodet.scoring.prompted import run_prompted

    start = time.time()

    data = _load_data(dataset, split_idx, n_splits, data_dir)
    y_test = np.asarray(data["y_test"]).astype(int)
    X_test = data["X_test"]

    # For pima (ODDS .mat): columns are integer-indexed (0..7); rename to UCI names before reorder
    # so that domain_order (which uses human-readable names) does not crash on set-mismatch.
    if dataset == "pima":
        from anodet.data.odds_names import apply_semantic
        X_test = apply_semantic(X_test, "pima")

    order = _order(X_test, ordering, domain_order)
    X_reordered = reorder(X_test, order)

    out = run_prompted(
        f"{model}-instruct", X_reordered,
        n_levels=n_levels, batch_size=batch_size, device=device,
    )
    scores = out["scores"]

    metrics = _metrics(y_test, scores)
    sample_weight = data.get("sample_weight")
    if sample_weight is not None:
        # compute weighted recall for security datasets (importance-reweighted)
        metrics["recall_at_1pct_fpr_weighted"] = recall_at_fpr(
            y_test, scores, 0.01, sample_weight=sample_weight
        )

    extra = {
        "ordering": ordering,
        "dataset": dataset,
        "n_rows_scored": int(len(y_test)),
        "n_rows_expected": int(len(y_test)),
        "wall_seconds": time.time() - start,
        "device_used": out.get("device"),
        "content_hash": data.get("content_hash"),
        "run_metadata": {
            "checkpoint_kind": "instruct",
            "dataset_content_hash": data.get("content_hash"),
        },
    }
    return metrics, "complete", extra


def make_run_cell(cfg: dict, **hparams) -> Callable[[dict], tuple[dict, str, dict]]:
    """Bind hyperparameters into a grid run_cell(cell) closure.

    The `modes` axis in the YAML encodes the ordering (not a scoring mode).
    `domain_orders` map in the YAML config supplies the per-dataset domain order.
    """
    domain_orders = cfg.get("domain_orders", {})
    data_dir = hparams.pop("data_dir", "data")

    def run_cell(cell: dict) -> tuple[dict, str, dict]:
        ordering = cell["mode"]  # mode axis encodes the column ordering
        domain_order = domain_orders.get(cell["dataset"])
        return run_one(
            cell["dataset"], cell["model"], ordering,
            domain_order=domain_order,
            split_idx=int(cell["seed"]),
            data_dir=data_dir,
            **hparams,
        )

    return run_cell


def run(config_path: str, results_root: str = "results", **hparams) -> int:
    """Run all pending cells from a YAML config; returns the number of cells run."""
    from anodet.eval import grid
    cfg = grid.load_config(config_path)
    return grid.run_grid(cfg, results_root, make_run_cell(cfg, **hparams))


def _cli():
    p = argparse.ArgumentParser(description="Exp 4 — column-order sensitivity on ODDS/security")
    p.add_argument("--config", default=None, help="YAML config for the full sweep")
    p.add_argument("--dataset", default=None)
    p.add_argument("--model", default="qwen2.5-3b")
    p.add_argument("--ordering", default="arbitrary",
                   choices=["arbitrary", "domain", "random:0", "random:1"])
    p.add_argument("--split-idx", type=int, default=0)
    p.add_argument("--n-splits", type=int, default=5)
    p.add_argument("--n-levels", type=int, default=10)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--device", default=None)
    p.add_argument("--results-root", default="results")
    p.add_argument("--data-dir", default="data")
    a = p.parse_args()

    hparams = dict(n_levels=a.n_levels, batch_size=a.batch_size,
                   device=a.device, n_splits=a.n_splits, data_dir=a.data_dir)

    if a.config:
        n = run(a.config, a.results_root, **hparams)
        print(f"[exp4] ran {n} pending cell(s) from {a.config}")
        return

    if not a.dataset:
        p.error("provide --dataset for a single cell, or --config for the full sweep")

    metrics, status, extra = run_one(
        a.dataset, a.model, a.ordering,
        split_idx=a.split_idx, **hparams,
    )

    from anodet.utils.run_metadata import RunMetadata, write_result
    meta = RunMetadata(
        experiment="exp4_serialization",
        model=a.model, mode=a.ordering,
        dataset=a.dataset, seed=a.split_idx,
        **extra.get("run_metadata", {}),
    )
    write_result(
        a.results_root, meta, metrics=metrics, status=status,
        n_rows_scored=extra["n_rows_scored"], n_rows_expected=extra["n_rows_expected"],
        extra={k: v for k, v in extra.items()
               if k not in {"run_metadata", "n_rows_scored", "n_rows_expected"}},
    )
    print(f"[exp4] {a.dataset} {a.model} {a.ordering} split{a.split_idx}: "
          f"AUROC={metrics['auroc']:.3f} "
          f"recall@1%FPR={metrics['recall_at_1pct_fpr']:.3f} "
          f"wall={extra['wall_seconds']:.1f}s")


if __name__ == "__main__":
    _cli()
