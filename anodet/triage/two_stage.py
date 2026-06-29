"""Two-stage classical -> LLM triage/rerank (Exp 6 / RQ7) — the constructive result.

A cheap classical detector (IForest/ECOD) selects the top-K candidates (the alert budget); the LLM re-scores
only that shortlist. We compare the operating point of the **two-stage** system vs **classical-alone** vs
**LLM-alone** at a matched budget — using the already-computed mode-B scores, so the second stage is cheap.
If Exp 3 shows LLMs weak standalone, a positive two-stage result is the paper's constructive headline.

Pure / no-GPU: takes precomputed score arrays. Reuses `anodet.metrics`.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from anodet.metrics import precision_at_k, recall_at_fpr, recall_at_k


def two_stage_scores(classical: np.ndarray, llm: np.ndarray, *, k: int) -> np.ndarray:
    """Combined score: classical picks the top-k shortlist; within it the LLM order decides; the rest rank below.

    Implemented as: rank candidates by LLM score (kept in the top band), push non-candidates strictly below by
    subtracting an offset larger than any LLM score. Preserves a single 1-D score usable by every metric.
    """
    classical, llm = np.asarray(classical, float), np.asarray(llm, float)
    n = len(classical)
    k = max(0, min(k, n))
    cand = np.argpartition(-classical, k - 1)[:k] if k > 0 else np.array([], dtype=int)
    out = llm.copy().astype(float)
    mask = np.ones(n, dtype=bool)
    mask[cand] = False
    if mask.any():
        out[mask] = llm.min() - 1.0 - (llm.max() - llm.min())  # strictly below any candidate's LLM score
    return out


def evaluate_triage(
    y_true: np.ndarray,
    classical: np.ndarray,
    llm: np.ndarray,
    *,
    k: int,
    n_top: Optional[int] = None,
    target_fpr: float = 0.01,
    sample_weight: Optional[np.ndarray] = None,
) -> dict:
    """Operating-point comparison of classical-alone / llm-alone / two-stage.

    `k` = the classical shortlist (the cheap pre-filter); `n_top` = the tight alert budget actually reviewed
    (default k//4, must be <= k). Two-stage's gain shows at `n_top`: the LLM re-orders within the shortlist so
    its top is enriched. Returns per-strategy recall@target_fpr, precision@n_top, recall@n_top + uplift.
    """
    y = np.asarray(y_true).astype(int)
    n_top = max(1, k // 4) if n_top is None else n_top
    two = two_stage_scores(classical, llm, k=k)

    def row(s):
        return {
            "recall_at_fpr": recall_at_fpr(y, s, target_fpr, sample_weight=sample_weight),
            "precision_at_k": precision_at_k(y, s, n_top, sample_weight=sample_weight),
            "recall_at_k": recall_at_k(y, s, n_top, sample_weight=sample_weight),
        }

    res = {"classical": row(classical), "llm": row(llm), "two_stage": row(two),
           "k": int(k), "n_top": int(n_top)}
    res["uplift_two_stage_vs_classical"] = {
        m: res["two_stage"][m] - res["classical"][m] for m in res["classical"]
    }
    return res
