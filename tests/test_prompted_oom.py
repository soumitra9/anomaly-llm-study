"""Prompted mode (mode B) OOM-retry: a CUDA OOM halves the batch and re-runs the (deterministic) pass.

Mirrors the likelihood score-batch OOM-retry test. Fakes transformers + a fake LM so it runs on CPU with
no model download; torch is real. Verifies the widest Qwen prompted sets can't hard-fail on memory.
"""
import types

import pandas as pd
import pytest

import anodet.scoring.prompted as P
from anodet.scoring.prompted import _is_oom


def test_is_oom_message_based():
    assert _is_oom(RuntimeError("CUDA out of memory. Tried to allocate 826.00 MiB"))
    assert not _is_oom(ValueError("bad shape"))


class _FakeEnc(dict):
    def to(self, device):
        return self


class _FakeTok:
    pad_token = None
    eos_token = "<eos>"
    pad_token_id = 0
    padding_side = "right"
    chat_template = None

    def __call__(self, prompts, return_tensors=None, padding=None):
        import torch
        return _FakeEnc(input_ids=torch.zeros((len(prompts), 3), dtype=torch.long))

    def encode(self, s, add_special_tokens=False):
        return [int(s)]  # digit "d" -> token id d, so digit_ids == [0..9]


class _FakeLM:
    """Raises CUDA-OOM on its first `oom_first` forward calls, then returns zero logits (vocab=20)."""
    def __init__(self, oom_first):
        self.oom_first = oom_first
        self.n_calls = 0

    def to(self, device):
        return self

    def eval(self):
        return self

    def __call__(self, **enc):
        import torch
        self.n_calls += 1
        if self.n_calls <= self.oom_first:
            raise RuntimeError("CUDA out of memory. Tried to allocate 1.00 GiB")
        rows = enc["input_ids"].shape[0]
        return types.SimpleNamespace(logits=torch.zeros(rows, 3, 20))


def _patch_transformers(monkeypatch, oom_first):
    import transformers
    from anodet import _fork

    lm = _FakeLM(oom_first)

    class _FakeAutoModel:
        @staticmethod
        def from_pretrained(name, torch_dtype=None):
            return lm

    class _FakeAutoTok:
        @staticmethod
        def from_pretrained(name):
            return _FakeTok()

    monkeypatch.setattr(_fork, "setup_env", lambda: None)
    monkeypatch.setattr(_fork, "pick_device", lambda prefer=None: "cpu")
    monkeypatch.setattr(transformers, "AutoModelForCausalLM", _FakeAutoModel, raising=False)
    monkeypatch.setattr(transformers, "AutoTokenizer", _FakeAutoTok, raising=False)
    return lm


def test_prompted_oom_halves_batch_and_completes(monkeypatch):
    # 5 rows, start batch 4: pass1 OOMs on its first forward -> halve to 2 -> pass2 succeeds.
    lm = _patch_transformers(monkeypatch, oom_first=1)
    Xte = pd.DataFrame({"a": [1, 2, 3, 4, 5], "b": [5, 4, 3, 2, 1]})
    out = P.run_prompted("qwen2.5-3b", Xte, batch_size=4, device="cpu")
    assert out["batch_size"] == 2                 # recorded final (halved) batch
    assert out["scores"].shape == (5,)            # all rows scored despite the OOM
    assert lm.n_calls >= 4                         # 1 OOM + 3 successful (rows 2,2,1 at bs=2)


def test_prompted_no_oom_keeps_batch(monkeypatch):
    _patch_transformers(monkeypatch, oom_first=0)
    Xte = pd.DataFrame({"a": [1, 2, 3], "b": [3, 2, 1]})
    out = P.run_prompted("qwen2.5-3b", Xte, batch_size=8, device="cpu")
    assert out["batch_size"] == 8                 # no OOM -> unchanged
    assert out["scores"].shape == (3,)
