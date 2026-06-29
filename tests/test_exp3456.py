"""Two-stage triage logic (real) + Exp 3/3b/4 runner dispatch (mocked scorers/loaders, no GPU)."""
import numpy as np
import pandas as pd
import pytest


# ----------------------------- Exp 6 two-stage (real) -----------------------------

def test_two_stage_beats_classical_at_budget():
    from anodet.triage.two_stage import evaluate_triage, two_stage_scores

    n = 20
    y = np.zeros(n, dtype=int); y[:4] = 1                  # positives at 0..3
    classical = np.full(n, 0.1); classical[:4] = 0.5; classical[4:10] = 0.9  # pos in top-10 but mid-ranked
    llm = np.zeros(n); llm[:4] = 1.0                       # llm ranks positives top

    two = two_stage_scores(classical, llm, k=10)
    # candidates (top-10 classical) contain all positives; llm floats them to the top
    assert set(np.argsort(-two)[:4]) == {0, 1, 2, 3}

    # shortlist k=10 (classical pre-filter), tight alert budget n_top=4 (reviewed): LLM re-ranking helps here
    res = evaluate_triage(y, classical, llm, k=10, n_top=4)
    assert res["two_stage"]["precision_at_k"] == 1.0       # LLM floats the 4 positives to the top of the shortlist
    assert res["two_stage"]["precision_at_k"] > res["classical"]["precision_at_k"]
    assert res["uplift_two_stage_vs_classical"]["precision_at_k"] > 0


# ----------------------------- Exp 3 security dispatch (mocked) -----------------------------

def _sec_data(n=60):
    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.normal(size=(n, 4)))
    y = np.r_[np.zeros(n - 6), np.ones(6)].astype(int)
    return {"X_train": X, "X_test": X, "y_test": y,
            "sample_weight": np.ones(n), "content_hash": "h", "split": "temporal"}


def test_exp3_modes(monkeypatch):
    import anodet.eval.exp3_security as e3
    monkeypatch.setattr(e3, "_load", lambda ds, dd, **k: _sec_data())
    import anodet.baselines.classical as cl
    monkeypatch.setattr(cl, "run_baseline", lambda name, a, b, **k: np.linspace(0, 1, len(b)))
    m, status, extra = e3.run_one("creditcard", "smol-360", "classical:iforest")
    assert status == "complete"
    assert {"auprc_gain", "recall_at_1pct_fpr", "precision_at_topN"} <= set(m)
    assert "recall_at_1pct_fpr_ci" in m
    with pytest.raises(ValueError):
        e3.run_one("creditcard", "smol-360", "bogus")


# ----------------------------- Exp 3b names dispatch (mocked) -----------------------------

def test_exp3b_arms(monkeypatch):
    import anodet.eval.exp3b_names as e3b
    df = pd.DataFrame(np.zeros((10, 8)))
    monkeypatch.setattr(e3b, "load_odds", lambda ds, **k: {
        "X_test": df, "y_test": np.r_[np.zeros(8), np.ones(2)].astype(int), "content_hash": "h"})
    import anodet.scoring.prompted as pr
    monkeypatch.setattr(pr, "run_prompted", lambda model, X, **k: {"scores": np.linspace(0, 1, len(X))})
    m, status, extra = e3b.run_one("pima", arm="semantic")
    assert "auroc" in m and extra["arm"] == "semantic"
    m2, _, _ = e3b.run_one("pima", arm="anon")
    assert "auroc" in m2
    with pytest.raises(ValueError):
        e3b.run_one("pima", arm="bogus")


# ----------------------------- Exp 4 ordering dispatch (mocked) -----------------------------

def test_exp4_orderings(monkeypatch):
    import anodet.eval.exp4_serialization as e4
    df = pd.DataFrame({"a": range(10), "b": range(10), "c": range(10)})
    monkeypatch.setattr(e4, "load_odds", lambda ds, **k: {
        "X_test": df, "y_test": np.r_[np.zeros(8), np.ones(2)].astype(int), "content_hash": "h"})
    import anodet.scoring.prompted as pr
    monkeypatch.setattr(pr, "run_prompted", lambda model, X, **k: {"scores": np.linspace(0, 1, len(X))})
    for ordering in ["arbitrary", "random:0"]:
        m, status, _ = e4.run_one("wine", "smol-360", ordering)
        assert "auroc" in m and status == "complete"
    with pytest.raises(ValueError):
        e4.run_one("wine", "smol-360", "domain")  # missing domain_order
