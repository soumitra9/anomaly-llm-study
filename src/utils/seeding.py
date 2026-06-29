"""Deterministic, centralized seeding.

All randomness in the project routes through here so a run is reproducible from its
logged seed. Frameworks (numpy, random, torch) are seeded from one integer; per-component
generators are derived deterministically from the same seed so independent components don't
share or collide RNG state.

torch is seeded only if installed (kept import-light for M0).
"""
from __future__ import annotations

import hashlib
import os
import random

import numpy as np


def _derive_int(seed: int, label: str, bits: int = 32) -> int:
    """Deterministically derive a sub-seed from (seed, label). Stable across runs/platforms."""
    h = hashlib.sha256(f"{seed}:{label}".encode()).digest()
    return int.from_bytes(h[: bits // 8], "big")


def seed_everything(seed: int, *, deterministic_torch: bool = True) -> None:
    """Seed python, numpy, and (if present) torch from a single integer."""
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed % (2**32))
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        if deterministic_torch:
            # Best-effort determinism; some ops lack deterministic kernels (warn-only).
            torch.use_deterministic_algorithms(True, warn_only=True)
    except ImportError:
        pass


def rng(seed: int, label: str) -> np.random.Generator:
    """Return an independent numpy Generator derived from (seed, label).

    Use a distinct `label` per component (e.g. 'normal_subsample', 'bootstrap') so each
    gets its own reproducible stream that does not collide with others.
    """
    return np.random.default_rng(_derive_int(seed, label))
