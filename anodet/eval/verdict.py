"""M1 reproduction-gate verdict (RQ1) — judge our results against AnoLLM, per the PRE-REGISTERED spec.

Reads the per-cell JSON written by `anodet.eval.exp1`/`scripts.kaggle_gate` under
`results/raw/exp1_repro/`, aggregates per-dataset mean AUROC over splits, and compares to the published
reference in `configs/anollm_reference.yaml` against the criteria fixed in `GATE_SPEC.md`:

  C1  |mean(ours) - mean(published)| <= c1_tol            (aggregate; always available)
  C2  Spearman rho(per-dataset ours, published) >= c2_min (needs published per-dataset values)
  C3  >= c3_min_in_band / 30 within published +/-1 std    (needs published per-dataset mean+std)

C2/C3 degrade to INFORMATIONAL when per-dataset reference numbers are absent (see the YAML sourcing rule).
The verdict is PRELIMINARY until all expected cells are complete; this never inflates a pass.

CLI:  uv run python -m anodet.eval.verdict            # uses results/ + configs/anollm_reference.yaml
"""
from __future__ import annotations

import argparse
import glob
from collections import defaultdict
from pathlib import Path
from typing import Optional

import numpy as np
import yaml

from anodet.utils.io import read_json

# Pre-registered thresholds (GATE_SPEC.md). Overridable for tests, NOT to be loosened on real data.
C1_TOL = 0.02
C2_MIN = 0.80
C3_MIN_IN_BAND = 24
# C3 band = max(+/-1 published std, +/-C3_ABS_FLOOR). The floor (pre-results refinement, 2026-06-29) avoids a
# zero-width band on the 6 datasets whose published SE is ~0; matches C1's aggregate tolerance. See GATE_SPEC.md.
C3_ABS_FLOOR = 0.02
N_DATASETS = 30


def load_cells(results_root: str = "results", experiment: str = "exp1_repro") -> list[dict]:
    """Load every complete per-cell JSON for `experiment`."""
    paths = glob.glob(str(Path(results_root) / "raw" / experiment / "*.json"))
    cells = []
    for p in paths:
        d = read_json(p)
        if d.get("status") == "complete" and "auroc" in d.get("metrics", {}):
            cells.append(d)
    return cells


def per_dataset_mean_auroc(cells: list[dict]) -> dict[str, float]:
    """Mean AUROC per dataset, averaged over splits/seeds."""
    by_ds: dict[str, list[float]] = defaultdict(list)
    for c in cells:
        ds = c["run_metadata"]["dataset"]
        by_ds[ds].append(float(c["metrics"]["auroc"]))
    return {ds: float(np.mean(v)) for ds, v in by_ds.items()}


def compute_verdict(
    results_root: str = "results",
    reference_path: str = "configs/anollm_reference.yaml",
    *,
    experiment: str = "exp1_repro",
    c1_tol: float = C1_TOL,
    c2_min: float = C2_MIN,
    c3_min_in_band: int = C3_MIN_IN_BAND,
    c3_abs_floor: float = C3_ABS_FLOOR,
    n_datasets: int = N_DATASETS,
) -> dict:
    """Return a verdict dict: per-criterion pass/fail + values + coverage + overall PASS/FAIL/PRELIMINARY."""
    from scipy.stats import spearmanr

    ref = yaml.safe_load(Path(reference_path).read_text())
    ref_mean = ref.get("aggregate_mean")
    ref_pd: dict = ref.get("per_dataset") or {}

    cells = load_cells(results_root, experiment)
    ours = per_dataset_mean_auroc(cells)
    coverage = len(ours)
    complete = coverage >= n_datasets

    out: dict = {
        "coverage": coverage, "n_datasets": n_datasets, "complete": complete,
        "our_mean": None, "ref_mean": ref_mean, "criteria": {}, "verdict": None,
    }
    if not ours:
        out["verdict"] = "NO_DATA"
        return out

    our_mean = float(np.mean(list(ours.values())))
    out["our_mean"] = our_mean

    # C1 — aggregate mean (always available)
    c1_delta = abs(our_mean - ref_mean) if ref_mean is not None else None
    out["criteria"]["C1_mean"] = {
        "delta": c1_delta, "tol": c1_tol,
        "pass": (c1_delta is not None and c1_delta <= c1_tol),
        "status": "active" if ref_mean is not None else "no_reference",
    }

    # C2 / C3 — need per-dataset published numbers
    shared = [d for d in ours if d in ref_pd]
    if shared:
        rho = float(spearmanr([ours[d] for d in shared], [ref_pd[d]["mean"] for d in shared]).correlation)
        in_band = sum(
            abs(ours[d] - ref_pd[d]["mean"]) <= max(ref_pd[d].get("std", 0.0), c3_abs_floor)
            for d in shared
        )
        out["criteria"]["C2_rank"] = {"spearman": rho, "min": c2_min, "n_shared": len(shared),
                                      "pass": rho >= c2_min, "status": "active"}
        out["criteria"]["C3_band"] = {"in_band": int(in_band), "of": len(shared),
                                      "min_in_band": c3_min_in_band,
                                      "pass": in_band >= c3_min_in_band, "status": "active"}
    else:
        out["criteria"]["C2_rank"] = {"status": "informational_no_reference", "pass": None}
        out["criteria"]["C3_band"] = {"status": "informational_no_reference", "pass": None}

    # overall: PASS needs all ACTIVE criteria to pass AND full coverage; else PRELIMINARY/FAIL
    active = [c for c in out["criteria"].values() if c.get("status") == "active"]
    all_active_pass = all(c["pass"] for c in active) if active else False
    if not complete:
        out["verdict"] = "PRELIMINARY_PASS" if all_active_pass else "PRELIMINARY"
    else:
        out["verdict"] = "PASS" if all_active_pass else "FAIL"
    return out


def _fmt(v: dict) -> str:
    lines = [f"M1 gate verdict — coverage {v['coverage']}/{v['n_datasets']} "
             f"({'complete' if v['complete'] else 'PARTIAL'})"]
    if v["our_mean"] is not None:
        lines.append(f"  mean AUROC: ours={v['our_mean']:.4f}  published={v['ref_mean']}")
    for name, c in v["criteria"].items():
        p = {True: "PASS", False: "FAIL", None: "info"}[c.get("pass")]
        lines.append(f"  {name:9s} [{p}] {({k: round(x, 4) if isinstance(x, float) else x for k, x in c.items()})}")
    lines.append(f"  => VERDICT: {v['verdict']}")
    return "\n".join(lines)


def _cli():
    p = argparse.ArgumentParser(description="M1 reproduction-gate verdict")
    p.add_argument("--results-root", default="results")
    p.add_argument("--reference", default="configs/anollm_reference.yaml")
    p.add_argument("--experiment", default="exp1_repro")
    a = p.parse_args()
    print(_fmt(compute_verdict(a.results_root, a.reference, experiment=a.experiment)))


if __name__ == "__main__":
    _cli()
