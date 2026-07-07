"""M6 — Paper figures for security transfer (RQ4) and ordering sensitivity (RQ5).

Usage:
    uv run python scripts/m6_figures.py [--results-root results] [--output-dir results]

Outputs:
    results/figures/exp3_security_bars.png  -- recall@1%FPR: best-classical vs LLM modes (RQ4)
    results/figures/exp4_ordering.png       -- AUROC by column ordering, pima vs UNSW (RQ5)
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Figure 2 — Security operational metrics bar chart (RQ4)
# x-axis: dataset; y-axis: recall@1%FPR
# Bar groups: ecod (best classical by notime), iforest, qwen-likelihood, qwen-prompted
# Classical creditcard: from exp3_security_notime (drop-Time corrected).
# Classical UNSW: from exp3_security (no Time column on UNSW).
# LLM: from exp3_security.
# ---------------------------------------------------------------------------

def figure_security_bars(results_root: pathlib.Path, out_path: pathlib.Path) -> None:
    notime = pd.read_csv(results_root / "tables" / "exp3_security_notime.csv")
    sec = pd.read_csv(results_root / "tables" / "exp3_security.csv")

    # Select methods to show: best two classicals + two LLMs
    # notime: drop-Time corrected creditcard. UNSW classical from exp3_security.
    datasets = ["creditcard-random", "creditcard-temporal", "unsw"]

    # Build unified recall table: rows = (dataset, method_label), cols = mean/std
    rows = []

    # Classical from notime (creditcard only) — iforest + ecod (the two highest performers)
    for det in ["iforest", "ecod"]:
        sub = notime[notime["model"] == det]
        for ds in ["creditcard-random", "creditcard-temporal"]:
            cell = sub[sub["dataset"] == ds]
            if cell.empty:
                continue
            rows.append({
                "dataset": ds,
                "method": f"classical:{det}",
                "mean": float(cell["recall_at_1fpr_mean"].iloc[0]),
                "std": float(cell["recall_at_1fpr_std"].iloc[0]),
            })

    # Classical from exp3_security for UNSW (iforest + ecod)
    for det_mode in ["classical:iforest", "classical:ecod"]:
        sub = sec[sec["mode"] == det_mode]
        cell = sub[sub["dataset"] == "unsw"]
        if cell.empty:
            continue
        rows.append({
            "dataset": "unsw",
            "method": det_mode,
            "mean": float(cell["recall_at_1pct_fpr_mean"].iloc[0]),
            "std": float(cell["recall_at_1pct_fpr_std"].iloc[0]),
        })

    # LLM modes from exp3_security (qwen only — primary model)
    for mode in ["likelihood", "prompted"]:
        sub = sec[(sec["mode"] == mode) & (sec["model"] == "qwen2.5-3b")]
        for ds in datasets:
            cell = sub[sub["dataset"] == ds]
            if cell.empty:
                # likelihood not run on UNSW — skip
                continue
            rows.append({
                "dataset": ds,
                "method": f"qwen:{mode}",
                "mean": float(cell["recall_at_1pct_fpr_mean"].iloc[0]),
                "std": float(cell["recall_at_1pct_fpr_std"].iloc[0]),
            })

    df = pd.DataFrame(rows)

    method_order = ["classical:ecod", "classical:iforest", "qwen:likelihood", "qwen:prompted"]
    method_labels = {
        "classical:ecod": "ECOD",
        "classical:iforest": "IForest",
        "qwen:likelihood": "Qwen-L",
        "qwen:prompted": "Qwen-P",
    }
    dataset_labels = {
        "creditcard-random": "CC-random",
        "creditcard-temporal": "CC-temporal",
        "unsw": "UNSW-NB15",
    }

    n_datasets = len(datasets)
    n_methods = len(method_order)
    x = np.arange(n_datasets)
    width = 0.18
    offsets = np.linspace(-(n_methods - 1) / 2, (n_methods - 1) / 2, n_methods) * width

    fig, ax = plt.subplots(figsize=(8, 4))
    for i, method in enumerate(method_order):
        means, stds = [], []
        for ds in datasets:
            sub = df[(df["dataset"] == ds) & (df["method"] == method)]
            if sub.empty:
                means.append(0.0)
                stds.append(0.0)
            else:
                means.append(float(sub["mean"].iloc[0]))
                stds.append(float(sub["std"].iloc[0]))
        ax.bar(
            x + offsets[i], means, width,
            yerr=stds, capsize=3,
            label=method_labels[method],
        )

    ax.set_xticks(x)
    ax.set_xticklabels([dataset_labels[d] for d in datasets])
    ax.set_ylabel("Recall @ 1% FPR")
    ax.set_ylim(0, 1.0)
    ax.set_title("RQ4 — Security transfer: classical vs LLM at fixed alert budget\n"
                 "(classical creditcard: drop-Time corrected; LLM: qwen2.5-3b)")
    ax.legend(loc="upper right", fontsize=8)
    ax.axhline(0, color="black", linewidth=0.5)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[m6_figures] Wrote {out_path}")


# ---------------------------------------------------------------------------
# Figure 3 — Ordering sensitivity (RQ5)
# Two subplots: pima (left) and UNSW (right).
# x-axis: ordering; y-axis: AUROC; error bars = SD over 3 seeds.
# ---------------------------------------------------------------------------

def figure_ordering(results_root: pathlib.Path, out_path: pathlib.Path) -> None:
    df = pd.read_csv(results_root / "tables" / "exp4_serialization.csv")

    # ordering display names and order
    ordering_order = ["arbitrary", "random:0", "random:1", "domain"]
    ordering_labels = {
        "arbitrary": "Arbitrary",
        "random:0": "Random-0",
        "random:1": "Random-1",
        "domain": "Domain",
    }

    datasets = ["pima", "unsw"]
    dataset_titles = {"pima": "Pima (8 cols)", "unsw": "UNSW-NB15 (47 cols)"}

    fig, axes = plt.subplots(1, 2, figsize=(9, 4), sharey=False)

    for ax, ds in zip(axes, datasets):
        sub = df[df["dataset"] == ds].set_index("mode")
        means = [float(sub.loc[o, "auroc_mean"]) if o in sub.index else 0.0
                 for o in ordering_order]
        stds = [float(sub.loc[o, "auroc_std"]) if o in sub.index else 0.0
                for o in ordering_order]

        x = np.arange(len(ordering_order))
        ax.bar(x, means, 0.55, yerr=stds, capsize=4,
               color=["#4c72b0", "#dd8452", "#55a868", "#c44e52"])
        ax.set_xticks(x)
        ax.set_xticklabels([ordering_labels[o] for o in ordering_order], fontsize=9)
        ax.set_title(dataset_titles[ds])
        ax.set_ylabel("AUROC (mean ± SD, 3 seeds)")
        ax.set_ylim(0.35, 0.80)

    fig.suptitle("RQ5 — Serialization column ordering: does domain-expert order help?",
                 fontsize=11)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[m6_figures] Wrote {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="M6 paper figures")
    ap.add_argument("--results-root", default="results")
    ap.add_argument("--output-dir", default="results")
    args = ap.parse_args()

    results_root = pathlib.Path(args.results_root)
    figs_dir = pathlib.Path(args.output_dir) / "figures"

    figure_security_bars(results_root, figs_dir / "exp3_security_bars.png")
    figure_ordering(results_root, figs_dir / "exp4_ordering.png")


if __name__ == "__main__":
    main()
