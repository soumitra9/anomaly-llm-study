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
    from scripts.m6_stats import section_rv1, section_rv2

    rv1 = section_rv1(pathlib.Path("results"))
    assert rv1["likelihood_mean_auprc_gain"] == pytest.approx(7.686, abs=0.05)
    assert rv1["likelihood_mean_recall_at_1pct_fpr"] == pytest.approx(0.302, abs=0.01)
    assert rv1["prompted_seed0_auprc_gain"] == pytest.approx(3.989, abs=0.01)

    rv2 = section_rv2(pathlib.Path("results"))
    assert rv2["mean_zero_shot_auroc"] == pytest.approx(0.468, abs=0.001)
    assert rv2["mean_few_shot_auroc"] == pytest.approx(0.759, abs=0.001)
    assert rv2["mean_likelihood_auroc"] == pytest.approx(0.773, abs=0.001)
    assert rv2["mean_delta_few_minus_zero"] == pytest.approx(0.290, abs=0.001)
    assert rv2["gap_closure_pct"] == pytest.approx(95.2, abs=0.5)
    assert set(rv2["regressions_vs_zero_shot"]) == {"speech", "vertebral"}


@pytest.mark.skipif(not _has_revision_cells(), reason="revision JSONs not present locally")
def test_rv1_unsw_prompted_cells_exist():
    prompted = list((RESULTS / "raw" / "exp3_security").glob("qwen2.5-3b__prompted__unsw__*.json"))
    assert len(prompted) >= 1
