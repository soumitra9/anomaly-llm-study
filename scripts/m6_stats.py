"""M6 — Confirmatory statistics and descriptive summaries for all RQs.

Framing: §1a re-runs the M2 Friedman/Wilcoxon as a *verification* of the pre-registered analysis,
not a new result. §1b-§1e are descriptive only (no per-instance arrays available; n too small for
formal tests). Writes results/tables/m6_stats.json and prints a human-readable summary.

Usage:
    uv run python scripts/m6_stats.py [--results-root results] [--output-dir results]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from anodet.analysis.aggregate import load_rows
from anodet.analysis.stats import average_ranks, friedman, holm_wilcoxon


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_exp_jsons(results_root: pathlib.Path, experiment: str) -> list[dict]:
    exp_dir = results_root / "raw" / experiment
    rows = []
    for p in sorted(exp_dir.glob("*.json")):
        if p.name.startswith("MANIFEST"):
            continue
        d = json.loads(p.read_text())
        if d.get("status") == "complete":
            rows.append(d)
    return rows


def _meta(d: dict) -> dict:
    return d.get("run_metadata", {})


# ---------------------------------------------------------------------------
# §1a — Verify M2 Friedman + Holm-Wilcoxon (RQ2, RQ3)
# Framing: verification of the pre-registered M2 analysis, not a new result.
# Exact confirmed column string values: model in {"smol-360","qwen2.5-3b"},
#   mode in {"likelihood","prompted"}.
# ---------------------------------------------------------------------------

def section_1a(results_root: pathlib.Path) -> dict:
    print("\n=== §1a — M2 verification: Friedman + Holm-Wilcoxon (RQ2, RQ3) ===")
    df = load_rows(str(results_root), "exp2_odds")

    # Pivot: 30 datasets × 4 conditions
    pivot = df.pivot_table(
        index="dataset",
        columns=["model", "mode"],
        values="auroc",
        aggfunc="mean",
    )
    # Flatten MultiIndex columns to "model__mode" strings
    pivot.columns = [f"{model}__{mode}" for model, mode in pivot.columns]
    assert pivot.shape == (30, 4), f"Expected 30x4 pivot, got {pivot.shape}"

    # Friedman omnibus
    fr = friedman(pivot)
    print(f"Friedman: stat={fr['statistic']:.3f}, p={fr['pvalue']:.3e}, k={fr['k']}, n={fr['n']}")

    # Average ranks
    ranks = average_ranks(pivot)
    print("Average ranks:", ranks.to_dict())

    # Holm-Wilcoxon: each method vs smol-360__likelihood (baseline)
    baseline = "smol-360__likelihood"
    hw = holm_wilcoxon(pivot, baseline)
    print(hw[["method", "median_delta", "p_raw", "p_holm", "reject"]].to_string(index=False))

    # Per-condition mean AUROC (for paper)
    means = pivot.mean().to_dict()
    print("Condition means:", {k: round(v, 4) for k, v in means.items()})

    return {
        "friedman": fr,
        "average_ranks": ranks.to_dict(),
        "holm_wilcoxon": hw.to_dict(orient="records"),
        "condition_means": means,
        "note": "Verification of pre-registered M2 analysis, not a new result.",
    }


# ---------------------------------------------------------------------------
# §1b — RQ3b: semantic vs anonymous column names on pima (descriptive)
# Reads JSONs directly; cross-checks against CSV to catch aggregate.py bugs.
# ---------------------------------------------------------------------------

def section_1b(results_root: pathlib.Path) -> dict:
    print("\n=== §1b — RQ3b: semantic vs anon column names (descriptive) ===")
    jsons = _load_exp_jsons(results_root, "exp3b_names")
    assert len(jsons) == 6, f"Expected 6 exp3b cells, got {len(jsons)}"

    by_mode: dict[str, list[float]] = {"anon": [], "semantic": []}
    seed_pairs: list[tuple[float, float]] = []  # (anon, semantic) per seed

    # Sort by mode then seed to ensure consistent ordering
    jsons_sorted = sorted(jsons, key=lambda d: (_meta(d)["mode"], _meta(d)["seed"]))
    for d in jsons_sorted:
        mode = _meta(d)["mode"]
        auroc = d["metrics"]["auroc"]
        by_mode[mode].append(auroc)

    print(f"anon  AUROCs (seeds 0-2): {[round(x, 4) for x in by_mode['anon']]}")
    print(f"seman AUROCs (seeds 0-2): {[round(x, 4) for x in by_mode['semantic']]}")

    anon = np.array(by_mode["anon"])
    sem = np.array(by_mode["semantic"])
    deltas = sem - anon  # positive = semantic better

    mean_anon = float(anon.mean())
    mean_sem = float(sem.mean())
    mean_delta = float(deltas.mean())
    std_delta = float(deltas.std(ddof=1))

    print(f"anon mean={mean_anon:.4f}, semantic mean={mean_sem:.4f}")
    print(f"delta (semantic - anon): {[round(d, 4) for d in deltas]} → mean={mean_delta:.4f}, std={std_delta:.4f}")
    print("Conclusion: null result — semantic names do not help (n=3 pairs; Wilcoxon min p=0.25)")

    # Issue-5 cross-check: means must match exp3b_names.csv
    csv_path = results_root / "tables" / "exp3b_names.csv"
    if csv_path.exists():
        csv = pd.read_csv(csv_path)
        csv_anon = float(csv.loc[csv["mode"] == "anon", "auroc_mean"].iloc[0])
        csv_sem = float(csv.loc[csv["mode"] == "semantic", "auroc_mean"].iloc[0])
        tol = 1e-6
        assert abs(csv_anon - mean_anon) < tol, f"CSV anon mean {csv_anon} != JSON mean {mean_anon}"
        assert abs(csv_sem - mean_sem) < tol, f"CSV semantic mean {csv_sem} != JSON mean {mean_sem}"
        print("Cross-check vs CSV: PASS")

    return {
        "anon_aurocs": list(map(float, anon)),
        "semantic_aurocs": list(map(float, sem)),
        "mean_anon": mean_anon,
        "mean_semantic": mean_sem,
        "per_seed_deltas": list(map(float, deltas)),
        "mean_delta": mean_delta,
        "std_delta": std_delta,
        "note": "Null result. n=3 pairs; Wilcoxon minimum achievable p=0.25 — underpowered. Report descriptively.",
    }


# ---------------------------------------------------------------------------
# §1c — RQ4: security transfer (descriptive)
# Classical (drop-Time): exp3_security_notime CSV.
# LLM modes: exp3_security CSV.
# Metric: recall@1%FPR (different field names in each CSV — reconciled here).
# ---------------------------------------------------------------------------

def section_1c(results_root: pathlib.Path) -> dict:
    print("\n=== §1c — RQ4: security transfer — classical vs LLM (descriptive) ===")

    # Classical (drop-Time corrected for creditcard; notime has no UNSW rows)
    notime = pd.read_csv(results_root / "tables" / "exp3_security_notime.csv")
    # Field: recall_at_1fpr_mean (note: no "pct" in name for notime CSV)

    # LLM + classical (original, includes UNSW)
    sec = pd.read_csv(results_root / "tables" / "exp3_security.csv")
    # LLM fields: recall_at_1pct_fpr_mean

    print("\nClassical recall@1%FPR (drop-Time, creditcard only):")
    notime_iforest = notime[notime["model"] == "iforest"]
    print(notime_iforest[["dataset", "recall_at_1fpr_mean", "recall_at_1fpr_std"]].to_string(index=False))

    print("\nLLM recall@1%FPR (exp3_security, all datasets):")
    llm_sec = sec[sec["mode"].isin(["likelihood", "prompted"])]
    print(llm_sec[["dataset", "model", "mode", "recall_at_1pct_fpr_mean", "recall_at_1pct_fpr_std"]].to_string(index=False))

    print("\nNote: n=2-3 datasets — no Friedman; per-dataset descriptive evidence only.")

    # Build a clean summary for JSON
    summary = []
    for _, row in notime.iterrows():
        summary.append({
            "dataset": row["dataset"],
            "model": row["model"],
            "mode": "classical",
            "source": "exp3_security_notime",
            "recall_at_1pct_fpr_mean": round(float(row["recall_at_1fpr_mean"]), 4),
            "recall_at_1pct_fpr_std": round(float(row["recall_at_1fpr_std"]), 4),
        })
    for _, row in llm_sec.iterrows():
        summary.append({
            "dataset": row["dataset"],
            "model": row["model"],
            "mode": row["mode"],
            "source": "exp3_security",
            "recall_at_1pct_fpr_mean": round(float(row["recall_at_1pct_fpr_mean"]), 4),
            "recall_at_1pct_fpr_std": round(float(row["recall_at_1pct_fpr_std"]), 4),
        })

    return {
        "summary": summary,
        "note": "Classical drop-Time from exp3_security_notime (creditcard only; UNSW has no Time column). "
                "No formal test: n=2-3 datasets insufficient for Friedman/Nemenyi.",
    }


# ---------------------------------------------------------------------------
# §1d — RQ5: serialization ordering effect sizes (descriptive)
# Reads exp4_serialization raw JSONs for per-seed AUROC.
# ---------------------------------------------------------------------------

def section_1d(results_root: pathlib.Path) -> dict:
    print("\n=== §1d — RQ5: serialization ordering effect sizes ===")
    jsons = _load_exp_jsons(results_root, "exp4_serialization")
    assert len(jsons) == 24, f"Expected 24 exp4 cells, got {len(jsons)}"

    records = []
    for d in jsons:
        m = _meta(d)
        records.append({
            "ordering": m["mode"],
            "dataset": m["dataset"],
            "seed": m["seed"],
            "auroc": d["metrics"]["auroc"],
        })
    df = pd.DataFrame(records)

    summary = df.groupby(["ordering", "dataset"])["auroc"].agg(
        mean="mean", std="std", n="count"
    ).round(4).reset_index()
    print(summary.to_string(index=False))

    # Key insight: pima is tied for arbitrary vs domain (both 0.4486)
    pima = df[df["dataset"] == "pima"].groupby("ordering")["auroc"].mean()
    unsw = df[df["dataset"] == "unsw"].groupby("ordering")["auroc"].mean()
    print(f"\npima AUROC by ordering:\n{pima.round(4)}")
    print(f"\nUNSW AUROC by ordering:\n{unsw.round(4)}")

    arb_unsw = float(unsw.get("arbitrary", float("nan")))
    dom_unsw = float(unsw.get("domain", float("nan")))
    effect_arb_vs_dom_unsw = arb_unsw - dom_unsw
    print(f"\nUNSW: arbitrary ({arb_unsw:.4f}) - domain ({dom_unsw:.4f}) = {effect_arb_vs_dom_unsw:.4f}")
    print("Note: pima tied (arbitrary == domain). Wilcoxon underpowered (effective n=3 UNSW seeds).")

    return {
        "per_ordering_per_dataset": summary.to_dict(orient="records"),
        "unsw_arbitrary_auroc": arb_unsw,
        "unsw_domain_auroc": dom_unsw,
        "unsw_effect_arbitrary_minus_domain": round(effect_arb_vs_dom_unsw, 4),
        "note": "pima: arbitrary == domain (0.4486). UNSW shows +0.126 AUROC for arbitrary over domain. "
                "Wilcoxon underpowered at n=3 UNSW seeds (pima tied → effective n=3). Report descriptively.",
    }


# ---------------------------------------------------------------------------
# §1e — RQ7: two-stage triage null result confirmation (descriptive)
# Reads exp6_triage raw JSONs; uses full_triage_results for uplift per seed.
# ---------------------------------------------------------------------------

def section_1e(results_root: pathlib.Path) -> dict:
    print("\n=== §1e — RQ7: triage null result confirmation ===")
    jsons = _load_exp_jsons(results_root, "exp6_triage")
    assert len(jsons) == 9, f"Expected 9 exp6 cells, got {len(jsons)}"

    records = []
    for d in jsons:
        m = _meta(d)
        ftr = d.get("extra", {}).get("full_triage_results", {})
        for k_str, vals in ftr.items():
            k_pct = int(k_str)
            records.append({
                "dataset": m["dataset"],
                "seed": m["seed"],
                "k_pct": k_pct,
                "recall_at_fpr_two_stage": vals["two_stage"]["recall_at_fpr"],
                "recall_at_fpr_classical": vals["classical"]["recall_at_fpr"],
                "uplift_recall": vals["uplift_two_stage_vs_classical"]["recall_at_fpr"],
            })
    df = pd.DataFrame(records)

    summary = df.groupby(["dataset", "k_pct"]).agg(
        uplift_mean=("uplift_recall", "mean"),
        uplift_std=("uplift_recall", "std"),
        recall_two_stage_mean=("recall_at_fpr_two_stage", "mean"),
        recall_classical_mean=("recall_at_fpr_classical", "mean"),
    ).round(4).reset_index()
    print(summary.to_string(index=False))

    k1 = df[df["k_pct"] == 1]
    assert (k1["uplift_recall"] == 0.0).all(), "Expected uplift=0.00 at k=1% across all cells"
    print("\nConfirmed: uplift at k=1% = 0.00 across all 9 cells.")

    return {
        "summary": summary.to_dict(orient="records"),
        "k1pct_uplift_all_zero": bool((k1["uplift_recall"] == 0.0).all()),
        "note": "Negative result confirmed. IForest alone near-ceiling. LLM re-ranking adds zero uplift "
                "at k=1% and is harmful at k=5-10%. Per-seed n=3 per dataset — report mean ± std only.",
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="M6 confirmatory statistics")
    ap.add_argument("--results-root", default="results")
    ap.add_argument("--output-dir", default="results")
    args = ap.parse_args()

    results_root = pathlib.Path(args.results_root)
    output_dir = pathlib.Path(args.output_dir)

    output = {}
    output["rq2_rq3_m2_verification"] = section_1a(results_root)
    output["rq3b_semantic_names"] = section_1b(results_root)
    output["rq4_security_transfer"] = section_1c(results_root)
    output["rq5_ordering"] = section_1d(results_root)
    output["rq7_triage"] = section_1e(results_root)

    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    out_path = tables_dir / "m6_stats.json"
    out_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"\n[m6_stats] Wrote {out_path}")


if __name__ == "__main__":
    main()
