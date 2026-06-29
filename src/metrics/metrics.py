"""Operational anomaly-detection metrics (PLAN §6).

Conventions
-----------
- `y_true`: 1 = anomaly (positive class), 0 = normal. Higher `scores` = more anomalous.
- AUROC/AUPRC use sklearn (tie-aware: tied scores get averaged ranks; we never break ties
  before ranking).
- For severe imbalance, AUPRC is reported alongside the no-skill baseline (= prevalence) and
  as a gain ratio.
- Importance reweighting (`sample_weight`) recovers true-base-rate AUPRC/FPR when negatives
  were subsampled for scoring cost (PLAN §2c).
- Top-N operating points use a stable, documented tie-break at the cutoff (report the number
  of distinct score levels separately as a diagnostic).
"""
from __future__ import annotations

from typing import Callable, Optional

import numpy as np
from scipy.stats import beta
from sklearn.metrics import average_precision_score, roc_auc_score, roc_curve

from src.utils.seeding import rng

_ArrayLike = np.ndarray


def _as_arrays(y_true, scores, sample_weight=None):
    y = np.asarray(y_true).astype(float).ravel()
    s = np.asarray(scores).astype(float).ravel()
    w = None if sample_weight is None else np.asarray(sample_weight).astype(float).ravel()
    return y, s, w


def prevalence(y_true, sample_weight: Optional[_ArrayLike] = None) -> float:
    """Weighted positive base rate."""
    y, _, w = _as_arrays(y_true, y_true, sample_weight)
    if w is None:
        return float(y.mean())
    return float(np.sum(y * w) / np.sum(w))


def auroc(y_true, scores, sample_weight: Optional[_ArrayLike] = None) -> float:
    """Tie-aware AUROC (Mann-Whitney). NaN if only one class present."""
    y, s, w = _as_arrays(y_true, scores, sample_weight)
    if len(np.unique(y)) < 2:
        return float("nan")
    return float(roc_auc_score(y, s, sample_weight=w))


def auprc(y_true, scores, sample_weight: Optional[_ArrayLike] = None) -> float:
    """Average precision (area under PR curve)."""
    y, s, w = _as_arrays(y_true, scores, sample_weight)
    if len(np.unique(y)) < 2:
        return float("nan")
    return float(average_precision_score(y, s, sample_weight=w))


def no_skill_auprc(y_true, sample_weight: Optional[_ArrayLike] = None) -> float:
    """No-skill (random-ranker) AUPRC baseline = prevalence."""
    return prevalence(y_true, sample_weight)


def auprc_gain(y_true, scores, sample_weight: Optional[_ArrayLike] = None) -> float:
    """AUPRC / prevalence — interpretable across datasets with different base rates."""
    base = no_skill_auprc(y_true, sample_weight)
    if base <= 0:
        return float("nan")
    return auprc(y_true, scores, sample_weight) / base


def make_importance_weights(y_true, n_neg_total: int) -> np.ndarray:
    """Weights that recover true-base-rate metrics when negatives were subsampled.

    Positives keep weight 1; each sampled negative is upweighted by
    `n_neg_total / n_neg_sampled` so the weighted negative mass equals the full population.
    """
    y = np.asarray(y_true).astype(int).ravel()
    n_neg_sampled = int((y == 0).sum())
    if n_neg_sampled == 0:
        raise ValueError("no negatives in sample")
    w_neg = float(n_neg_total) / n_neg_sampled
    w = np.ones_like(y, dtype=float)
    w[y == 0] = w_neg
    return w


def _topk_indices(scores: np.ndarray, k: int) -> np.ndarray:
    """Indices of the top-k by score, descending, stable tie-break (deterministic)."""
    k = max(0, min(int(k), len(scores)))
    # stable sort on negated scores keeps original order among ties at the cutoff
    order = np.argsort(-scores, kind="stable")
    return order[:k]


def precision_at_k(y_true, scores, k: int, sample_weight: Optional[_ArrayLike] = None) -> float:
    """Precision among the top-k highest-scoring rows (an analyst's fixed alert budget)."""
    y, s, w = _as_arrays(y_true, scores, sample_weight)
    idx = _topk_indices(s, k)
    if len(idx) == 0:
        return float("nan")
    if w is None:
        return float(y[idx].mean())
    return float(np.sum(y[idx] * w[idx]) / np.sum(w[idx]))


def recall_at_k(y_true, scores, k: int, sample_weight: Optional[_ArrayLike] = None) -> float:
    """Fraction of all (weighted) positives captured within the top-k rows."""
    y, s, w = _as_arrays(y_true, scores, sample_weight)
    idx = _topk_indices(s, k)
    if w is None:
        total_pos = y.sum()
        return float(y[idx].sum() / total_pos) if total_pos > 0 else float("nan")
    total_pos = np.sum(y * w)
    return float(np.sum(y[idx] * w[idx]) / total_pos) if total_pos > 0 else float("nan")


def recall_at_fpr(
    y_true, scores, target_fpr: float = 0.01, sample_weight: Optional[_ArrayLike] = None
) -> float:
    """Recall (TPR) at the operating point whose FPR is as large as possible but <= target.

    With few negatives the FPR grid is coarse (e.g. 50 negatives -> steps of 0.02); then the
    only point with FPR <= 1% is FPR = 0 (threshold above every negative), i.e. recall at zero
    false positives — a well-defined, strict answer.
    """
    y, s, w = _as_arrays(y_true, scores, sample_weight)
    if len(np.unique(y)) < 2:
        return float("nan")
    fpr, tpr, _ = roc_curve(y, s, sample_weight=w)
    mask = fpr <= target_fpr + 1e-12
    if not mask.any():
        return 0.0
    return float(tpr[mask].max())


def recall_at_fixed_false_alarms(
    y_true, scores, n_false_alarms: int, sample_weight: Optional[_ArrayLike] = None
) -> float:
    """Recall when the analyst tolerates exactly `n_false_alarms` false positives.

    Sampling-robust under reweighting: converts an absolute false-alarm budget into the
    equivalent FPR target and reuses `recall_at_fpr`.
    """
    y, _, w = _as_arrays(y_true, scores, sample_weight)
    neg_mass = float(np.sum((1 - y) * (w if w is not None else 1.0)))
    if neg_mass <= 0:
        return float("nan")
    return recall_at_fpr(y_true, scores, target_fpr=n_false_alarms / neg_mass, sample_weight=sample_weight)


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact (Clopper-Pearson) binomial CI for a proportion k/n at level 1-alpha."""
    if n == 0:
        return (0.0, 1.0)
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return (lo, hi)


def bootstrap_ci(
    metric_fn: Callable[..., float],
    y_true,
    scores,
    *,
    n_boot: int = 1000,
    seed: int = 0,
    alpha: float = 0.05,
    sample_weight: Optional[_ArrayLike] = None,
) -> tuple[float, float, float]:
    """Percentile bootstrap CI over test instances. Returns (point, lo, hi). Deterministic."""
    y, s, w = _as_arrays(y_true, scores, sample_weight)
    n = len(y)
    point = metric_fn(y, s, sample_weight=w) if w is not None else metric_fn(y, s)
    gen = rng(seed, f"bootstrap:{metric_fn.__name__}")
    vals = []
    for _ in range(n_boot):
        idx = gen.integers(0, n, size=n)
        try:
            v = metric_fn(y[idx], s[idx], sample_weight=(w[idx] if w is not None else None))
        except Exception:
            v = np.nan
        vals.append(v)
    arr = np.asarray(vals, dtype=float)
    arr = arr[~np.isnan(arr)]
    if arr.size == 0:
        return (point, float("nan"), float("nan"))
    lo = float(np.percentile(arr, 100 * alpha / 2))
    hi = float(np.percentile(arr, 100 * (1 - alpha / 2)))
    return (point, lo, hi)
