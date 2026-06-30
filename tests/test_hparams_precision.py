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
