"""Exp 4 — serialization/column-order sensitivity (RQ5).

Prompted scoring of the same rows under different column orders: arbitrary (as-loaded), domain-informed,
and >=2 random-permutation controls. Reports AUROC per ordering (Wilcoxon vs the random controls in analysis).
Labelled an ablation of a domain-informed order — NOT CausalTAD mechanism transfer (PLAN §Exp4).
[provisional — needs GPU + a chosen domain order per dataset; mocked dispatch test now]
"""
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np

from anodet.data.odds import load_odds
from anodet.data.serialize import arbitrary_order, random_order, reorder
from anodet.metrics import auroc


def _order(X, ordering: str, domain_order: Optional[Sequence[str]]):
    if ordering == "arbitrary":
        return arbitrary_order(X)
    if ordering == "domain":
        if not domain_order:
            raise ValueError("ordering='domain' requires domain_order")
        return list(domain_order)
    if ordering.startswith("random:"):
        return random_order(X, seed=int(ordering.split(":", 1)[1]))
    raise ValueError(f"unknown ordering {ordering!r}")


def run_one(dataset: str, model: str, ordering: str = "arbitrary", *,
            domain_order: Optional[Sequence[str]] = None, split_idx: int = 0,
            n_levels: int = 10, batch_size: int = 16,
            device: Optional[str] = None) -> tuple[dict, str, dict]:
    """One ordering cell. ordering in {arbitrary, domain, random:<seed>}. Returns (metrics, status, extra)."""
    from anodet.scoring.prompted import run_prompted

    data = load_odds(dataset, split_idx=split_idx)
    order = _order(data["X_test"], ordering, domain_order)
    X = reorder(data["X_test"], order)
    scores = run_prompted(f"{model}-instruct", X, n_levels=n_levels,
                          batch_size=batch_size, device=device)["scores"]
    metrics = {"auroc": auroc(np.asarray(data["y_test"]).astype(int), scores)}
    extra = {"ordering": ordering, "n_rows_scored": int(len(data["y_test"]))}
    return metrics, "complete", extra
