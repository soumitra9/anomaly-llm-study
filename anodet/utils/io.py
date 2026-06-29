"""Atomic, hashable JSON I/O for the per-run result records (the system of record).

- `atomic_write_json`: tmp -> fsync -> os.replace, so a killed process never leaves a
  half-written JSON that parses (resumability on 12h Kaggle sessions depends on this).
- `content_hash` / `array_hash`: stable SHA-256 over files / numpy arrays for data + split
  provenance (a metric mismatch then implicates code, not silent data drift).
- `redact`: strip secrets from anything logged into RunMetadata.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

_SECRET_HINTS = ("api_key", "apikey", "token", "secret", "password", "hf_token")


def redact(obj: Any) -> Any:
    """Recursively replace values whose key looks secret with '***REDACTED***'."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(k, str) and any(h in k.lower() for h in _SECRET_HINTS):
                out[k] = "***REDACTED***"
            else:
                out[k] = redact(v)
        return out
    if isinstance(obj, (list, tuple)):
        return [redact(v) for v in obj]
    return obj


def atomic_write_json(path: str | Path, payload: dict, *, redact_secrets: bool = True) -> Path:
    """Write JSON atomically: write to a temp file in the same dir, fsync, then os.replace."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = redact(payload) if redact_secrets else payload
    text = json.dumps(data, indent=2, sort_keys=True, default=_json_default)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)  # atomic on POSIX
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return path


def read_json(path: str | Path) -> dict:
    with open(path) as f:
        return json.load(f)


def _json_default(o: Any):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(f"Not JSON-serializable: {type(o)}")


def content_hash(path: str | Path, *, algo: str = "sha256", chunk: int = 1 << 20) -> str:
    """Stable hash of a file's bytes (for dataset provenance)."""
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return f"{algo}:{h.hexdigest()}"


def array_hash(arr: np.ndarray, *, algo: str = "sha256") -> str:
    """Stable hash of a numpy array (for split / subsample index provenance).

    Uses C-contiguous bytes + shape + dtype so logically identical arrays hash identically.
    """
    a = np.ascontiguousarray(arr)
    h = hashlib.new(algo)
    h.update(str(a.dtype).encode())
    h.update(str(a.shape).encode())
    h.update(a.tobytes())
    return f"{algo}:{h.hexdigest()}"
