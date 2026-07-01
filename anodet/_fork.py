"""Bridge to the vendored AnoLLM fork (third_party/AnoLLM).

Centralizes every environment workaround discovered in M1 so the rest of `anodet` never repeats
them. The fork is run as-is: we import its `anollm` package and its `src.data_utils`. Our package
is `anodet` (renamed from `src`) precisely so it does not collide with the fork's own `src`.

Workarounds captured here (see README "do NOT re-derive"):
  - USE_TF=0: adbench pulls TF/Keras-3 which breaks transformers' lazy TF integration; we use torch.
  - single-process gloo group + LOCAL_RANK/WORLD_SIZE: AnoLLM's trainer is DDP/CUDA-hardwired.
  - sys.path: add the fork dir so `import anollm` / `import src.data_utils` resolve to the fork.
  - device pick: cuda > mps > cpu; bf16 only on cuda.
"""
from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FORK_DIR = REPO_ROOT / "third_party" / "AnoLLM"
DATA_DIR = REPO_ROOT / "data"  # gitignored; loaders + split caches live here

_ENV_READY = False
_DIST_READY = False


def setup_env() -> None:
    """Idempotent process-env setup. Call before importing transformers/anollm."""
    global _ENV_READY
    if _ENV_READY:
        return
    os.environ.setdefault("USE_TF", "0")
    os.environ.setdefault("USE_TORCH", "1")
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("WANDB_DISABLED", "true")
    for k, v in {
        "LOCAL_RANK": "0", "RANK": "0", "WORLD_SIZE": "1",
        "MASTER_ADDR": "127.0.0.1", "MASTER_PORT": "29500",
    }.items():
        os.environ.setdefault(k, v)
    if str(FORK_DIR) not in sys.path:
        sys.path.insert(0, str(FORK_DIR))  # fork's `anollm` + `src` (only `src` on path)
    _ENV_READY = True


def ensure_dist() -> None:
    """Init a 1-rank gloo process group so AnoLLM's DDP-hardwired trainer runs single-process."""
    global _DIST_READY
    if _DIST_READY:
        return
    setup_env()
    import torch.distributed as dist

    if not dist.is_initialized():
        dist.init_process_group(backend="gloo", rank=0, world_size=1)
    _DIST_READY = True


def pick_device(prefer: str | None = None) -> str:
    """cuda > mps > cpu, unless `prefer` overrides."""
    if prefer:
        return prefer
    import torch

    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


@contextlib.contextmanager
def cwd_fork():
    """Run a block with cwd at the fork root (data_utils/adbench assume relative paths there)."""
    prev = os.getcwd()
    os.chdir(FORK_DIR)
    try:
        yield
    finally:
        os.chdir(prev)


def import_fork():
    """Return (AnoLLM, data_utils_module) from the fork, after env setup."""
    setup_env()
    from anollm import AnoLLM  # type: ignore
    import src.data_utils as data_utils  # type: ignore  # fork's src, not ours (we are `anodet`)

    return AnoLLM, data_utils


# Canonical model aliases (mirror train_anollm.py get_args).
# Likelihood mode (A) fine-tunes the BASE backbone; prompted mode (B) uses the instruct sibling
# (see anodet.scoring.prompted.INSTRUCT_ALIASES). Qwen3-4B is our M2 scale-up extension (AnoLLM used SmolLM only).
MODEL_ALIASES = {
    "smol": "HuggingFaceTB/SmolLM-135M",
    "smol-360": "HuggingFaceTB/SmolLM-360M",
    "smol-1.7b": "HuggingFaceTB/SmolLM-1.7B",
    "qwen2.5-3b": "Qwen/Qwen2.5-3B",  # M2 scale-up base backbone (Qwen3 arch unsupported by pinned transformers 4.48.2); instruct sibling in prompted.INSTRUCT_ALIASES
}


def resolve_model(name: str) -> str:
    return MODEL_ALIASES.get(name, name)
