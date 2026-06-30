"""Mode A (likelihood) — production wrapper over the AnoLLM fork.

Fine-tunes a backbone on the (normal) training rows, then scores test rows by mean NLL over `r`
random column permutations. Returns the FULL per-permutation matrix (n_test, r) so the
r-sensitivity curve (PLAN §4a/§9b) is free post-hoc (average prefixes). Device-agnostic:
bf16 on CUDA (matches AnoLLM), fp32 on MPS/CPU. Single-process via the fork bridge's gloo group.
"""
from __future__ import annotations

import tempfile
from typing import Optional

import numpy as np
import pandas as pd

from anodet import _fork


def _select_precision(device: str, cuda_capability_major: int) -> tuple[dict, str]:
    """Return (HF-TrainingArguments precision kwargs, precision label) for the device.

    bf16 only on Ampere+ (compute capability major >= 8) where it's hardware-native; fp16 on older CUDA
    (Pascal/Turing emulate bf16 ~10x slower — the Kaggle-P100 trap); fp32 off-GPU.
    """
    if device == "cuda":
        if cuda_capability_major >= 8:
            return {"bf16": True}, "bf16"
        return {"fp16": True}, "fp16"
    return {"bf16": False, "fp16": False, "use_cpu": device == "cpu"}, "fp32"


def _is_oom(exc: BaseException) -> bool:
    """True iff `exc` is a CUDA out-of-memory error (typed or message-based)."""
    import torch

    return isinstance(exc, getattr(torch.cuda, "OutOfMemoryError", ())) or "out of memory" in str(exc).lower()


def run_likelihood(
    model: str,
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    *,
    text_columns: Optional[list] = None,
    max_length_dict: Optional[dict] = None,
    lora: bool = False,
    max_steps: int = 2000,
    lr: float = 5e-5,
    r: int = 21,
    batch_size: int = 32,
    device: Optional[str] = None,
    experiment_dir: Optional[str] = None,
) -> dict:
    """Fine-tune + NLL-score. Returns {'mean': (n_test,), 'per_permutation': (n_test, r),
    'lora': cfg|None, 'device': str, 'r': int, 'precision': str, 'batch_size': int}."""
    _fork.ensure_dist()
    import torch

    AnoLLM, _ = _fork.import_fork()
    device = _fork.pick_device(device)

    # Precision by HARDWARE capability (see _select_precision): bf16 only on Ampere+; else fp16 on CUDA; fp32 off-GPU.
    cap_major = torch.cuda.get_device_capability()[0] if device == "cuda" else 0
    prec_update, precision = _select_precision(device, cap_major)
    train_kwargs = dict(max_steps=max_steps, learning_rate=lr, report_to=[], **prec_update)

    model_name = _fork.resolve_model(model)
    # LoRA config AnoLLM hardcodes (r=8, alpha=32, smolLM proj modules) — recorded for provenance
    lora_cfg = (
        {"rank": 8, "alpha": 32, "dropout": 0.1,
         "target_modules": ["q_proj", "o_proj", "k_proj", "v_proj", "gate_proj", "up_proj", "down_proj"]}
        if lora else None
    )

    # OOM-retry: AnoLLM's batches assume a 48GB card; on a smaller GPU halve the batch and retry (floor 1).
    bs = int(batch_size)
    while True:
        try:
            anollm = AnoLLM(
                model_name,
                experiment_dir=experiment_dir or tempfile.mkdtemp(prefix="anollm_"),
                batch_size=bs,
                efficient_finetuning="lora" if lora else "",
                max_length_dict=max_length_dict,
                textual_columns=text_columns or [],
                **train_kwargs,
            )
            if device != "cuda":
                anollm.model = anollm.model.float()  # bf16 checkpoint -> fp32 for MPS/CPU
            with tempfile.TemporaryDirectory() as dtmp:
                anollm.fit(X_train, X_train.columns.to_list(), use_wandb=False, processed_data_dir=dtmp)
                per_perm = anollm.decision_function(X_test, n_permutations=r, batch_size=bs, device=device)
            break
        except Exception as e:  # noqa: BLE001 — narrow to OOM below, re-raise everything else
            if not _is_oom(e) or bs <= 1:
                raise
            if device == "cuda":
                torch.cuda.empty_cache()
            new_bs = max(1, bs // 2)
            print(f"[oom-retry] batch {bs} OOM on {model_name} -> retrying at {new_bs}", flush=True)
            bs = new_bs

    return {
        "mean": np.asarray(per_perm).mean(axis=1),
        "per_permutation": np.asarray(per_perm),
        "lora": lora_cfg,
        "device": device,
        "r": int(r),
        "precision": precision,
        "batch_size": bs,
    }


def r_sensitivity(per_permutation: np.ndarray, r_values=(5, 8, 10, 21)) -> dict:
    """Free r-sensitivity: mean over the first k permutations, for each k (no re-run)."""
    n_perm = per_permutation.shape[1]
    return {int(k): per_permutation[:, : min(k, n_perm)].mean(axis=1) for k in r_values if k <= n_perm}
