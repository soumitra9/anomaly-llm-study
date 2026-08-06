"""Fast smoke: RV1 + RV2 code paths with mocked models — no HF downloads."""
import json
import sys
import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# RV1: exp3_security.run_one records r_permutations + max_steps in JSON
# ---------------------------------------------------------------------------

def _fake_likelihood(model, X_train, X_test, *, lora, r, max_steps, batch_size, device):
    n = len(X_test)
    return {
        "mean": np.linspace(0, 1, n),
        "r": r,
        "lora": {"rank": 10},
        "precision": "fp32",
    }


def test_rv1_run_one_records_r_and_max_steps(tmp_path, monkeypatch):
    """run_one likelihood on unsw records r_permutations=5 and max_steps in extra."""
    import anodet.eval.exp3_security as exp3
    import anodet.scoring.likelihood as lik_mod
    monkeypatch.setattr(lik_mod, "run_likelihood", _fake_likelihood)

    # minimal fake UNSW data
    n_train, n_test, n_feat = 50, 30, 5
    y_test = np.zeros(n_test, dtype=int)
    y_test[:3] = 1
    weight = np.ones(n_test)
    fake_data = {
        "X_train": pd.DataFrame(np.random.rand(n_train, n_feat)),
        "X_test": pd.DataFrame(np.random.rand(n_test, n_feat)),
        "y_test": y_test,
        "sample_weight": weight,
        "content_hash": "abc123",
        "split": None,
        "flagged": None,
    }
    monkeypatch.setattr(exp3, "_load", lambda *a, **k: fake_data)

    metrics, status, extra = exp3.run_one(
        "unsw", "qwen2.5-3b", "likelihood",
        r=5, max_steps=1000, device="cpu",
    )
    assert status == "complete"
    rm = extra["run_metadata"]
    assert rm["r_permutations"] == 5, f"expected r_permutations=5, got {rm['r_permutations']}"
    assert rm["checkpoint_kind"] == "base"
    assert extra["max_steps"] == 1000


def test_rv1_fleet_threads_r_and_max_steps(tmp_path, monkeypatch):
    """exp3_fleet --likelihood-tasks unsw --r 5 --max-steps 1000 threads correct kwargs to run_one."""
    import anodet.eval.exp3_security as exp3
    import scripts.exp3_fleet as fleet
    calls = []

    def fake_run_one(dataset, model, mode, *, data_dir, n_levels, batch_size, device, n_top, **kw):
        calls.append({"dataset": dataset, "mode": mode, "r": kw.get("r"), "max_steps": kw.get("max_steps")})
        return (
            {"auprc_gain": 1.0, "recall_at_1pct_fpr": 0.5},
            "complete",
            {"run_metadata": {"dataset_content_hash": "x"}, "n_rows_scored": 10, "n_rows_expected": 10},
        )

    monkeypatch.setattr(exp3, "run_one", fake_run_one)
    monkeypatch.setattr(sys, "argv", [
        "exp3_fleet",
        "--task-datasets", "unsw",
        "--modes", "likelihood",
        "--models", "qwen2.5-3b",
        "--likelihood-tasks", "unsw",
        "--seeds", "0",
        "--r", "5",
        "--max-steps", "1000",
        "--results-root", str(tmp_path),
        "--device", "cpu",
    ])
    assert fleet.main() == 0
    assert len(calls) == 1
    c = calls[0]
    assert c["dataset"] == "unsw" and c["mode"] == "likelihood"
    assert c["r"] == 5, f"expected r=5, got {c['r']}"
    assert c["max_steps"] == 1000, f"expected max_steps=1000, got {c['max_steps']}"


# ---------------------------------------------------------------------------
# RV2: revision_fewshot records n_shots in decode_config
# ---------------------------------------------------------------------------

def _fake_run_prompted(model, X_test, *, X_train=None, y_train=None, n_shots=0,
                       shot_seed=0, n_levels=10, batch_size=16, device=None,
                       paraphrase=0, also_parse_integer=False):
    return {
        "scores": np.linspace(0, 1, len(X_test)),
        "distinct_levels": 10,
        "device": "cpu",
        "batch_size": batch_size,
        "n_shots": n_shots,
    }


def test_rv2_fewshot_records_n_shots(tmp_path, monkeypatch):
    """revision_fewshot writes JSONs with n_shots=3 in decode_config."""
    import scripts.revision_fewshot as rv2
    import anodet.scoring.prompted as pr
    import anodet.data.odds as odds_mod
    monkeypatch.setattr(pr, "run_prompted", _fake_run_prompted)

    n_train, n_test = 40, 20
    y_train = np.zeros(n_train, dtype=int)
    fake_data = {
        "X_train": pd.DataFrame(np.random.rand(n_train, 4), columns=list("abcd")),
        "X_test": pd.DataFrame(np.random.rand(n_test, 4), columns=list("abcd")),
        "y_train": y_train,
        "y_test": np.array([1] * 2 + [0] * 18),
        "content_hash": "fakehash",
        "split_index_hash": "fakesplit",
    }
    monkeypatch.setattr(odds_mod, "load_odds", lambda *a, **k: fake_data)

    monkeypatch.setattr(sys, "argv", [
        "revision_fewshot",
        "--datasets", "breastw",
        "--seeds", "0",
        "--n-shots", "3",
        "--batch-size", "4",
        "--device", "cpu",
        "--results-root", str(tmp_path),
    ])
    assert rv2.main() == 0
    jsons = list((tmp_path / "raw" / "exp2_fewshot").glob("*.json"))
    assert len(jsons) == 1
    payload = json.loads(jsons[0].read_text())
    assert payload["status"] == "complete"
    dc = payload["run_metadata"]["decode_config"]
    assert dc["n_shots"] == 3, f"expected n_shots=3, got {dc}"
    assert dc["scorer"] == "expected_value"


# ---------------------------------------------------------------------------
# RV1: default behavior unchanged (no UNSW in default likelihood tasks)
# ---------------------------------------------------------------------------

def test_rv1_default_still_excludes_unsw():
    import scripts.exp3_fleet as fleet
    cells = fleet.build_cells(list(fleet.TASKS), ["qwen2.5-3b"],
                              ["likelihood"], [0])
    assert not any(c["task"] == "unsw" for c in cells)
