"""Engine-free numerics for prompted (mode B) scoring.

The expected-value scorer turns a model's distribution over a small set of "anomaly level"
tokens into a single continuous, tie-free score (PLAN §4b) — eliminating the ties/parse
failures of naive integer parsing. These functions are pure (no transformers) so they're
unit-tested in M0; the transformers-backed elicitation is added in M2.
"""
from __future__ import annotations

import re
from typing import Optional, Sequence

import numpy as np


def expected_score(levels: Sequence[float], logprobs: Sequence[float]) -> float:
    """Expected anomaly level under the model's distribution over the level tokens.

    `score = Σ_k softmax(logprobs)_k · levels_k`. Continuous and tie-free from a single
    forward pass. `logprobs` need not be normalized (softmax handles it); they are the
    model's log-probabilities for each candidate level token.
    """
    lv = np.asarray(levels, dtype=float).ravel()
    lp = np.asarray(logprobs, dtype=float).ravel()
    if lv.shape != lp.shape or lv.size == 0:
        raise ValueError("levels and logprobs must be same nonempty length")
    lp = lp - lp.max()  # stabilize
    p = np.exp(lp)
    p = p / p.sum()
    return float(np.dot(p, lv))


def parse_int_score(text: str, lo: int = 0, hi: int = 100) -> Optional[int]:
    """Naive fallback scorer: extract the first integer in [lo, hi] from model text.

    Returns None on failure (the caller records a parse-failure — a primary reported metric,
    PLAN §7). Handles "Score: 87", "87/100", surrounding prose; rejects spelled-out numbers,
    out-of-range, and empty/garbage.
    """
    if not text:
        return None
    for m in re.finditer(r"-?\d+", text):
        val = int(m.group())
        if lo <= val <= hi:
            return val
    return None


def parse_failure_rate(parsed: Sequence[Optional[int]]) -> float:
    """Fraction of None entries (rows whose integer score could not be parsed)."""
    parsed = list(parsed)
    if not parsed:
        return float("nan")
    return sum(1 for p in parsed if p is None) / len(parsed)
