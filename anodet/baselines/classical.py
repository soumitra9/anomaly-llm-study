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


def _encode_for_classical(
    X_train: pd.DataFrame, X_test: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Ordinal-encode any string/categorical columns before float-casting for classical detectors.

    Catches object dtype, pandas StringDtype (used in UNSW-NB15 parquet), and CategoricalDtype.
    Encoding is fit on the union of train+test categories so test never sees an unmapped value.
    Unknown values (NaN after mapping) are encoded as -1, which is a valid ordinal integer.
    ODDS data has no string columns so this is a no-op for all prior experiments; it only
    activates for mixed-type datasets like UNSW-NB15.
    """
    cat_cols = [
        c for c in X_train.columns
        if pd.api.types.is_object_dtype(X_train[c])
        or isinstance(X_train[c].dtype, (pd.CategoricalDtype, pd.StringDtype))
    ]
    if not cat_cols:
        return X_train, X_test

    X_tr = X_train.copy()
    X_te = X_test.copy()
    for col in cat_cols:
        combined = pd.concat([X_tr[col].astype(str), X_te[col].astype(str)], ignore_index=True)
        categories = pd.Categorical(combined).categories
        mapping = {v: i for i, v in enumerate(categories)}
        X_tr[col] = X_tr[col].astype(str).map(mapping).fillna(-1).astype(int)
        X_te[col] = X_te[col].astype(str).map(mapping).fillna(-1).astype(int)
    return X_tr, X_te


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
    """Fit `name` on X_train, return anomaly scores for X_test (higher = more anomalous).

    Ordinal-encodes any object/category columns before the float cast so mixed-type datasets
    (e.g. UNSW-NB15 with proto/state/service string columns) work without preprocessing outside
    this function. Encoding is consistent across train and test.
    """
    X_train, X_test = _encode_for_classical(X_train, X_test)
    clf = _make(name, seed)
    # Use .astype(float).to_numpy() instead of np.asarray(.., dtype=float) so pandas nullable
    # extension types (Int64, Float64, StringDtype) are converted correctly — pd.NA → np.nan.
    clf.fit(X_train.astype(float).to_numpy())
    return clf.decision_function(X_test.astype(float).to_numpy())


def run_panel(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    *,
    names: Optional[list[str]] = None,
    seed: int = 42,
) -> dict[str, np.ndarray]:
    """Run every baseline in `names` (default the full PANEL). Returns {name: scores}."""
    return {n: run_baseline(n, X_train, X_test, seed=seed) for n in (names or list(PANEL))}
