"""M1 gate verdict: aggregation, C1/C2/C3 logic, coverage/preliminary handling, no-reference degrade."""
import yaml

from anodet.eval.verdict import compute_verdict
from anodet.utils.io import atomic_write_json


def _cell(tmp, ds, auroc, seed=0):
    atomic_write_json(
        tmp / "raw" / "exp1_repro" / f"smol-360__likelihood__{ds}__seed{seed}.json",
        {"status": "complete", "metrics": {"auroc": auroc},
         "run_metadata": {"dataset": ds, "model": "smol-360", "mode": "likelihood", "seed": seed}},
    )


def _ref(tmp, mean, per_dataset):
    p = tmp / "ref.yaml"
    p.write_text(yaml.safe_dump({"aggregate_mean": mean, "per_dataset": per_dataset}))
    return str(p)


def test_partial_coverage_is_preliminary(tmp_path):
    _cell(tmp_path, "wine", 0.86)
    _cell(tmp_path, "breastw", 0.99)
    ref = _ref(tmp_path, 0.865, {})
    v = compute_verdict(str(tmp_path), ref, n_datasets=30)
    assert v["coverage"] == 2 and not v["complete"]
    assert v["verdict"].startswith("PRELIMINARY")


def test_full_pass_with_per_dataset(tmp_path):
    ours = {"wine": 0.86, "breastw": 0.99, "cardio": 0.90}
    pub = {"wine": {"mean": 0.865, "std": 0.03}, "breastw": {"mean": 0.99, "std": 0.01},
           "cardio": {"mean": 0.91, "std": 0.03}}
    for ds, a in ours.items():
        _cell(tmp_path, ds, a)
    ref = _ref(tmp_path, sum(p["mean"] for p in pub.values()) / 3, pub)
    v = compute_verdict(str(tmp_path), ref, n_datasets=3, c2_min=0.5, c3_min_in_band=3)
    assert v["complete"]
    assert v["criteria"]["C1_mean"]["pass"]
    assert v["criteria"]["C2_rank"]["status"] == "active"
    assert v["criteria"]["C3_band"]["pass"]
    assert v["verdict"] == "PASS"


def test_c1_fail_gives_fail(tmp_path):
    _cell(tmp_path, "wine", 0.50)  # far from published
    ref = _ref(tmp_path, 0.865, {})
    v = compute_verdict(str(tmp_path), ref, n_datasets=1)
    assert not v["criteria"]["C1_mean"]["pass"]
    assert v["verdict"] == "FAIL"


def test_no_reference_per_dataset_is_informational(tmp_path):
    _cell(tmp_path, "wine", 0.87)
    ref = _ref(tmp_path, 0.865, {})  # no per_dataset
    v = compute_verdict(str(tmp_path), ref, n_datasets=1)
    assert v["criteria"]["C2_rank"]["pass"] is None
    assert v["criteria"]["C3_band"]["pass"] is None
    assert v["criteria"]["C1_mean"]["pass"]  # |0.87-0.865| <= 0.02
    assert v["verdict"] == "PASS"  # rests on C1 alone when per-dataset absent
