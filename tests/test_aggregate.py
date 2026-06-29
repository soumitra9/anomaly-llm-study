"""Aggregation: flatten cells, mean/std over seeds, drop nested metrics, write CSV."""
from anodet.analysis.aggregate import aggregate, build, load_rows
from anodet.utils.io import atomic_write_json


def _cell(tmp, ds, model, mode, seed, auroc):
    atomic_write_json(
        tmp / "raw" / "exp2_odds" / f"{model}__{mode}__{ds}__seed{seed}.json",
        {"status": "complete",
         "metrics": {"auroc": auroc, "auprc": auroc - 0.1,
                     "r_sensitivity_auroc": {"5": auroc}},  # nested -> must be dropped
         "run_metadata": {"dataset": ds, "model": model, "mode": mode, "seed": seed}},
    )


def test_load_drops_nested_metrics(tmp_path):
    _cell(tmp_path, "wine", "smol-360", "likelihood", 0, 0.86)
    rows = load_rows(str(tmp_path), "exp2_odds")
    assert "auroc" in rows.columns and "auprc" in rows.columns
    assert "r_sensitivity_auroc" not in rows.columns  # nested dropped


def test_aggregate_mean_std_over_seeds(tmp_path):
    _cell(tmp_path, "wine", "smol-360", "likelihood", 0, 0.80)
    _cell(tmp_path, "wine", "smol-360", "likelihood", 1, 0.90)
    agg = aggregate(load_rows(str(tmp_path), "exp2_odds"))
    row = agg[(agg.dataset == "wine") & (agg["mode"] == "likelihood")].iloc[0]
    assert abs(row["auroc_mean"] - 0.85) < 1e-9
    assert row["n_seeds"] == 2


def test_build_writes_csv(tmp_path):
    _cell(tmp_path, "wine", "smol-360", "prompted", 0, 0.7)
    out = build(str(tmp_path), "exp2_odds")
    assert out.exists() and out.suffix == ".csv"
