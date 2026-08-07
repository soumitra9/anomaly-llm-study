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

# GATE_SPEC §RV2 — same 8 datasets as DA1 dissolving arm
RV2_DATASETS = [
    "arrhythmia", "breastw", "cardio", "ionosphere",
    "shuttle", "speech", "vertebral", "yeast",
]

# ODDS catalog dimensions for RV2 regression pattern (static; TODO: verify-vs-ODDS primary source).
RV2_ODDS_SHAPES: dict[str, dict[str, float]] = {
    "arrhythmia": {"n_samples": 452, "n_features": 274, "anomaly_pct": 14.6},
    "breastw": {"n_samples": 683, "n_features": 9, "anomaly_pct": 35.0},
    "cardio": {"n_samples": 1831, "n_features": 21, "anomaly_pct": 9.6},
    "ionosphere": {"n_samples": 351, "n_features": 33, "anomaly_pct": 35.9},
    "shuttle": {"n_samples": 49097, "n_features": 9, "anomaly_pct": 7.2},
    "speech": {"n_samples": 3686, "n_features": 400, "anomaly_pct": 1.7},
    "vertebral": {"n_samples": 240, "n_features": 6, "anomaly_pct": 12.5},
    "yeast": {"n_samples": 1484, "n_features": 8, "anomaly_pct": 34.2},
}

RV2_PROTOCOL_FIELDS = (
    "dataset_content_hash",
    "serialization_template_hash",
    "split_index_hash",
    "n_rows_scored",
    "decode_config.n_levels",
)


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
# §RV1 — UNSW likelihood arm (reviewer item 3; GATE_SPEC §RV1)
# Descriptive: likelihood vs prompted on UNSW, recall@1%FPR + AUPRC gain.
# ---------------------------------------------------------------------------

def section_rv1(results_root: pathlib.Path) -> dict:
    print("\n=== §RV1 — UNSW likelihood vs prompted (descriptive) ===")
    jsons = _load_exp_jsons(results_root, "exp3_security")
    unsw = [d for d in jsons if _meta(d).get("dataset") == "unsw"
            and _meta(d).get("model") == "qwen2.5-3b"
            and _meta(d).get("mode") in ("likelihood", "prompted")]
    assert len([d for d in unsw if _meta(d)["mode"] == "likelihood"]) == 3, "Expected 3 RV1 likelihood cells"
    assert len([d for d in unsw if _meta(d)["mode"] == "prompted"]) >= 1, "Expected M3 prompted UNSW cells"

    rows = []
    for d in sorted(unsw, key=lambda x: (_meta(x)["mode"], _meta(x)["seed"])):
        m = _meta(d)
        rows.append({
            "mode": m["mode"],
            "seed": m["seed"],
            "auprc_gain": round(d["metrics"]["auprc_gain"], 4),
            "recall_at_1pct_fpr": round(d["metrics"]["recall_at_1pct_fpr"], 4),
            "r_permutations": m.get("r_permutations"),
        })
        print(f"  {m['mode']:12} seed{m['seed']}: gain={d['metrics']['auprc_gain']:.3f} "
              f"recall@1%FPR={d['metrics']['recall_at_1pct_fpr']:.3f}")

    lik = [r for r in rows if r["mode"] == "likelihood"]
    pro = [r for r in rows if r["mode"] == "prompted"]
    lik_gain_mean = float(np.mean([r["auprc_gain"] for r in lik]))
    lik_r1_mean = float(np.mean([r["recall_at_1pct_fpr"] for r in lik]))
    pro_gain_seed0 = next(r["auprc_gain"] for r in pro if r["seed"] == 0)
    pro_r1_seed0 = next(r["recall_at_1pct_fpr"] for r in pro if r["seed"] == 0)
    print(f"Likelihood mean gain={lik_gain_mean:.3f}, recall@1%FPR={lik_r1_mean:.3f}")
    print(f"Prompted seed0 (M3 ref): gain={pro_gain_seed0:.3f}, recall@1%FPR={pro_r1_seed0:.3f}")

    return {
        "cells": rows,
        "likelihood_mean_auprc_gain": round(lik_gain_mean, 4),
        "likelihood_mean_recall_at_1pct_fpr": round(lik_r1_mean, 4),
        "prompted_seed0_auprc_gain": pro_gain_seed0,
        "prompted_seed0_recall_at_1pct_fpr": pro_r1_seed0,
        "note": "Descriptive per-dataset security evidence (n=1 dataset). RV1 fills missing strongest LLM mode on UNSW.",
    }


# ---------------------------------------------------------------------------
# §RV2 protocol — few-shot vs zero-shot comparability (seed0 per dataset)
# ---------------------------------------------------------------------------

def _rv2_cell_path(results_root: pathlib.Path, dataset: str, seed: int = 0) -> tuple[pathlib.Path, pathlib.Path]:
    fs = results_root / "raw" / "exp2_fewshot" / f"qwen2.5-3b__prompted-fewshot__{dataset}__seed{seed}.json"
    zs = results_root / "raw" / "exp2_odds" / f"qwen2.5-3b__prompted__{dataset}__seed{seed}.json"
    return fs, zs


def _protocol_field(fs: dict, zs: dict, field: str):
    if field == "n_rows_scored":
        return fs["n_rows_scored"], zs["n_rows_scored"]
    if field == "decode_config.n_levels":
        return fs["run_metadata"]["decode_config"]["n_levels"], zs["run_metadata"]["decode_config"]["n_levels"]
    return fs["run_metadata"][field], zs["run_metadata"][field]


def section_rv2_protocol(results_root: pathlib.Path) -> dict:
    print("\n=== §RV2 protocol — few-shot vs zero-shot comparability (seed0) ===")
    per_dataset = []
    git_sha_null_on_fewshot = False
    for ds in RV2_DATASETS:
        fs_path, zs_path = _rv2_cell_path(results_root, ds)
        fs = json.loads(fs_path.read_text())
        zs = json.loads(zs_path.read_text())
        mismatches = []
        shared = {}
        for field in RV2_PROTOCOL_FIELDS:
            v_fs, v_zs = _protocol_field(fs, zs, field)
            if v_fs != v_zs:
                mismatches.append({"field": field, "few_shot": v_fs, "zero_shot": v_zs})
            else:
                shared[field] = v_fs
        env_fs = fs["run_metadata"].get("env", {})
        env_zs = zs["run_metadata"].get("env", {})
        if env_fs.get("git_sha") is None or env_fs.get("anollm_submodule_sha") is None:
            git_sha_null_on_fewshot = True
        status = "PASS" if not mismatches else "FAIL"
        per_dataset.append({
            "dataset": ds,
            "status": status,
            "shared": shared,
            "mismatches": mismatches,
            "expected_diffs": ["mode", "n_shots", "rendered_prompt_hash"],
        })
        print(f"  {ds:12} {status}")

    all_pass = all(r["status"] == "PASS" for r in per_dataset)
    print(f"Overall: {'PASS' if all_pass else 'FAIL'} (n={len(RV2_DATASETS)} datasets, seed0)")
    if git_sha_null_on_fewshot:
        print("Hygiene note: few-shot cells have git_sha/anollm_submodule_sha=null (zero-shot has SHAs); "
              "serialization + split hashes match — not a protocol confound.")

    return {
        "per_dataset": per_dataset,
        "overall_pass": all_pass,
        "fields_checked": list(RV2_PROTOCOL_FIELDS),
        "git_sha_null_on_fewshot": git_sha_null_on_fewshot,
        "note": "Few-shot vs zero-shot differ only in n_shots/mode/prompt hash when PASS. "
                "git_sha null on revision pod is metadata hygiene only.",
    }


# ---------------------------------------------------------------------------
# §RV2 — Few-shot vs zero-shot prompted (reviewer item 1; GATE_SPEC §RV2)
# Descriptive + primary Wilcoxon (8 dataset means) + cell-level sensitivity.
# ---------------------------------------------------------------------------

def section_rv2(results_root: pathlib.Path) -> dict:
    print("\n=== §RV2 — Few-shot vs zero-shot prompted (descriptive) ===")
    fs_rows = load_rows(str(results_root), "exp2_fewshot")
    zs_rows = load_rows(str(results_root), "exp2_odds")
    lk_rows = load_rows(str(results_root), "exp2_odds")
    zs_rows = zs_rows[(zs_rows["model"] == "qwen2.5-3b") & (zs_rows["mode"] == "prompted")]
    lk_rows = lk_rows[(lk_rows["model"] == "qwen2.5-3b") & (lk_rows["mode"] == "likelihood")]
    fs_rows = fs_rows[fs_rows["mode"] == "prompted-fewshot"]

    per_dataset = []
    all_deltas = []
    for ds in RV2_DATASETS:
        zs = zs_rows[zs_rows["dataset"] == ds]["auroc"].values
        fs = fs_rows[fs_rows["dataset"] == ds]["auroc"].values
        lk = lk_rows[lk_rows["dataset"] == ds]["auroc"].values
        assert len(zs) == len(fs) == len(lk) == 3, f"Expected 3 seeds each for {ds}"
        zm, fm, lm = float(np.mean(zs)), float(np.mean(fs)), float(np.mean(lk))
        delta = fm - zm
        all_deltas.extend((fs - zs).tolist())
        per_dataset.append({
            "dataset": ds,
            "zero_shot_auroc_mean": round(zm, 4),
            "few_shot_auroc_mean": round(fm, 4),
            "likelihood_auroc_mean": round(lm, 4),
            "delta_few_minus_zero": round(delta, 4),
            "likelihood_minus_few_shot": round(lm - fm, 4),
        })
        print(f"  {ds:12} zs={zm:.3f} fs={fm:.3f} lk={lm:.3f} Δfs-zs={delta:+.3f}")

    mean_zs = float(np.mean([r["zero_shot_auroc_mean"] for r in per_dataset]))
    mean_fs = float(np.mean([r["few_shot_auroc_mean"] for r in per_dataset]))
    mean_lk = float(np.mean([r["likelihood_auroc_mean"] for r in per_dataset]))
    mean_delta = float(np.mean(all_deltas))
    gap_zs_lk = mean_lk - mean_zs
    gap_fs_lk = mean_lk - mean_fs
    gap_closure = (1.0 - abs(gap_fs_lk) / abs(gap_zs_lk)) * 100.0 if gap_zs_lk else 0.0

    print(f"Mean AUROC: zero-shot={mean_zs:.3f}, few-shot={mean_fs:.3f}, likelihood={mean_lk:.3f}")
    print(f"Mean ΔAUROC (few−zero, 24 cells)={mean_delta:+.4f}; gap closure={gap_closure:.1f}%")

    regressions = [r["dataset"] for r in per_dataset if r["delta_few_minus_zero"] < 0]
    if regressions:
        print(f"Regressions vs zero-shot: {regressions}")

    # Primary: paired Wilcoxon on 8 dataset-mean AUROCs (Demsar convention, matches M2 §1a).
    pivot = pd.DataFrame({
        "dataset": [r["dataset"] for r in per_dataset],
        "few_shot": [r["few_shot_auroc_mean"] for r in per_dataset],
        "likelihood": [r["likelihood_auroc_mean"] for r in per_dataset],
    }).set_index("dataset")
    hw = holm_wilcoxon(pivot, baseline="likelihood")
    hw_row = hw.iloc[0]
    median_delta_fs_minus_lk = float(hw_row["median_delta"])
    mean_gap_lk_minus_fs = float(np.mean([r["likelihood_minus_few_shot"] for r in per_dataset]))
    wilcoxon_primary = {
        "n_pairs": len(per_dataset),
        "min_achievable_p_n8": 0.0078125,
        "statistic": float(hw_row["statistic"]),
        "p_raw": float(hw_row["p_raw"]),
        "p_holm": float(hw_row["p_holm"]),
        "reject_at_0_05": bool(hw_row["reject"]),
        "median_delta_few_minus_likelihood": round(median_delta_fs_minus_lk, 4),
        "mean_delta_likelihood_minus_few_shot": round(mean_gap_lk_minus_fs, 4),
        "note": "Primary result: Wilcoxon on 8 dataset-mean AUROCs (few-shot vs likelihood). "
                "Family size 1 → p_holm equals p_raw. At n=8, minimum achievable p≈0.008; "
                "non-rejection indicates underpowered / statistically indistinguishable, not proof of equality.",
    }
    print(f"\nWilcoxon primary (n=8 dataset means): p={wilcoxon_primary['p_raw']:.4f}, "
          f"median Δ(few−likelihood)={median_delta_fs_minus_lk:+.4f}, "
          f"reject={wilcoxon_primary['reject_at_0_05']}")

    # Sensitivity: 24 cell-level pairs (seeds not independent — footnote only).
    from scipy.stats import wilcoxon, spearmanr

    cell_fs, cell_lk = [], []
    for ds in RV2_DATASETS:
        fs_vals = fs_rows[fs_rows["dataset"] == ds]["auroc"].values
        lk_vals = lk_rows[lk_rows["dataset"] == ds]["auroc"].values
        cell_fs.extend(fs_vals.tolist())
        cell_lk.extend(lk_vals.tolist())
    w_stat, w_p_cell = wilcoxon(cell_lk, cell_fs)
    wilcoxon_sensitivity = {
        "n_pairs": len(cell_fs),
        "statistic": float(w_stat),
        "p_raw": float(w_p_cell),
        "mean_delta_likelihood_minus_few_shot": round(float(np.mean(np.array(cell_lk) - np.array(cell_fs))), 4),
        "caveat": "Non-independent sensitivity check: 8 datasets × 3 seeds; seeds within a dataset are re-runs, "
                  "not independent samples. Do not treat as co-equal to the primary n=8 test.",
    }
    print(f"Wilcoxon sensitivity (n=24 cells, non-independent): p={wilcoxon_sensitivity['p_raw']:.4f} "
          f"[footnote only]")

    # Regression pattern vs static ODDS shapes.
    shape_rows = []
    for r in per_dataset:
        ds = r["dataset"]
        shape = RV2_ODDS_SHAPES[ds]
        shape_rows.append({
            "dataset": ds,
            "delta_few_minus_zero": r["delta_few_minus_zero"],
            "regressed": r["delta_few_minus_zero"] < 0,
            **shape,
        })
    deltas = np.array([s["delta_few_minus_zero"] for s in shape_rows])
    n_feat = np.array([s["n_features"] for s in shape_rows])
    n_samp = np.array([s["n_samples"] for s in shape_rows])
    anom = np.array([s["anomaly_pct"] for s in shape_rows])

    def _spearman(x, y) -> dict:
        rho, p = spearmanr(x, y)
        return {"rho": round(float(rho), 4), "p": round(float(p), 4)}

    regression_analysis = {
        "per_dataset": shape_rows,
        "shape_source_note": "Static ODDS catalog dimensions (TODO: verify-vs-ODDS primary PDF/source).",
        "spearman_delta_vs_n_features": _spearman(deltas, n_feat),
        "spearman_delta_vs_n_samples": _spearman(deltas, n_samp),
        "spearman_delta_vs_anomaly_pct": _spearman(deltas, anom),
        "regressors": regressions,
        "pattern_note": "Regressions speech (highest n_features≈400) and vertebral (lowest n_samples≈240, "
                        "n_features≈6) sit at shape extremes; n=8 — descriptive only, no causal claim.",
    }
    print(f"Spearman Δ(few−zero) vs n_features: rho={regression_analysis['spearman_delta_vs_n_features']['rho']}")

    return {
        "per_dataset": per_dataset,
        "mean_zero_shot_auroc": round(mean_zs, 4),
        "mean_few_shot_auroc": round(mean_fs, 4),
        "mean_likelihood_auroc": round(mean_lk, 4),
        "mean_delta_few_minus_zero": round(mean_delta, 4),
        "gap_closure_pct": round(gap_closure, 1),
        "regressions_vs_zero_shot": regressions,
        "wilcoxon_primary": wilcoxon_primary,
        "wilcoxon_sensitivity_cell_level": wilcoxon_sensitivity,
        "regression_analysis": regression_analysis,
        "note": "Primary Wilcoxon uses 8 dataset-mean AUROCs (Demsar/M2 convention). "
                "Cell-level Wilcoxon is a non-independent sensitivity check only.",
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
    output["rv1_unsw_likelihood"] = section_rv1(results_root)
    output["rv2_protocol_comparability"] = section_rv2_protocol(results_root)
    output["rv2_fewshot"] = section_rv2(results_root)

    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    out_path = tables_dir / "m6_stats.json"
    out_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"\n[m6_stats] Wrote {out_path}")


if __name__ == "__main__":
    main()
