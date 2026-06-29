"""Column-ordering + row serialization (Exp 4 / RQ5).

Exp 4 asks whether a *domain-informed* column order changes AUROC vs arbitrary / random orders.
The base text format is AnoLLM's "col is value , ..." (reused from `scoring.prompted.serialize_rows`);
this module only re-orders columns before serialization and provides deterministic random-permutation
controls. It does NOT claim CausalTAD mechanism transfer — it is an ablation of column order.
"""
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np
import pandas as pd

from anodet.scoring.prompted import serialize_rows


def arbitrary_order(df: pd.DataFrame) -> list[str]:
    """The frame's native column order (the 'as-loaded' control)."""
    return list(df.columns)


def random_order(df: pd.DataFrame, seed: int) -> list[str]:
    """A deterministic random permutation of columns (random-permutation control)."""
    rng = np.random.default_rng(seed)
    cols = list(df.columns)
    rng.shuffle(cols)
    return cols


def reorder(df: pd.DataFrame, order: Sequence[str]) -> pd.DataFrame:
    """Return df with columns in `order` (validates the set matches exactly)."""
    order = list(order)
    if set(order) != set(df.columns):
        missing = set(df.columns) - set(order)
        extra = set(order) - set(df.columns)
        raise ValueError(f"order mismatch: missing={sorted(missing)} extra={sorted(extra)}")
    return df[order]


def serialize(df: pd.DataFrame, order: Optional[Sequence[str]] = None) -> list[str]:
    """Serialize rows to 'col is value , ...' text, optionally after re-ordering columns."""
    if order is not None:
        df = reorder(df, order)
    return serialize_rows(df)
