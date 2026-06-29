"""ODDS loader — clean wrapper over the AnoLLM fork's `src.data_utils.load_data`.

One call = one (dataset, split) loaded through the *same* protocol/binning the Exp 1 gate uses
(see `anodet.eval.exp1.reproduce_cell`), so mode-A and mode-B in Exp 2 score identical rows. Returns
the train/test frames, the fork's text-column + max-length hints, and provenance hashes for RunMetadata.

Data lands in `_fork.DATA_DIR` (= REPO_ROOT/data, gitignored); most ODDS sets auto-download via
ucimlrepo on first use. The canonical 30-set list lives in `ODDS_30`.
"""
from __future__ import annotations

import types
from typing import Optional

import numpy as np

from anodet import _fork
from anodet.utils.io import array_hash, frame_hash

# 30 ODDS datasets (AnoLLM exp2-odds order) — mirror of scripts/kaggle_gate.ODDS_30.
ODDS_30 = [
    "wine", "breastw", "cardio", "ecoli", "lymphography", "vertebral", "wbc", "yeast", "heart",
    "glass", "ionosphere", "letter_recognition", "mammography", "pendigits", "pima", "satellite",
    "satimage-2", "thyroid", "vowels", "shuttle", "seismic", "optdigits", "annthyroid", "http",
    "smtp", "mulcross", "covertype", "musk", "arrhythmia", "speech",
]


class _Args(types.SimpleNamespace):
    """load_data() uses both attribute access and `'x' in args` membership."""

    def __contains__(self, k):
        return k in self.__dict__


def load_odds(
    name: str,
    *,
    split_idx: int = 0,
    n_splits: int = 5,
    setting: str = "semi_supervised",
    binning: str = "standard",
    train_ratio: float = 0.5,
    seed: int = 42,
    n_buckets: int = 10,
    remove_feature_name: bool = False,
) -> dict:
    """Load one ODDS split via the fork. Returns a dict:
    {'X_train','X_test','y_train','y_test','text_columns','max_length_dict',
     'content_hash','split_index_hash'}.
    """
    _fork.setup_env()
    _, data_utils = _fork.import_fork()

    args = _Args(
        dataset=name, setting=setting, data_dir=str(_fork.DATA_DIR),
        n_splits=n_splits, split_idx=split_idx, train_ratio=train_ratio, seed=seed,
        binning=binning, n_buckets=n_buckets, remove_feature_name=remove_feature_name,
    )
    with _fork.cwd_fork():  # data_utils/adbench assume cwd at the fork root
        X_train, X_test, y_train, y_test = data_utils.load_data(args)
        text_columns = data_utils.get_text_columns(name)
        max_length_dict = data_utils.get_max_length_dict(name)

    return {
        "X_train": X_train,
        "X_test": X_test,
        "y_train": np.asarray(y_train),
        "y_test": np.asarray(y_test),
        "text_columns": text_columns,
        "max_length_dict": max_length_dict,
        "content_hash": frame_hash(X_test),  # type-robust: handles text columns (e.g. lymphography)
        "split_index_hash": array_hash(np.asarray(X_test.index)),
    }
