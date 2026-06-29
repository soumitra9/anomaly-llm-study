"""Credit Card Fraud loader (Exp 3 / RQ4) — ULB dataset, ODbL.

284,807 transactions, 0.17% fraud, numeric (Time, V1..V28 PCA, Amount, Class). Per PLAN §2c we run BOTH a
**temporal** split (train earlier, test later — realistic) and a **random** split (AnoLLM comparability),
cap the scored test set via negative subsampling, and recover the true-base-rate AUPRC with importance
reweighting (`metrics.make_importance_weights`).

DOWNLOAD (out-of-band, once): via Kaggle MCP `download_dataset(ownerSlug='mlg-ulb', datasetSlug='creditcardfraud')`
-> `creditcard.csv`; pin the dataset version id into RunMetadata. ODbL recorded in DATA_LICENSES.md.
`prepare_creditcard` is a pure function (testable on synthetic frames); `load_creditcard` reads the CSV.
[provisional — validate schema/base-rate on the real download in Phase B]
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from anodet.metrics import make_importance_weights
from anodet.utils.io import frame_hash

LABEL = "Class"
TIME = "Time"


def prepare_creditcard(
    df: pd.DataFrame,
    *,
    split: str = "temporal",
    test_frac: float = 0.5,
    max_test_neg: Optional[int] = 20000,
    seed: int = 42,
) -> dict:
    """Split + subsample + reweight. Returns X_train, X_test, y_test, sample_weight, hashes, base_rate.

    Train uses NORMALS only (uncontaminated, AnoLLM protocol). Test = held-out normals (optionally
    subsampled) + all held-out frauds; `sample_weight` upweights subsampled negatives to the true base rate.
    """
    if split == "temporal":
        df = df.sort_values(TIME).reset_index(drop=True)
        cut = int(len(df) * (1 - test_frac))
        train_df, test_df = df.iloc[:cut], df.iloc[cut:]
    elif split == "random":
        rng = np.random.default_rng(seed)
        perm = rng.permutation(len(df))
        cut = int(len(df) * (1 - test_frac))
        train_df, test_df = df.iloc[perm[:cut]], df.iloc[perm[cut:]]
    else:
        raise ValueError(f"split must be 'temporal' or 'random' (got {split!r})")

    feat = [c for c in df.columns if c != LABEL]
    X_train = train_df[train_df[LABEL] == 0][feat].reset_index(drop=True)  # normals only

    pos = test_df[test_df[LABEL] == 1]
    neg = test_df[test_df[LABEL] == 0]
    n_neg_total = len(neg)
    if max_test_neg is not None and n_neg_total > max_test_neg:
        neg = neg.sample(n=max_test_neg, random_state=seed)
    test = pd.concat([pos, neg]).sample(frac=1, random_state=seed).reset_index(drop=True)
    y_test = test[LABEL].to_numpy().astype(int)
    X_test = test[feat].reset_index(drop=True)
    # importance weights: scale the (subsampled) negatives back to n_neg_total
    weights = make_importance_weights(y_test, n_neg_total)

    return {
        "X_train": X_train, "X_test": X_test, "y_test": y_test, "sample_weight": weights,
        "split": split, "content_hash": frame_hash(X_test),
        "true_base_rate": float((df[LABEL] == 1).mean()),
        "n_neg_total": int(n_neg_total), "n_neg_scored": int(len(neg)),
    }


def load_creditcard(csv_path: str, **kwargs) -> dict:
    """Read creditcard.csv and prepare it. `dataset_version_id` should be recorded separately in RunMetadata."""
    p = Path(csv_path)
    if not p.exists():
        raise FileNotFoundError(
            f"{csv_path} not found — download via Kaggle MCP download_dataset(mlg-ulb/creditcardfraud) first")
    return prepare_creditcard(pd.read_csv(p), **kwargs)
