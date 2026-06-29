"""Semantic vs anonymized column names (Exp 3b / RQ3b).

ODDS `.mat` files ship only X + y, so real column names must be recovered from the UCI source and
**aligned to the .mat column order**. The canonical names below are the UCI feature orders for two
genuinely-semantic sets (`pima`, `breastw` backup). Alignment to the actual loaded column order is a
verification gate (PLAN §2c, "Day-0 sub-step"): `semantic_names()` only asserts the *count* matches;
the *order* correspondence must be confirmed against the UCI source before any confirmatory Exp 3b run.

Use `apply_semantic` to rename to real names and `anonymize` to rename to `col_0..col_{n-1}`; the Exp 3b
delta is (semantic AUROC − anonymized AUROC) on the same model/mode/split.
"""
from __future__ import annotations

import pandas as pd

# UCI feature orders (recover from source; ORDER must be verified against the .mat before confirmatory use).
_UCI_NAMES = {
    # Pima Indians Diabetes — 8 features
    "pima": [
        "pregnancies", "glucose", "blood_pressure", "skin_thickness",
        "insulin", "bmi", "diabetes_pedigree", "age",
    ],
    # Wisconsin Breast Cancer (original) — 9 features
    "breastw": [
        "clump_thickness", "uniformity_cell_size", "uniformity_cell_shape", "marginal_adhesion",
        "single_epithelial_cell_size", "bare_nuclei", "bland_chromatin", "normal_nucleoli", "mitoses",
    ],
}

SEMANTIC_DATASETS = tuple(_UCI_NAMES)


def semantic_names(dataset: str, n_cols: int) -> list[str]:
    """Canonical UCI feature names for `dataset`; raises if count != n_cols (alignment guard)."""
    if dataset not in _UCI_NAMES:
        raise KeyError(f"no semantic names recorded for '{dataset}' (have {list(_UCI_NAMES)})")
    names = _UCI_NAMES[dataset]
    if len(names) != n_cols:
        raise ValueError(
            f"'{dataset}' has {n_cols} loaded columns but {len(names)} recorded names — "
            "verify UCI order alignment before use (PLAN §2c)"
        )
    return list(names)


def apply_semantic(df: pd.DataFrame, dataset: str) -> pd.DataFrame:
    """Return a copy of df with columns renamed to recovered semantic names (order-aligned)."""
    return df.set_axis(semantic_names(dataset, df.shape[1]), axis=1)


def anonymize(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with columns renamed to col_0..col_{n-1} (the anonymized arm)."""
    return df.set_axis([f"col_{i}" for i in range(df.shape[1])], axis=1)
