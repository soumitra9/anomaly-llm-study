"""UNSW-NB15 loader (Exp 3 / RQ4) — mixed-type network flows with rich named features.

~2.5M flows; we subsample to ~200-400k, run a leakage screen (PLAN §2c), and reweight subsampled negatives.
The leakage screen drops identifier/label columns and screens look-ahead `ct_*` connection-tracking features:
any single feature that alone yields near-perfect AUROC is flagged as suspected leakage.

DOWNLOAD (out-of-band): via the `nids-datasets` package (Network-Flows subset) or a local CSV/parquet.
`leakage_screen` / `prepare_unsw` are pure functions (testable on synthetic frames).
[provisional — verify the real schema, dropped columns, and base rate in Phase B]
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from anodet.metrics import auroc, make_importance_weights
from anodet.utils.io import frame_hash

LABEL = "label"
# identifiers + leakage-prone columns dropped unconditionally (PLAN §2c)
DROP_ALWAYS = ["label", "attack_cat", "id", "srcip", "dstip", "sport", "dsport"]


def leakage_screen(df: pd.DataFrame, *, label_col: str = LABEL,
                   drop_always=DROP_ALWAYS, ct_auroc_threshold: float = 0.99) -> dict:
    """Drop identifiers/labels; flag+drop single-feature look-ahead `ct_*` columns above the AUROC threshold.

    Returns {'X': features-only frame, 'y': labels, 'dropped': [...], 'flagged': {col: auroc}}.
    """
    if label_col not in df.columns:
        raise KeyError(f"label column '{label_col}' not in frame")
    y = df[label_col].to_numpy().astype(int)
    dropped = [c for c in drop_always if c in df.columns]
    work = df.drop(columns=dropped)

    flagged = {}
    for c in [c for c in work.columns if c.startswith("ct_")]:
        col = pd.to_numeric(work[c], errors="coerce")
        if col.notna().all() and col.nunique() > 1:
            a = auroc(y, col.to_numpy())
            a = max(a, 1 - a)  # direction-agnostic
            if a >= ct_auroc_threshold:
                flagged[c] = float(a)
    work = work.drop(columns=list(flagged))
    return {"X": work.reset_index(drop=True), "y": y, "dropped": dropped, "flagged": flagged}


def prepare_unsw(df: pd.DataFrame, *, subsample: Optional[int] = 300000,
                 test_frac: float = 0.5, max_test_neg: Optional[int] = 40000, seed: int = 42) -> dict:
    """Leakage-screen -> subsample -> uncontaminated split -> reweight. Mirrors creditcard's contract."""
    screen = leakage_screen(df)
    X, y = screen["X"], screen["y"]
    rng = np.random.default_rng(seed)

    if subsample is not None and len(X) > subsample:
        idx = rng.choice(len(X), size=subsample, replace=False)
        X, y = X.iloc[idx].reset_index(drop=True), y[idx]

    perm = rng.permutation(len(X))
    cut = int(len(X) * (1 - test_frac))
    tr, te = perm[:cut], perm[cut:]
    X_train = X.iloc[tr][y[tr] == 0].reset_index(drop=True)  # normals only

    Xte_all, yte_all = X.iloc[te].reset_index(drop=True), y[te]
    pos = np.where(yte_all == 1)[0]
    neg = np.where(yte_all == 0)[0]
    n_neg_total = len(neg)
    if max_test_neg is not None and n_neg_total > max_test_neg:
        neg = rng.choice(neg, size=max_test_neg, replace=False)
    keep = rng.permutation(np.concatenate([pos, neg]))
    X_test, y_test = Xte_all.iloc[keep].reset_index(drop=True), yte_all[keep]
    weights = make_importance_weights(y_test, n_neg_total)

    return {"X_train": X_train, "X_test": X_test, "y_test": y_test, "sample_weight": weights,
            "content_hash": frame_hash(X_test), "dropped": screen["dropped"], "flagged": screen["flagged"],
            "n_neg_total": int(n_neg_total), "n_neg_scored": int(len(neg))}
