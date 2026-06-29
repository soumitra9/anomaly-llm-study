"""Generic Cartesian-loop grid runner + completion manifest.

A config is a YAML of axis *lists* (models, modes, datasets, seeds). `expand_grid` produces
one cell per combination; `run_grid` runs each *pending* cell (skipping already-complete ones
for free resumption) via a caller-supplied `run_cell` callback that returns
`(metrics: dict, status: str, extra: dict)`. `write_manifest` records the expected grid and
the actual vs expected gap so aggregation can refuse to run on an incomplete grid.

This keeps experiment-specific logic (fine-tuning, prompting, baselines) out of the runner —
M1/M2 supply `run_cell`.
"""
from __future__ import annotations

import itertools
from pathlib import Path
from typing import Callable, Iterable

import yaml

from src.utils.io import atomic_write_json
from src.utils.run_metadata import cell_key, cell_path, is_complete


def load_config(path: str | Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def expand_grid(cfg: dict) -> list[dict]:
    """Expand axis-lists into one dict per (model, mode, dataset, seed) cell."""
    axes = cfg["axes"]
    models = axes["models"]
    modes = axes["modes"]
    datasets = axes["datasets"]
    seeds = axes["seeds"]
    cells = []
    for model, mode, dataset, seed in itertools.product(models, modes, datasets, seeds):
        cells.append({"model": model, "mode": mode, "dataset": dataset, "seed": int(seed)})
    return cells


def _path_for(cfg: dict, results_root: str | Path, cell: dict) -> Path:
    key = cell_key(cell["model"], cell["mode"], cell["dataset"], cell["seed"])
    return cell_path(results_root, cfg["experiment"], key)


def pending_cells(cfg: dict, results_root: str | Path) -> list[dict]:
    """Cells whose result JSON is missing or not status=='complete'."""
    return [c for c in expand_grid(cfg) if not is_complete(_path_for(cfg, results_root, c))]


def write_manifest(cfg: dict, results_root: str | Path) -> Path:
    """Write MANIFEST.jsonl: one line per expected cell with its completion status + gap count."""
    cells = expand_grid(cfg)
    lines = []
    n_missing = 0
    for c in cells:
        p = _path_for(cfg, results_root, c)
        complete = is_complete(p)
        n_missing += 0 if complete else 1
        lines.append({**c, "experiment": cfg["experiment"], "complete": complete, "path": str(p)})
    out = Path(results_root) / "MANIFEST.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(__import__("json").dumps(d, sort_keys=True) for d in lines) + "\n"
    tmp = out.with_suffix(".jsonl.tmp")
    tmp.write_text(text)
    tmp.replace(out)
    # also drop a tiny summary so a glance shows completeness
    atomic_write_json(
        Path(results_root) / "MANIFEST_summary.json",
        {"experiment": cfg["experiment"], "n_expected": len(cells), "n_missing": n_missing},
    )
    return out


def assert_grid_complete(cfg: dict, results_root: str | Path) -> None:
    """Raise (with the gap list) if any expected cell is missing/incomplete — gate for aggregation."""
    missing = pending_cells(cfg, results_root)
    if missing:
        keys = [cell_key(c["model"], c["mode"], c["dataset"], c["seed"]) for c in missing]
        raise RuntimeError(
            f"{len(missing)} incomplete cell(s) for experiment '{cfg['experiment']}':\n  "
            + "\n  ".join(keys[:50])
            + ("\n  ..." if len(keys) > 50 else "")
        )


def run_grid(
    cfg: dict,
    results_root: str | Path,
    run_cell: Callable[[dict], tuple[dict, str, dict]],
) -> int:
    """Run all pending cells. `run_cell(cell)` returns (metrics, status, extra). Returns #run."""
    from src.utils.run_metadata import RunMetadata, write_result

    pend = pending_cells(cfg, results_root)
    for cell in pend:
        metrics, status, extra = run_cell(cell)
        meta = RunMetadata(
            experiment=cfg["experiment"],
            model=cell["model"],
            mode=cell["mode"],
            dataset=cell["dataset"],
            seed=cell["seed"],
            **extra.get("run_metadata", {}),
        )
        write_result(
            results_root,
            meta,
            metrics=metrics,
            status=status,
            n_rows_scored=extra.get("n_rows_scored"),
            n_rows_expected=extra.get("n_rows_expected"),
            cost=extra.get("cost"),
            extra={k: v for k, v in extra.items() if k not in {"run_metadata", "cost", "n_rows_scored", "n_rows_expected"}},
        )
    write_manifest(cfg, results_root)
    return len(pend)
