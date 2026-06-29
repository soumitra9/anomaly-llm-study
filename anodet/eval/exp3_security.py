"""Exp 3 — security transfer (RQ4): mode B + classical (+ mode A on creditcard, one model) on real data.

Operational metrics under extreme imbalance (PLAN §7): AUPRC-gain, Precision@top-N, Recall@1%FPR with
Clopper-Pearson CI, all importance-reweighted to the true base rate (the loaders supply `sample_weight`).
`run_one` is a single (dataset, model, mode) cell; wire to `grid.run_grid` via a config like exp2.
[provisional — needs the real creditcard/UNSW downloads; validated by mocked dispatch test now]
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from anodet.metrics import (auprc_gain, clopper_pearson, precision_at_k,
                            recall_at_fpr, recall_at_k)

_LOADERS = {"creditcard": "anodet.data.creditcard", "unsw": "anodet.data.unsw"}


def _load(dataset: str, data_dir: str, **kw):
    if dataset == "creditcard":
        from anodet.data.creditcard import load_creditcard
        return load_creditcard(f"{data_dir}/creditcard.csv", **kw)
    if dataset == "unsw":
        import pandas as pd
        from anodet.data.unsw import prepare_unsw
        return prepare_unsw(pd.read_parquet(f"{data_dir}/unsw.parquet"), **kw)
    raise ValueError(f"unknown security dataset {dataset!r} (have {list(_LOADERS)})")


def _operational_metrics(y, scores, weight, *, n_top: int = 100) -> dict:
    y = np.asarray(y).astype(int)
    rec = recall_at_fpr(y, scores, 0.01, sample_weight=weight)
    n_pos = int(y.sum())
    n_hit = int(round(rec * n_pos))
    lo, hi = clopper_pearson(n_hit, n_pos) if n_pos else (0.0, 0.0)
    return {
        "auprc_gain": auprc_gain(y, scores, sample_weight=weight),
        "recall_at_1pct_fpr": rec,
        "recall_at_1pct_fpr_ci": [lo, hi],
        "precision_at_topN": precision_at_k(y, scores, n_top, sample_weight=weight),
        "recall_at_topN": recall_at_k(y, scores, n_top, sample_weight=weight),
    }


def run_one(dataset: str, model: str, mode: str, *, data_dir: str = "data",
            n_levels: int = 10, batch_size: int = 16, device: Optional[str] = None,
            n_top: int = 100, **load_kw) -> tuple[dict, str, dict]:
    """One security cell. mode in {prompted, classical:<name>, likelihood}. Returns (metrics, status, extra)."""
    data = _load(dataset, data_dir, **load_kw)
    y, w = data["y_test"], data.get("sample_weight")

    if mode == "prompted":
        from anodet.scoring.prompted import run_prompted
        scores = run_prompted(f"{model}-instruct", data["X_test"], n_levels=n_levels,
                              batch_size=batch_size, device=device)["scores"]
    elif mode.startswith("classical:"):
        from anodet.baselines.classical import run_baseline
        scores = run_baseline(mode.split(":", 1)[1], data["X_train"], data["X_test"])
    elif mode == "likelihood":
        from anodet.scoring.likelihood import run_likelihood
        scores = run_likelihood(model, data["X_train"], data["X_test"], lora=True,
                                device=device)["mean"]
    else:
        raise ValueError(f"unknown mode {mode!r}")

    metrics = _operational_metrics(y, scores, w, n_top=n_top)
    extra = {"run_metadata": {"dataset_content_hash": data["content_hash"]},
             "n_rows_scored": int(len(y)), "n_rows_expected": int(len(y)),
             "split": data.get("split"), "flagged_leakage": data.get("flagged")}
    return metrics, "complete", extra
