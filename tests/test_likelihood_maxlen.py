"""run_likelihood must coerce max_length_dict None->{} (the fork does `name not in max_length_dict`).

Regression for the M3 credit-card path: ODDS loaders supply max_length_dict, but the security loaders
(creditcard/unsw) don't, so run_likelihood was passing None -> fork crash `NoneType is not iterable`.
"""
import numpy as np
import pandas as pd


def test_run_likelihood_coerces_none_max_length_dict(monkeypatch):
    import anodet.scoring.likelihood as L
    from anodet import _fork

    captured = {}

    class _FakeModel:
        def float(self):
            return self

        def to(self, *a, **k):
            return self

    class _FakeAnoLLM:
        def __init__(self, name, *, batch_size, max_length_dict=None, **kw):
            captured["mld"] = max_length_dict
            self.model = _FakeModel()

        def fit(self, *a, **k):
            pass

        def decision_function(self, X, *, n_permutations, batch_size, device):
            return np.zeros((len(X), n_permutations))

    monkeypatch.setattr(_fork, "ensure_dist", lambda: None)
    monkeypatch.setattr(_fork, "pick_device", lambda prefer=None: "cpu")
    monkeypatch.setattr(_fork, "resolve_model", lambda n: n)
    monkeypatch.setattr(_fork, "import_fork", lambda: (_FakeAnoLLM, None))

    Xtr = pd.DataFrame({"a": [1, 2, 3]})
    Xte = pd.DataFrame({"a": [1, 2]})
    # call WITHOUT max_length_dict (the security-loader case) -> must not pass None to the fork
    L.run_likelihood("smol", Xtr, Xte, lora=True, max_steps=1, r=2, batch_size=2, device="cpu")
    assert captured["mld"] == {} and isinstance(captured["mld"], dict)
