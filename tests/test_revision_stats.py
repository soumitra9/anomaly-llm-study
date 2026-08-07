"""RV1/RV2 analysis sections — recomputed deltas must match local JSONs."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def _has_revision_cells() -> bool:
    rv1 = list((RESULTS / "raw" / "exp3_security").glob("qwen2.5-3b__likelihood__unsw__*.json"))
    rv2 = list((RESULTS / "raw" / "exp2_fewshot").glob("*.json"))
    return len(rv1) == 3 and len(rv2) == 24


@pytest.mark.skipif(not _has_revision_cells(), reason="revision JSONs not present locally")
def test_rv2_protocol_comparability_breastw_seed0():
    """Few-shot vs zero-shot differ only in n_shots/mode; same split + serialization."""
    fs = json.loads(
        (RESULTS / "raw" / "exp2_fewshot" / "qwen2.5-3b__prompted-fewshot__breastw__seed0.json").read_text()
    )
    zs = json.loads(
        (RESULTS / "raw" / "exp2_odds" / "qwen2.5-3b__prompted__breastw__seed0.json").read_text()
    )
    rm_fs, rm_zs = fs["run_metadata"], zs["run_metadata"]
    assert rm_fs["dataset_content_hash"] == rm_zs["dataset_content_hash"]
    assert rm_fs["serialization_template_hash"] == rm_zs["serialization_template_hash"]
    assert rm_fs["split_index_hash"] == rm_zs["split_index_hash"]
    assert fs["n_rows_scored"] == zs["n_rows_scored"]
    assert rm_fs["decode_config"]["n_shots"] == 3


@pytest.mark.skipif(not _has_revision_cells(), reason="revision JSONs not present locally")
def test_rv1_and_rv2_stats_sections():
    import pathlib
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.m6_stats import section_rv1, section_rv2, section_rv2_protocol

    rv1 = section_rv1(pathlib.Path("results"))
    assert rv1["likelihood_mean_auprc_gain"] == pytest.approx(7.686, abs=0.05)
    assert rv1["likelihood_mean_recall_at_1pct_fpr"] == pytest.approx(0.302, abs=0.01)
    assert rv1["prompted_seed0_auprc_gain"] == pytest.approx(3.989, abs=0.01)

    protocol = section_rv2_protocol(pathlib.Path("results"))
    assert protocol["overall_pass"] is True
    assert all(r["status"] == "PASS" for r in protocol["per_dataset"])
    assert len(protocol["per_dataset"]) == 8

    rv2 = section_rv2(pathlib.Path("results"))
    assert rv2["mean_zero_shot_auroc"] == pytest.approx(0.468, abs=0.001)
    assert rv2["mean_few_shot_auroc"] == pytest.approx(0.759, abs=0.001)
    assert rv2["mean_likelihood_auroc"] == pytest.approx(0.773, abs=0.001)
    assert rv2["mean_delta_few_minus_zero"] == pytest.approx(0.290, abs=0.001)
    assert rv2["gap_closure_pct"] == pytest.approx(95.2, abs=0.5)
    assert set(rv2["regressions_vs_zero_shot"]) == {"speech", "vertebral"}

    wp = rv2["wilcoxon_primary"]
    assert wp["n_pairs"] == 8
    assert wp["min_achievable_p_n8"] == pytest.approx(0.0078125)
    assert wp["mean_delta_likelihood_minus_few_shot"] == pytest.approx(0.014, abs=0.002)
    assert wp["reject_at_0_05"] is False
    assert wp["p_raw"] == pytest.approx(0.6406, abs=0.01)

    ws = rv2["wilcoxon_sensitivity_cell_level"]
    assert ws["n_pairs"] == 24
    assert "Non-independent" in ws["caveat"]

    ra = rv2["regression_analysis"]
    assert set(ra["regressors"]) == {"speech", "vertebral"}
    assert len(ra["per_dataset"]) == 8
    assert "TODO: verify-vs-ODDS" in ra["shape_source_note"]


@pytest.mark.skipif(not _has_revision_cells(), reason="revision JSONs not present locally")
def test_m6_stats_json_rv2_keys():
    import json

    stats_path = RESULTS / "tables" / "m6_stats.json"
    assert stats_path.exists(), "Run m6_stats.py first"
    data = json.loads(stats_path.read_text())
    assert "rv2_protocol_comparability" in data
    assert data["rv2_protocol_comparability"]["overall_pass"] is True
    rv2 = data["rv2_fewshot"]
    assert "wilcoxon_primary" in rv2
    assert "wilcoxon_sensitivity_cell_level" in rv2
    assert "regression_analysis" in rv2


@pytest.mark.skipif(not _has_revision_cells(), reason="revision JSONs not present locally")
def test_rv1_unsw_prompted_cells_exist():
    prompted = list((RESULTS / "raw" / "exp3_security").glob("qwen2.5-3b__prompted__unsw__*.json"))
    assert len(prompted) >= 1
