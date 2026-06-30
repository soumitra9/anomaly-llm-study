"""Exp 2 cell dispatch (mocked scorers, no GPU) + classical baselines + serialize/name helpers."""
import numpy as np
import pandas as pd
import pytest

from anodet.data import odds_names, serialize


# ----------------------------- Exp 2 dispatch (mocked) -----------------------------

def _fake_data(n=20, d=4):
    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.integers(0, 9, size=(n, d)), columns=[f"c{i}" for i in range(d)])
    y = np.array([0] * (n - 4) + [1] * 4)
    return {"X_train": X, "X_test": X, "y_test": y, "text_columns": [],
            "max_length_dict": {}, "content_hash": "deadbeef", "split_index_hash": "feedface"}


def _patch(monkeypatch, captured=None):
    import anodet.eval.exp2 as exp2

    def fake_load_odds(name, *, split_idx=0, n_splits=5):
        if captured is not None:
            captured["split_idx"] = split_idx
        return _fake_data()

    def fake_run_likelihood(model, Xtr, Xte, **kw):
        n = len(Xte)
        return {"mean": np.linspace(0, 1, n), "per_permutation": np.tile(np.linspace(0, 1, n), (3, 1)).T,
                "lora": {"rank": 8}, "device": "cpu", "r": 3, "precision": "fp32", "batch_size": 8}

    def fake_run_prompted(model, Xte, **kw):
        return {"scores": np.linspace(0, 1, len(Xte)), "distinct_levels": 5, "device": "cpu"}

    monkeypatch.setattr(exp2, "load_odds", fake_load_odds)
    monkeypatch.setattr(exp2, "run_likelihood", fake_run_likelihood)
    monkeypatch.setattr(exp2, "run_prompted", fake_run_prompted)
    monkeypatch.setattr(exp2, "seed_everything", lambda s: None)
    return exp2


def test_exp2_likelihood_cell(monkeypatch):
    exp2 = _patch(monkeypatch)
    metrics, status, extra = exp2.run_one("breastw", "smol-360", "likelihood", max_steps=1, r=3)
    assert status == "complete"
    assert {"auroc", "auprc", "auprc_gain", "recall_at_1pct_fpr"} <= set(metrics)
    assert "r_sensitivity_auroc" in metrics  # free curve attached for mode A
    assert extra["run_metadata"]["checkpoint_kind"] == "base"
    assert extra["run_metadata"]["lora"] == {"rank": 8}


def test_exp2_prompted_cell(monkeypatch):
    exp2 = _patch(monkeypatch)
    metrics, status, extra = exp2.run_one("breastw", "smol-360", "prompted")
    assert status == "complete"
    assert metrics["distinct_levels"] == 5
    assert extra["run_metadata"]["checkpoint_kind"] == "instruct"
    assert extra["run_metadata"]["decode_config"]["scorer"] == "expected_value"


def test_exp2_unknown_mode_raises(monkeypatch):
    exp2 = _patch(monkeypatch)
    with pytest.raises(ValueError):
        exp2.run_one("breastw", "smol-360", "bogus")


def test_exp2_seed_maps_to_split_idx(monkeypatch):
    captured = {}
    exp2 = _patch(monkeypatch, captured)
    run_cell = exp2.make_run_cell(max_steps=1, r=3)
    run_cell({"model": "smol-360", "mode": "prompted", "dataset": "breastw", "seed": 2})
    assert captured["split_idx"] == 2


# ----------------------------- classical baselines (real pyod, tiny) -----------------------------

def test_baseline_panel_shapes():
    from anodet.baselines.classical import PANEL, run_panel

    rng = np.random.default_rng(1)
    X_train = pd.DataFrame(rng.normal(0, 1, size=(60, 3)))
    X_test = pd.DataFrame(np.vstack([rng.normal(0, 1, size=(18, 3)),
                                     rng.normal(8, 1, size=(2, 3))]))
    out = run_panel(X_train, X_test, seed=0)
    assert set(out) == set(PANEL)
    for name, scores in out.items():
        assert scores.shape == (20,)
        assert np.isfinite(scores).all(), name


# ----------------------------- serialize + odds_names helpers -----------------------------

def test_serialize_reorder_and_random():
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4], "c": [5, 6]})
    assert serialize.arbitrary_order(df) == ["a", "b", "c"]
    perm = serialize.random_order(df, seed=0)
    assert sorted(perm) == ["a", "b", "c"]
    rows = serialize.serialize(df, order=["c", "a", "b"])
    assert rows[0].startswith("c is 5")
    with pytest.raises(ValueError):
        serialize.reorder(df, ["a", "b"])  # missing column


def test_semantic_names_count_guard():
    df8 = pd.DataFrame(np.zeros((2, 8)))
    assert len(odds_names.semantic_names("pima", 8)) == 8
    assert list(odds_names.apply_semantic(df8, "pima").columns)[1] == "glucose"
    assert list(odds_names.anonymize(df8).columns) == [f"col_{i}" for i in range(8)]
    with pytest.raises(ValueError):
        odds_names.semantic_names("pima", 7)  # count mismatch -> alignment guard fires
    with pytest.raises(KeyError):
        odds_names.semantic_names("nonesuch", 3)
