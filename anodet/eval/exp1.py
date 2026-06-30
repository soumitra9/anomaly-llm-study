"""Exp 1 — AnoLLM reproduction runner (mode A / likelihood).

One cell = one (model, dataset, split). Loads via the fork's `load_data` (same protocol/binning),
fine-tunes + NLL-scores, computes our metrics + the free r-sensitivity curve, and writes a per-cell
JSON through `anodet.utils.run_metadata` (resumable; reconciled by the manifest).

CLI (gate on Kaggle):  uv run python -m anodet.eval.exp1 --dataset breastw --model smol-360 \
                          --split-idx 0 --max-steps 2000 --r 21
Local validation:      ... --max-steps 10 --r 2 --device cpu
"""
from __future__ import annotations

import argparse
import types
from typing import Optional

import numpy as np

from anodet import _fork
from anodet.data.hparams import get_hparams
from anodet.metrics import auprc, auprc_gain, auroc, recall_at_fpr
from anodet.scoring.likelihood import r_sensitivity, run_likelihood
from anodet.utils.io import array_hash, frame_hash
from anodet.utils.run_metadata import RunMetadata, write_result


class _Args(types.SimpleNamespace):
    def __contains__(self, k):  # load_data() uses both attr access and `'x' in args`
        return k in self.__dict__


def _metrics(y, scores) -> dict:
    return {
        "auroc": auroc(y, scores),
        "auprc": auprc(y, scores),
        "auprc_gain": auprc_gain(y, scores),
        "recall_at_1pct_fpr": recall_at_fpr(y, scores, 0.01),
    }


def reproduce_cell(
    dataset: str,
    model: str = "smol-360",
    *,
    split_idx: int = 0,
    n_splits: int = 5,
    setting: str = "semi_supervised",
    binning: str = "standard",
    max_steps: int = 2000,
    r: int = 21,
    lora: Optional[bool] = None,
    batch_size: Optional[int] = None,
    device: Optional[str] = None,
    results_root: str = "results",
) -> dict:
    _fork.setup_env()
    _, data_utils = _fork.import_fork()

    # Per-dataset (batch, lora) from AnoLLM Table 7 (faithful + fits memory); explicit args override.
    cfg_bs, cfg_lora = get_hparams(dataset)
    if batch_size is None:
        batch_size = cfg_bs
    if lora is None:
        lora = cfg_lora

    args = _Args(
        dataset=dataset, setting=setting, data_dir=str(_fork.DATA_DIR),
        n_splits=n_splits, split_idx=split_idx, train_ratio=0.5, seed=42,
        binning=binning, n_buckets=10, remove_feature_name=False,
    )
    with _fork.cwd_fork():  # data_utils/adbench safest with cwd at the fork root
        X_train, X_test, y_train, y_test = data_utils.load_data(args)
        text_cols = data_utils.get_text_columns(dataset)
        max_len = data_utils.get_max_length_dict(dataset)
    y_test = np.asarray(y_test)

    out = run_likelihood(
        model, X_train, X_test, text_columns=text_cols, max_length_dict=max_len,
        lora=lora, max_steps=max_steps, r=r, batch_size=batch_size, device=device,
    )

    metrics = _metrics(y_test, out["mean"])
    # free r-sensitivity: AUROC at each prefix length
    metrics["r_sensitivity_auroc"] = {
        k: auroc(y_test, s) for k, s in r_sensitivity(out["per_permutation"]).items()
    }

    meta = RunMetadata(
        experiment="exp1_repro",
        model=model,
        mode="likelihood",
        dataset=dataset,
        seed=split_idx,
        hf_revision=None,  # filled at run time in M-gate (resolve HF revision hash)
        checkpoint_kind="base",  # Exp 1 reproduces AnoLLM's base + (full or lora) FT
        lora=out["lora"],
        precision=out["precision"],
        r_permutations=out["r"],
        split_index_hash=array_hash(np.asarray(X_test.index)),
        dataset_content_hash=frame_hash(X_test),  # type-robust: handles text columns (e.g. lymphography)
    )
    meta.env["device_used"] = out["device"]
    write_result(
        results_root, meta, metrics=metrics, status="complete",
        n_rows_scored=int(len(y_test)), n_rows_expected=int(len(y_test)),
        extra={"setting": setting, "binning": binning, "n_splits": n_splits,
               "max_steps": max_steps, "batch_size": out["batch_size"],
               "score_batch_size": out["score_batch_size"],
               "test_anomaly_rate": float(y_test.mean())},
    )
    return metrics


def _cli():
    p = argparse.ArgumentParser(description="Exp 1 AnoLLM reproduction (mode A)")
    p.add_argument("--dataset", required=True)
    p.add_argument("--model", default="smol-360")
    p.add_argument("--split-idx", type=int, default=0)
    p.add_argument("--n-splits", type=int, default=5)
    p.add_argument("--setting", default="semi_supervised")
    p.add_argument("--binning", default="standard")
    p.add_argument("--max-steps", type=int, default=2000)
    p.add_argument("--r", type=int, default=21)
    p.add_argument("--lora", action=argparse.BooleanOptionalAction, default=None,
                   help="override per-dataset LoRA from configs/anollm_hparams.yaml (default: use config)")
    p.add_argument("--batch-size", type=int, default=None,
                   help="override per-dataset batch from configs/anollm_hparams.yaml (default: use config)")
    p.add_argument("--device", default=None)
    p.add_argument("--results-root", default="results")
    a = p.parse_args()
    m = reproduce_cell(
        a.dataset, a.model, split_idx=a.split_idx, n_splits=a.n_splits, setting=a.setting,
        binning=a.binning, max_steps=a.max_steps, r=a.r, lora=a.lora,
        batch_size=a.batch_size, device=a.device, results_root=a.results_root,
    )
    print(f"[exp1] {a.dataset} {a.model} split{a.split_idx}: "
          f"AUROC={m['auroc']:.3f} AUPRC={m['auprc']:.3f} "
          f"recall@1%FPR={m['recall_at_1pct_fpr']:.3f}")


if __name__ == "__main__":
    _cli()
