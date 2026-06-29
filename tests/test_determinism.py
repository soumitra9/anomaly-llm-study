"""Determinism + traceability-core tests: seeding, atomic I/O, hashing, bootstrap."""
import numpy as np

from src.metrics import auroc, bootstrap_ci
from src.utils.io import array_hash, atomic_write_json, read_json
from src.utils.seeding import rng


def test_rng_same_seed_label_identical():
    a = rng(123, "x").random(5)
    b = rng(123, "x").random(5)
    assert np.allclose(a, b)


def test_rng_different_label_independent():
    a = rng(123, "x").random(5)
    c = rng(123, "y").random(5)
    assert not np.allclose(a, c)


def test_atomic_write_roundtrip_and_redaction(tmp_path):
    p = tmp_path / "nested" / "run.json"
    atomic_write_json(p, {"x": 1, "openai_api_key": "SECRET", "nested": {"hf_token": "T"}})
    d = read_json(p)
    assert d["x"] == 1
    assert d["openai_api_key"] == "***REDACTED***"
    assert d["nested"]["hf_token"] == "***REDACTED***"


def test_array_hash_stable_and_sensitive():
    assert array_hash(np.arange(10)) == array_hash(np.arange(10))
    assert array_hash(np.arange(10)) != array_hash(np.arange(11))


def test_bootstrap_ci_deterministic():
    g = np.random.default_rng(0)
    y = (g.random(500) < 0.3).astype(int)
    s = g.random(500)
    assert bootstrap_ci(auroc, y, s, n_boot=200, seed=7) == bootstrap_ci(
        auroc, y, s, n_boot=200, seed=7
    )
