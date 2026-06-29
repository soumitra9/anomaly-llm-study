"""Statistical tests for the comparisons in PLAN §7.

ODDS (many datasets): Friedman omnibus -> average ranks -> Nemenyi critical difference (replicating
AnoLLM Fig 7). Pre-registered pairwise claims: Holm-corrected Wilcoxon signed-rank. Security (n=2-3
datasets, no Friedman power): per-dataset bootstrap CIs (reuse `metrics.bootstrap_ci`) + effect sizes.

Input convention: a `scores` DataFrame indexed by dataset (rows) with one column per method, entries =
the metric (higher = better, e.g. AUROC). Ranks are computed so **rank 1 = best**.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pandas as pd

# Nemenyi two-tailed q_alpha (studentized range / sqrt(2)) for alpha=0.05, k = #methods (2..10).
_Q05 = {2: 1.960, 3: 2.343, 4: 2.569, 5: 2.728, 6: 2.850, 7: 2.949, 8: 3.031, 9: 3.102, 10: 3.164}


def average_ranks(scores: pd.DataFrame) -> pd.Series:
    """Mean rank per method across datasets; rank 1 = best (highest score). Ties get average ranks."""
    # rank within each dataset (row): highest score -> rank 1
    ranks = scores.rank(axis=1, ascending=False, method="average")
    return ranks.mean(axis=0).sort_values()


def friedman(scores: pd.DataFrame) -> dict:
    """Friedman omnibus across methods (columns) over datasets (rows)."""
    from scipy.stats import friedmanchisquare

    cols = [scores[c].to_numpy() for c in scores.columns]
    stat, p = friedmanchisquare(*cols)
    return {"statistic": float(stat), "pvalue": float(p), "k": scores.shape[1], "n": scores.shape[0]}


def nemenyi_cd(k: int, n: int, alpha: float = 0.05) -> float:
    """Critical difference for the Nemenyi test: q_alpha * sqrt(k(k+1)/(6n))."""
    if alpha != 0.05 or k not in _Q05:
        raise ValueError(f"q table only has alpha=0.05, k in {sorted(_Q05)} (got alpha={alpha}, k={k})")
    return _Q05[k] * math.sqrt(k * (k + 1) / (6.0 * n))


def holm_wilcoxon(scores: pd.DataFrame, baseline: str) -> pd.DataFrame:
    """Wilcoxon signed-rank of each method vs `baseline` across datasets, Holm-corrected across the family.

    Returns a DataFrame: method, statistic, p_raw, p_holm, reject (at 0.05), median_delta (method - baseline).
    """
    from scipy.stats import wilcoxon

    others = [c for c in scores.columns if c != baseline]
    rows = []
    for m in others:
        delta = scores[m].to_numpy() - scores[baseline].to_numpy()
        if np.allclose(delta, 0):
            stat, p = float("nan"), 1.0
        else:
            stat, p = wilcoxon(scores[m].to_numpy(), scores[baseline].to_numpy())
        rows.append({"method": m, "statistic": float(stat), "p_raw": float(p),
                     "median_delta": float(np.median(delta))})
    df = pd.DataFrame(rows).sort_values("p_raw").reset_index(drop=True)
    # Holm step-down: sort ascending p, threshold alpha/(M-i)
    m_tests = len(df)
    p_holm, running = [], 0.0
    for i, p in enumerate(df["p_raw"]):
        adj = min(1.0, p * (m_tests - i))
        running = max(running, adj)  # enforce monotonic non-decreasing
        p_holm.append(running)
    df["p_holm"] = p_holm
    df["reject"] = df["p_holm"] < 0.05
    return df


def bootstrap_delta_ci(y_true, scores_a, scores_b, metric_fn, *, n_boot: int = 1000,
                       seed: int = 0, alpha: float = 0.05) -> dict:
    """Bootstrap CI for metric(a) - metric(b) on the same instances (security per-dataset effect size)."""
    y = np.asarray(y_true)
    a, b = np.asarray(scores_a), np.asarray(scores_b)
    rng = np.random.default_rng(seed)
    n = len(y)
    deltas = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        deltas.append(metric_fn(y[idx], a[idx]) - metric_fn(y[idx], b[idx]))
    lo, hi = np.quantile(deltas, [alpha / 2, 1 - alpha / 2])
    return {"delta": float(metric_fn(y, a) - metric_fn(y, b)), "lo": float(lo), "hi": float(hi),
            "excludes_zero": bool(lo > 0 or hi < 0)}
