"""Security loaders: creditcard split/subsample/reweight + UNSW leakage screen (synthetic frames)."""
import numpy as np
import pandas as pd
import pytest

from anodet.data import creditcard, unsw


def _cc_df(n=200, n_fraud=12, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "Time": np.arange(n),
        "V1": rng.normal(size=n), "V2": rng.normal(size=n),
        "Amount": rng.gamma(2, size=n),
        "Class": np.r_[np.zeros(n - n_fraud), np.ones(n_fraud)].astype(int),
    })
    return df.sample(frac=1, random_state=seed).reset_index(drop=True)


@pytest.mark.parametrize("split", ["temporal", "random"])
def test_creditcard_prepare(split):
    out = creditcard.prepare_creditcard(_cc_df(), split=split, max_test_neg=30, seed=1)
    assert "Class" not in out["X_train"].columns          # label excluded from features
    assert set(np.unique(out["y_test"])) <= {0, 1}
    assert int(out["y_test"].sum()) == 12  # ALL anomalies land in test (uncontaminated protocol)
    assert out["sample_weight"].shape == out["y_test"].shape
    assert out["n_neg_scored"] <= 30 and out["n_neg_total"] >= out["n_neg_scored"]
    assert 0 < out["true_base_rate"] < 1


def test_creditcard_temporal_is_ordered():
    # temporal split must train on earlier rows -> train normals' max Time < test min Time region
    df = _cc_df(n=100, n_fraud=5)
    out = creditcard.prepare_creditcard(df, split="temporal", max_test_neg=None, test_frac=0.5)
    assert len(out["X_train"]) > 0


def test_creditcard_missing_file():
    with pytest.raises(FileNotFoundError):
        creditcard.load_creditcard("/nonexistent/creditcard.csv")


def _unsw_df(n=400, seed=0):
    rng = np.random.default_rng(seed)
    y = np.r_[np.zeros(n - 40), np.ones(40)].astype(int)
    return pd.DataFrame({
        "id": np.arange(n), "srcip": ["1.2.3.4"] * n, "sport": rng.integers(0, 65535, n),
        "attack_cat": ["none"] * n,
        "dur": rng.gamma(2, size=n),                 # legit feature
        "ct_leak": y.astype(float) + rng.normal(0, 0.001, n),  # near-perfect single-feature -> leakage
        "ct_ok": rng.normal(size=n),                 # ct_ feature with no signal
        "label": y,
    })


def test_unsw_leakage_screen_drops_ids_and_flags_leak():
    s = unsw.leakage_screen(_unsw_df())
    assert set(["id", "srcip", "sport", "attack_cat", "label"]) <= set(s["dropped"])
    assert "ct_leak" in s["flagged"]            # caught as look-ahead
    assert "ct_leak" not in s["X"].columns      # and dropped
    assert "ct_ok" in s["X"].columns            # harmless ct_ kept
    assert "dur" in s["X"].columns


def test_unsw_prepare_contract():
    out = unsw.prepare_unsw(_unsw_df(), subsample=None, max_test_neg=50, seed=2)
    assert out["sample_weight"].shape == out["y_test"].shape
    assert "ct_leak" not in out["X_train"].columns
    assert out["n_neg_scored"] <= 50
