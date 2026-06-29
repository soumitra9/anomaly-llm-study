"""Exp 3b — semantic vs anonymized column names (RQ3b).

Same model/mode/split, prompted scoring on `pima` (breastw backup) with (a) real UCI semantic column names
vs (b) anonymized col_0..col_n. The RQ3b effect is Δ AUROC (semantic − anonymized), bootstrap-CI'd in analysis.
`run_one` scores one arm; the pair is run as two cells and differenced.
[provisional — needs UCI-order verification (odds_names guard) + GPU; mocked dispatch test now]
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from anodet.data.odds import load_odds
from anodet.data.odds_names import anonymize, apply_semantic
from anodet.metrics import auroc


def run_one(dataset: str = "pima", arm: str = "semantic", model: str = "qwen3-4b", *,
            split_idx: int = 0, n_levels: int = 10, batch_size: int = 16,
            device: Optional[str] = None) -> tuple[dict, str, dict]:
    """One arm ('semantic'|'anon'). Returns (metrics, status, extra)."""
    from anodet.scoring.prompted import run_prompted

    data = load_odds(dataset, split_idx=split_idx)
    X = data["X_test"]
    if arm == "semantic":
        X = apply_semantic(X, dataset)   # raises if UCI name count != columns (alignment guard)
    elif arm == "anon":
        X = anonymize(X)
    else:
        raise ValueError(f"arm must be 'semantic' or 'anon' (got {arm!r})")

    scores = run_prompted(f"{model}-instruct", X, n_levels=n_levels,
                          batch_size=batch_size, device=device)["scores"]
    metrics = {"auroc": auroc(np.asarray(data["y_test"]).astype(int), scores)}
    extra = {"run_metadata": {"dataset_content_hash": data["content_hash"]},
             "arm": arm, "n_rows_scored": int(len(data["y_test"]))}
    return metrics, "complete", extra
