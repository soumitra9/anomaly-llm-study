"""Regenerate results/figures/* from aggregated tables + results/raw/ (deterministic; PLAN §10).

Best-effort: builds whatever figures the available tables support (e.g. exp2 CD diagram once exp2_odds.csv
exists). Safe to run early — it skips figures whose inputs are not present yet.
Usage:  uv run python scripts/make_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from anodet.analysis.figures import cd_diagram, per_dataset_bars

RESULTS = "results"
RV2_DATASETS = [
    "arrhythmia", "breastw", "cardio", "ionosphere",
    "shuttle", "speech", "vertebral", "yeast",
]


def _rv2_pivot(results_root: Path) -> pd.DataFrame | None:
    fs = results_root / "tables" / "exp2_fewshot.csv"
    zs = results_root / "tables" / "exp2_odds.csv"
    if not fs.exists() or not zs.exists():
        return None
    fs_df = pd.read_csv(fs)
    zs_df = pd.read_csv(zs)
    lk_df = zs_df[(zs_df["model"] == "qwen2.5-3b") & (zs_df["mode"] == "likelihood")]
    fs_df = fs_df[fs_df["mode"] == "prompted-fewshot"]
    zs_df = zs_df[(zs_df["model"] == "qwen2.5-3b") & (zs_df["mode"] == "prompted")]
    rows = []
    for ds in RV2_DATASETS:
        row = {"dataset": ds}
        for label, sub in [("zero_shot", zs_df), ("few_shot", fs_df), ("likelihood", lk_df)]:
            v = sub.loc[sub["dataset"] == ds, "auroc_mean"]
            if len(v) == 1:
                row[label] = float(v.iloc[0])
        if len(row) > 1:
            rows.append(row)
    if not rows:
        return None
    pivot = pd.DataFrame(rows).set_index("dataset")[["zero_shot", "few_shot", "likelihood"]]
    return pivot.reindex(RV2_DATASETS).dropna(how="all")


def main() -> int:
    figdir = Path(RESULTS) / "figures"
    tables = Path(RESULTS) / "tables"
    made = 0

    exp2 = tables / "exp2_odds.csv"
    if exp2.exists():
        df = pd.read_csv(exp2)
        if {"dataset", "model", "mode", "auroc_mean"} <= set(df.columns):
            df = df.assign(method=df["model"] + ":" + df["mode"])
            pivot = df.pivot_table(index="dataset", columns="method", values="auroc_mean")
            if pivot.shape[1] >= 2 and pivot.shape[0] >= 2:
                out = cd_diagram(pivot.dropna(), str(figdir / "exp2_cd_diagram.png"))
                print(f"[figures] {out}"); made += 1

    rv2 = _rv2_pivot(Path(RESULTS))
    if rv2 is not None and not rv2.empty:
        out = per_dataset_bars(
            rv2,
            str(figdir / "rv2_fewshot_vs_zeroshot.png"),
            ylabel="AUROC (mean over 3 seeds)",
            title="RV2: zero-shot vs few-shot vs likelihood (8 ODDS datasets)",
        )
        print(f"[figures] {out}"); made += 1

    sec = tables / "exp3_security.csv"
    if sec.exists():
        unsw = pd.read_csv(sec)
        unsw = unsw[(unsw["dataset"] == "unsw") & (unsw["model"] == "qwen2.5-3b")
                    & (unsw["mode"].isin(["likelihood", "prompted"]))]
        if not unsw.empty:
            bar_df = unsw.groupby("mode")["recall_at_1pct_fpr_mean"].mean().to_frame("recall@1%FPR").T
            out = per_dataset_bars(
                bar_df,
                str(figdir / "rv1_unsw_likelihood.png"),
                ylabel="recall@1%FPR (mean over seeds)",
                title="RV1: UNSW likelihood vs prompted",
            )
            print(f"[figures] {out}"); made += 1

    if not made:
        print("[figures] no inputs ready yet (run `make tables` after results land)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
