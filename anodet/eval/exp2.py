"""Exp 2 — model generation × scoring mode on ODDS (RQ2, RQ3).

The headline same-model A/B: for each (model, mode, dataset, seed) cell, score the *same* ODDS rows
either by **likelihood** (mode A: LoRA fine-tune the base backbone, mean NLL over r permutations) or
by **prompted** expected-value (mode B: the frozen instruct sibling, single forward pass). Differs from
the Exp 1 gate only in: LoRA (not full) FT, the modern models, and the added prompted mode.

Cells are driven by `anodet.eval.grid` over `configs/exp2.yaml` (resumable; manifest-reconciled). The
"seed" axis is the ODDS split index (matches `exp1.reproduce_cell`'s seed==split_idx convention), so the
3 seeds are 3 of the 5 ODDS splits — split-variance, per PLAN §7.

CLI (single-cell local validation):
  uv run python -m anodet.eval.exp2 --dataset breastw --model smol-360 --mode prompted \
       --max-steps 10 --r 2 --device cpu
Full sweep:
  uv run python -m anodet.eval.exp2 --config configs/exp2.yaml
"""
from __future__ import annotations

import argparse
import hashlib
from typing import Callable, Optional

import numpy as np

from anodet.data.odds import load_odds
from anodet.eval import grid
from anodet.metrics import auprc, auprc_gain, auroc, recall_at_fpr
from anodet.scoring.likelihood import r_sensitivity, run_likelihood
from anodet.scoring.prompted import run_prompted
from anodet.utils.seeding import seed_everything

_SERIALIZE_FMT = "col is value , ..."  # serialize_rows() template marker (for provenance hashing)


def _h(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def _metrics(y, scores) -> dict:
    return {
        "auroc": auroc(y, scores),
        "auprc": auprc(y, scores),
        "auprc_gain": auprc_gain(y, scores),
        "recall_at_1pct_fpr": recall_at_fpr(y, scores, 0.01),
    }


def run_one(
    dataset: str,
    model: str,
    mode: str,
    *,
    split_idx: int = 0,
    n_splits: int = 5,
    max_steps: int = 2000,
    r: int = 10,
    n_levels: int = 10,
    batch_size: int = 32,
    device: Optional[str] = None,
) -> tuple[dict, str, dict]:
    """Run one Exp 2 cell. Returns (metrics, status, extra) per the grid `run_cell` contract."""
    seed_everything(split_idx)
    data = load_odds(dataset, split_idx=split_idx, n_splits=n_splits)
    y_test = data["y_test"]
    common_meta = {
        "dataset_content_hash": data["content_hash"],
        "split_index_hash": data["split_index_hash"],
    }

    if mode == "likelihood":
        out = run_likelihood(
            model, data["X_train"], data["X_test"],
            text_columns=data["text_columns"], max_length_dict=data["max_length_dict"],
            lora=True, max_steps=max_steps, r=r, batch_size=batch_size, device=device,
        )
        metrics = _metrics(y_test, out["mean"])
        metrics["r_sensitivity_auroc"] = {
            k: auroc(y_test, s) for k, s in r_sensitivity(out["per_permutation"]).items()
        }
        run_metadata = {
            **common_meta,
            "checkpoint_kind": "base",
            "lora": out["lora"],
            "precision": "bf16" if out["device"] == "cuda" else "fp32",
            "r_permutations": out["r"],
            "serialization_template_hash": _h(_SERIALIZE_FMT),
        }
        extra = {"run_metadata": run_metadata, "n_rows_scored": int(len(y_test)),
                 "n_rows_expected": int(len(y_test)), "device_used": out["device"],
                 "max_steps": max_steps}

    elif mode == "prompted":
        out = run_prompted(
            f"{model}-instruct", data["X_test"],
            n_levels=n_levels, batch_size=batch_size, device=device,
        )
        metrics = _metrics(y_test, out["scores"])
        metrics["distinct_levels"] = out["distinct_levels"]
        run_metadata = {
            **common_meta,
            "checkpoint_kind": "instruct",
            "precision": "bf16" if out["device"] == "cuda" else "fp32",
            "decode_config": {"scorer": "expected_value", "n_levels": n_levels, "temperature": 0},
            "serialization_template_hash": _h(_SERIALIZE_FMT),
            "rendered_prompt_hash": _h(f"{_SERIALIZE_FMT}|n_levels={n_levels}"),
        }
        extra = {"run_metadata": run_metadata, "n_rows_scored": int(len(y_test)),
                 "n_rows_expected": int(len(y_test)), "device_used": out["device"],
                 "distinct_levels": out["distinct_levels"]}

    else:
        raise ValueError(f"unknown mode '{mode}' (expected 'likelihood' or 'prompted')")

    return metrics, "complete", extra


def make_run_cell(**hparams) -> Callable[[dict], tuple[dict, str, dict]]:
    """Bind hyperparameters into a grid `run_cell(cell)` closure (seed == ODDS split_idx)."""
    def run_cell(cell: dict) -> tuple[dict, str, dict]:
        return run_one(
            cell["dataset"], cell["model"], cell["mode"],
            split_idx=int(cell["seed"]), **hparams,
        )
    return run_cell


def run(config_path: str, results_root: str = "results", **hparams) -> int:
    """Run all pending cells of `config_path`; returns the number of cells run."""
    cfg = grid.load_config(config_path)
    return grid.run_grid(cfg, results_root, make_run_cell(**hparams))


def _cli():
    p = argparse.ArgumentParser(description="Exp 2 — model × scoring-mode on ODDS")
    p.add_argument("--config", default=None, help="run the full sweep from a YAML config")
    p.add_argument("--dataset")
    p.add_argument("--model", default="smol-360")
    p.add_argument("--mode", default="prompted", choices=["likelihood", "prompted"])
    p.add_argument("--split-idx", type=int, default=0)
    p.add_argument("--n-splits", type=int, default=5)
    p.add_argument("--max-steps", type=int, default=2000)
    p.add_argument("--r", type=int, default=10)
    p.add_argument("--n-levels", type=int, default=10)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--device", default=None)
    p.add_argument("--results-root", default="results")
    a = p.parse_args()

    hparams = dict(max_steps=a.max_steps, r=a.r, n_levels=a.n_levels,
                   batch_size=a.batch_size, device=a.device, n_splits=a.n_splits)

    if a.config:
        n = run(a.config, a.results_root, **hparams)
        print(f"[exp2] ran {n} pending cell(s) from {a.config}")
        return

    if not a.dataset:
        p.error("provide --dataset for a single cell, or --config for the full sweep")

    metrics, status, extra = run_one(a.dataset, a.model, a.mode, split_idx=a.split_idx, **hparams)
    # single-cell mode still writes a per-cell JSON (mirrors the grid path)
    from anodet.utils.run_metadata import RunMetadata, write_result
    meta = RunMetadata(experiment="exp2_odds", model=a.model, mode=a.mode,
                       dataset=a.dataset, seed=a.split_idx, **extra["run_metadata"])
    write_result(a.results_root, meta, metrics=metrics, status=status,
                 n_rows_scored=extra["n_rows_scored"], n_rows_expected=extra["n_rows_expected"],
                 extra={k: v for k, v in extra.items()
                        if k not in {"run_metadata", "n_rows_scored", "n_rows_expected"}})
    print(f"[exp2] {a.dataset} {a.model} {a.mode} split{a.split_idx}: "
          f"AUROC={metrics['auroc']:.3f} AUPRC={metrics['auprc']:.3f} "
          f"recall@1%FPR={metrics['recall_at_1pct_fpr']:.3f} (device={extra['device_used']})")


if __name__ == "__main__":
    _cli()
