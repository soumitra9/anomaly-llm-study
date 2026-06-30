"""AnoLLM per-dataset hyperparameters (batch size + LoRA) from configs/anollm_hparams.yaml.

Transcribed eyes-on from AnoLLM ICLR-2025 Table 7 (SmolLM-360M column). AnoLLM full-fine-tunes most ODDS
datasets but uses LoRA + tiny batch for the widest (arrhythmia/musk/speech). Using these makes our
reproduction faithful AND fits memory. The Kaggle gate hardcoded batch=32/lora=False for all — correct for
the narrow datasets it ran, wrong (and OOM-prone) for the wide ones.
"""
from __future__ import annotations

import functools
from pathlib import Path

import yaml

_CFG = Path(__file__).resolve().parents[2] / "configs" / "anollm_hparams.yaml"


@functools.lru_cache(maxsize=1)
def _table() -> dict:
    return yaml.safe_load(_CFG.read_text())["hparams"]


def get_hparams(dataset: str, *, default_batch: int = 32, default_lora: bool = False) -> tuple[int, bool]:
    """Return (batch_size, use_lora) for `dataset` from AnoLLM Table 7; defaults if not listed."""
    h = _table().get(dataset)
    if h is None:
        return default_batch, default_lora
    return int(h["batch_size"]), bool(h["use_lora"])
