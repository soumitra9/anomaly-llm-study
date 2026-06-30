"""Phase-0 fixes: per-dataset hparams (Table 7), precision-by-capability, OOM detection."""
import pytest

from anodet.data.hparams import get_hparams
from anodet.scoring.likelihood import _is_oom, _select_precision


# ----- AnoLLM Table 7 per-dataset (batch, lora) -----

def test_hparams_full_ft_narrow_datasets():
    assert get_hparams("wine") == (32, False)
    assert get_hparams("breastw") == (32, False)
    assert get_hparams("cardio") == (32, False)  # OOM'd on P100 at 32; fine on a 48GB card


def test_hparams_lora_for_widest_datasets():
    # AnoLLM uses LoRA + tiny batch for the widest-feature sets (Table 7) — our gate wrongly used full-FT/32.
    assert get_hparams("arrhythmia") == (2, True)
    assert get_hparams("speech") == (2, True)
    assert get_hparams("musk") == (8, True)


def test_hparams_big_batches_and_covertype_alias():
    assert get_hparams("http") == (128, False)
    assert get_hparams("mulcross") == (96, False)
    assert get_hparams("covertype") == (48, False)  # paper: ForestCover
    assert get_hparams("unknown_dataset") == (32, False)  # default fallback


# ----- precision selection -----

def test_precision_ampere_is_bf16():
    upd, prec = _select_precision("cuda", 8)   # A40/A6000/A100 (cc>=8)
    assert prec == "bf16" and upd == {"bf16": True}


def test_precision_pre_ampere_is_fp16():
    upd, prec = _select_precision("cuda", 6)   # P100 (cc 6.0) / T4 (7.5)
    assert prec == "fp16" and upd == {"fp16": True}


def test_precision_off_gpu_is_fp32():
    upd, prec = _select_precision("cpu", 0)
    assert prec == "fp32" and upd["use_cpu"] is True and not upd["bf16"] and not upd["fp16"]


# ----- OOM detection -----

def test_is_oom_message_based():
    assert _is_oom(RuntimeError("CUDA out of memory. Tried to allocate 826.00 MiB"))
    assert not _is_oom(ValueError("bad shape"))
    assert not _is_oom(RuntimeError("some unrelated cuda error"))


# ----- scoring batch decoupled from training batch (inference is score-neutral) -----

def _fake_fork(monkeypatch, decision_fn):
    """Patch _fork so run_likelihood drives a fake AnoLLM on CPU.

    decision_fn(call_idx, batch_size, n_rows, n_perms) returns the per-permutation array (or raises).
    Returns (likelihood_module, calls_dict).
    """
    import numpy as np

    import anodet.scoring.likelihood as L
    from anodet import _fork

    calls = {"fit": 0, "ctor_batches": [], "decision_batches": []}

    class _FakeModel:
        def float(self):
            return self

        def to(self, *a, **k):
            return self

    class _FakeAnoLLM:
        def __init__(self, model_name, *, batch_size, **kw):
            calls["ctor_batches"].append(batch_size)
            self.model = _FakeModel()

        def fit(self, *a, **k):
            calls["fit"] += 1

        def decision_function(self, X_test, *, n_permutations, batch_size, device):
            calls["decision_batches"].append(batch_size)
            return decision_fn(len(calls["decision_batches"]), batch_size, len(X_test), n_permutations)

    monkeypatch.setattr(_fork, "ensure_dist", lambda: None)
    monkeypatch.setattr(_fork, "pick_device", lambda prefer=None: "cpu")
    monkeypatch.setattr(_fork, "resolve_model", lambda name: name)
    monkeypatch.setattr(_fork, "import_fork", lambda: (_FakeAnoLLM, None))
    return L, calls


def test_score_batch_elevated_and_independent_oom_retry(monkeypatch):
    """Wide LoRA set (train batch 2): scoring lifts to 32; a score-time OOM halves the SCORE batch
    only and never refits (train batch untouched)."""
    import numpy as np
    import pandas as pd

    def decision_fn(call_idx, bs, n, r):
        if call_idx == 1:  # OOM the first (elevated) scoring attempt
            raise RuntimeError("CUDA out of memory. Tried to allocate 1.00 GiB")
        return np.zeros((n, r))

    L, calls = _fake_fork(monkeypatch, decision_fn)
    Xtr = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    Xte = pd.DataFrame({"a": [1, 2], "b": [3, 4]})

    out = L.run_likelihood("smol-360", Xtr, Xte, lora=True, max_steps=1, r=3, batch_size=2, device="cpu")

    assert calls["ctor_batches"] == [2]            # train batch untouched (no train OOM)
    assert calls["fit"] == 1                       # fit ran exactly once (score OOM does NOT refit)
    assert calls["decision_batches"] == [32, 16]   # elevated to 32, then halved independently
    assert out["batch_size"] == 2                  # recorded TRAIN batch
    assert out["score_batch_size"] == 16           # recorded final SCORE batch
    assert out["per_permutation"].shape == (2, 3)


def test_score_batch_unchanged_for_full_ft(monkeypatch):
    """Full-FT set (train batch >= 32): scoring batch == train batch — provably no behavior change."""
    import numpy as np
    import pandas as pd

    L, calls = _fake_fork(monkeypatch, lambda i, bs, n, r: np.zeros((n, r)))
    Xtr = pd.DataFrame({"a": [1, 2, 3]})
    Xte = pd.DataFrame({"a": [1, 2, 3]})

    out = L.run_likelihood("smol-360", Xtr, Xte, lora=False, max_steps=1, r=2, batch_size=128, device="cpu")
    assert calls["decision_batches"] == [128]      # http-like big batch preserved (max(128,32)=128)
    assert out["score_batch_size"] == 128
