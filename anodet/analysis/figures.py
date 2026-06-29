"""Figures built from aggregated tables (matplotlib, headless). PLAN §7/§13.

- `cd_diagram`: average-rank axis with a Nemenyi critical-difference bar (AnoLLM Fig 7 style).
- `pareto`: accuracy vs cost scatter with the Pareto frontier highlighted (Exp 5).
- `per_dataset_bars`: per-dataset metric bars for two methods.

[provisional] — these render correctly on synthetic input; visual polish happens in Phase B on real data.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless / Kaggle-safe
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from anodet.analysis.stats import average_ranks, nemenyi_cd  # noqa: E402


def cd_diagram(scores: pd.DataFrame, out_path: str, *, alpha: float = 0.05) -> Path:
    """Average ranks of each method with a critical-difference bar (lower rank = better)."""
    ranks = average_ranks(scores)
    cd = nemenyi_cd(scores.shape[1], scores.shape[0], alpha)
    fig, ax = plt.subplots(figsize=(7, 2 + 0.3 * len(ranks)))
    ax.scatter(ranks.values, range(len(ranks)))
    ax.set_yticks(range(len(ranks)))
    ax.set_yticklabels(ranks.index)
    ax.set_xlabel("average rank (1 = best)")
    ax.set_title(f"Critical-difference (Nemenyi CD={cd:.2f}, n={scores.shape[0]}, k={scores.shape[1]})")
    best = ranks.iloc[0]
    ax.axvspan(best, best + cd, alpha=0.15, color="grey")  # CD band from the best
    fig.tight_layout()
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return p


def pareto(df: pd.DataFrame, out_path: str, *, acc: str = "auroc", cost: str = "cost",
           label: str = "method") -> Path:
    """Scatter accuracy vs cost; highlight the Pareto frontier (high acc, low cost)."""
    d = df.sort_values(cost).reset_index(drop=True)
    frontier, best_acc = [], -np.inf
    for _, r in d.iterrows():
        if r[acc] > best_acc:
            frontier.append(r); best_acc = r[acc]
    fr = pd.DataFrame(frontier)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(d[cost], d[acc])
    if label in d.columns:
        for _, r in d.iterrows():
            ax.annotate(str(r[label]), (r[cost], r[acc]), fontsize=7)
    ax.plot(fr[cost], fr[acc], "r--", label="Pareto frontier")
    ax.set_xlabel(cost); ax.set_ylabel(acc); ax.legend()
    ax.set_title("Accuracy vs cost")
    fig.tight_layout()
    p = Path(out_path); p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, dpi=150); plt.close(fig)
    return p


def per_dataset_bars(scores: pd.DataFrame, out_path: str) -> Path:
    """Grouped bars: one cluster per dataset (rows), one bar per method (columns)."""
    fig, ax = plt.subplots(figsize=(2 + 0.5 * len(scores), 4))
    scores.plot(kind="bar", ax=ax)
    ax.set_ylabel("metric"); ax.set_title("Per-dataset comparison")
    fig.tight_layout()
    p = Path(out_path); p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, dpi=150); plt.close(fig)
    return p
