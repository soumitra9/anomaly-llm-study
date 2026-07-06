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


def _apply_binning(X_train: pd.DataFrame, X_test: pd.DataFrame,
                   method: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply AnoLLM-compatible binning to numeric columns, fit on X_train only.

    method='standard': StandardScaler per numeric column, rounded to 1 dp.
    This matches the AnoLLM fork's normalize(..., 'standard') semantics but with correct
    train/test isolation (scaler fit on train, applied to both). ODDS datasets use this
    preprocessing before serialization; BA1 applies it to creditcard to bound the
    serialization confound between experiments.

    Only 'standard' is supported; add other methods if needed.
    Raw floats (None / method='none') are a no-op.
    """
    from sklearn.preprocessing import StandardScaler

    if method not in ("standard",):
        raise ValueError(f"binning method {method!r} not supported (have: 'standard')")

    numeric_cols = [c for c in X_train.columns
                    if X_train[c].dtype in (np.float64, np.float32, np.int64, np.int32)]
    Xtr = X_train.copy()
    Xte = X_test.copy()
    for col in numeric_cols:
        scaler = StandardScaler()
        Xtr[col] = scaler.fit_transform(Xtr[[col]]).round(1).ravel()
        Xte[col] = scaler.transform(Xte[[col]]).round(1).ravel()
    return Xtr, Xte


def prepare_creditcard(
    df: pd.DataFrame,
    *,
    split: str = "temporal",
    test_frac: float = 0.5,
    max_test_neg: Optional[int] = 20000,
    seed: int = 42,
    binning: Optional[str] = None,
    drop_time: bool = False,
) -> dict:
    """Split + subsample + reweight. Returns X_train, X_test, y_test, sample_weight, hashes, base_rate.

    AnoLLM protocol (uncontaminated): train = (1-test_frac) of the NORMALS only; test = the remaining
    normals (optionally subsampled) + **ALL** anomalies; `sample_weight` upweights subsampled negatives back
    to the true base rate. We split *normals* (not all rows) so every anomaly lands in test — splitting all
    rows would drop the train-half's anomalies.

    `binning`: if 'standard', apply StandardScaler per numeric column (fit on X_train, transform both),
    rounded to 1 dp — matching AnoLLM ODDS preprocessing for the BA1 confound check. Default None = raw
    floats (all prior M3 cells used this).

    `drop_time`: if True, exclude the 'Time' column from features used for scoring. 'Time' encodes temporal
    order and creates a train/test distribution shift under temporal splits; passing drop_time=True isolates
    the T3 confound check. Default False (M3 cells kept Time to stay consistent with prior run metadata).
    """
    exclude = {LABEL}
    if drop_time:
        exclude.add(TIME)
    feat = [c for c in df.columns if c not in exclude]
    normals = df[df[LABEL] == 0]
    anomalies = df[df[LABEL] == 1]  # every anomaly goes to test (uncontaminated training)

    if split == "temporal":
        normals = normals.sort_values(TIME)
        cut = int(len(normals) * (1 - test_frac))
        train_norm, test_norm = normals.iloc[:cut], normals.iloc[cut:]
    elif split == "random":
        rng = np.random.default_rng(seed)
        perm = rng.permutation(len(normals))
        cut = int(len(normals) * (1 - test_frac))
        train_norm, test_norm = normals.iloc[perm[:cut]], normals.iloc[perm[cut:]]
    else:
        raise ValueError(f"split must be 'temporal' or 'random' (got {split!r})")

    X_train = train_norm[feat].reset_index(drop=True)  # normals only

    n_neg_total = len(test_norm)
    test_neg = test_norm
    if max_test_neg is not None and n_neg_total > max_test_neg:
        test_neg = test_norm.sample(n=max_test_neg, random_state=seed)
    test = pd.concat([anomalies, test_neg]).sample(frac=1, random_state=seed).reset_index(drop=True)
    y_test = test[LABEL].to_numpy().astype(int)
    X_test = test[feat].reset_index(drop=True)

    if binning is not None:
        X_train, X_test = _apply_binning(X_train, X_test, method=binning)

    # importance weights: scale the (subsampled) negatives back to n_neg_total
    weights = make_importance_weights(y_test, n_neg_total)

    return {
        "X_train": X_train, "X_test": X_test, "y_test": y_test, "sample_weight": weights,
        "split": split, "content_hash": frame_hash(X_test),
        "true_base_rate": float((df[LABEL] == 1).mean()),
        "n_neg_total": int(n_neg_total), "n_neg_scored": int(len(test_neg)),
    }


def load_creditcard(csv_path: str, **kwargs) -> dict:
    """Read creditcard.csv and prepare it. `dataset_version_id` should be recorded separately in RunMetadata."""
    p = Path(csv_path)
    if not p.exists():
        raise FileNotFoundError(
            f"{csv_path} not found — download via Kaggle MCP download_dataset(mlg-ulb/creditcardfraud) first")
    return prepare_creditcard(pd.read_csv(p), **kwargs)
