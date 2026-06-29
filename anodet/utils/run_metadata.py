"""RunMetadata — the per-run provenance block embedded in every result JSON.

Designed so any number in the paper reconstructs to the exact code + env + data + model +
config that produced it (see the implementation plan's Traceability section). Import-light:
torch/transformers are captured only if installed.
"""
from __future__ import annotations

import dataclasses
import platform
import subprocess
import time
from dataclasses import dataclass, field
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Optional

from .io import atomic_write_json, content_hash

REPO_ROOT = Path(__file__).resolve().parents[2]
_KEY_LIBS = (
    "torch", "transformers", "peft", "datasets", "accelerate",
    "pyod", "deepod", "scikit-learn", "numpy", "scipy", "pandas",
)


def _run_git(*args: str, cwd: Path = REPO_ROOT) -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=10
        )
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def git_sha(cwd: Path = REPO_ROOT) -> Optional[str]:
    return _run_git("rev-parse", "HEAD", cwd=cwd)


def git_dirty(cwd: Path = REPO_ROOT) -> Optional[bool]:
    status = _run_git("status", "--porcelain", cwd=cwd)
    return None if status is None else bool(status)


def submodule_ref(name: str = "third_party/AnoLLM") -> Optional[str]:
    sub = REPO_ROOT / name
    return git_sha(cwd=sub) if sub.exists() else None


def uv_lock_hash() -> Optional[str]:
    lock = REPO_ROOT / "uv.lock"
    return content_hash(lock) if lock.exists() else None


def lib_versions() -> dict[str, str]:
    out: dict[str, str] = {}
    for lib in _KEY_LIBS:
        try:
            out[lib] = importlib_metadata.version(lib)
        except importlib_metadata.PackageNotFoundError:
            continue
    return out


def device_info() -> dict[str, Any]:
    info: dict[str, Any] = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
    }
    try:
        import torch

        info["torch_cuda_available"] = torch.cuda.is_available()
        info["torch_mps_available"] = bool(getattr(torch.backends, "mps", None)) and torch.backends.mps.is_available()
        if torch.cuda.is_available():
            info["gpu"] = torch.cuda.get_device_name(0)
            info["cuda"] = torch.version.cuda
    except ImportError:
        pass
    return info


def capture_env(engine: str = "hf", parity_status: Optional[str] = None) -> dict[str, Any]:
    """Env provenance block: code refs, lockfile hash, lib versions, device, engine."""
    return {
        "git_sha": git_sha(),
        "git_dirty": git_dirty(),
        "anollm_submodule_sha": submodule_ref(),
        "uv_lock_hash": uv_lock_hash(),
        "lib_versions": lib_versions(),
        "engine": engine,  # 'hf' everywhere in v1 (no vLLM)
        "logprob_parity_status": parity_status,
        "device": device_info(),
    }


@dataclass
class RunMetadata:
    """Full provenance for one (model, mode, dataset, seed) cell."""

    # identity (the cell key)
    experiment: str
    model: str
    mode: str  # 'likelihood' (A) | 'prompted' (B) | 'classical' | baseline name
    dataset: str
    seed: int

    # model provenance
    hf_revision: Optional[str] = None
    checkpoint_kind: Optional[str] = None  # 'instruct' | 'base'
    lora: Optional[dict] = None  # rank/alpha/target_modules/steps/lr (None for mode B/classical)
    precision: Optional[str] = None  # 'fp16' | 'bf16' | '4bit' | ...

    # data provenance
    dataset_content_hash: Optional[str] = None
    split_index_hash: Optional[str] = None
    subsample_index_hash: Optional[str] = None
    dataset_version_id: Optional[str] = None  # e.g. Kaggle dataset version

    # scoring provenance
    r_permutations: Optional[int] = None
    decode_config: Optional[dict] = None
    rendered_prompt_hash: Optional[str] = None
    serialization_template_hash: Optional[str] = None

    # env (filled by capture_env)
    env: dict = field(default_factory=capture_env)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def cell_key(model: str, mode: str, dataset: str, seed: int) -> str:
    """Deterministic, filename-safe key for one run cell."""
    safe = lambda s: str(s).replace("/", "-").replace(" ", "_")
    return f"{safe(model)}__{safe(mode)}__{safe(dataset)}__seed{seed}"


def cell_path(results_root: str | Path, experiment: str, key: str) -> Path:
    return Path(results_root) / "raw" / experiment / f"{key}.json"


def is_complete(path: str | Path) -> bool:
    """A cell is reusable iff its JSON exists, parses, and status == 'complete'."""
    from .io import read_json

    p = Path(path)
    if not p.exists():
        return False
    try:
        return read_json(p).get("status") == "complete"
    except Exception:
        return False  # partial / corrupt -> re-run


def write_result(
    results_root: str | Path,
    meta: RunMetadata,
    *,
    metrics: dict,
    status: str = "complete",
    n_rows_scored: Optional[int] = None,
    n_rows_expected: Optional[int] = None,
    cost: Optional[dict] = None,
    extra: Optional[dict] = None,
) -> Path:
    """Write one per-cell result JSON atomically (the system of record)."""
    key = cell_key(meta.model, meta.mode, meta.dataset, meta.seed)
    path = cell_path(results_root, meta.experiment, key)
    payload = {
        "key": key,
        "status": status,
        "n_rows_scored": n_rows_scored,
        "n_rows_expected": n_rows_expected,
        "timestamp_unix": int(time.time()),
        "metrics": metrics,
        "cost": cost or {},
        "run_metadata": meta.to_dict(),
    }
    if extra:
        payload["extra"] = extra
    return atomic_write_json(path, payload)
