"""Classical baseline panel (PyOD) — the "beats-best-classical" comparands.

The four classical detectors AnoLLM reports (IForest, PCA, KNN, ECOD), via PyOD 2.0.1 (pinned). Each
fits on the (normal) training rows and scores the *same frozen* test set the LLMs score, so the
per-dataset tally is apples-to-apples. Higher `decision_function` = more anomalous (PyOD convention),
matching our metric direction. The 8 DeepOD deep baselines + custom ICL/DTE are deferred to M3.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

# Lazy imports inside _make so importing this module never requires pyod at collection time.
PANEL = ("iforest", "pca", "knn", "ecod")


def _make(name: str, seed: int):
    if name == "iforest":
        from pyod.models.iforest import IForest
        return IForest(random_state=seed)
    if name == "pca":
        from pyod.models.pca import PCA
        return PCA(random_state=seed)
    if name == "knn":
        from pyod.models.knn import KNN
        return KNN()  # deterministic; no random_state
    if name == "ecod":
        from pyod.models.ecod import ECOD
        return ECOD()  # parameter-free, deterministic
    raise KeyError(f"unknown baseline '{name}' (have {PANEL})")


def run_baseline(
    name: str,
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    *,
    seed: int = 42,
) -> np.ndarray:
    """Fit `name` on X_train, return anomaly scores for X_test (higher = more anomalous)."""
    clf = _make(name, seed)
    clf.fit(np.asarray(X_train.values, dtype=float))
    return np.asarray(clf.decision_function(np.asarray(X_test.values, dtype=float)))


def run_panel(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    *,
    names: Optional[list[str]] = None,
    seed: int = 42,
) -> dict[str, np.ndarray]:
    """Run every baseline in `names` (default the full PANEL). Returns {name: scores}."""
    return {n: run_baseline(n, X_train, X_test, seed=seed) for n in (names or list(PANEL))}
