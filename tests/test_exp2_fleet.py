"""M2 fleet runner (scripts/exp2_fleet.py): per-dataset batch lookup, sharding, skip-complete resume."""
import sys

import scripts.exp2_fleet as fleet


def test_batch_tables_lookup():
    tables = fleet._load_batch_tables()
    # SmolLM from anollm_hparams.yaml (Table 7), Qwen from qwen_hparams.yaml (half, floor 2, cap 32)
    assert tables["smol-360"]["cardio"] == 32
    assert tables["qwen2.5-3b"]["cardio"] == 16
    assert tables["qwen2.5-3b"]["speech"] == 2   # widest set: smoke-confirmed batch 2
    assert tables["qwen2.5-3b"]["http"] == 32    # capped (smol 128 -> min(32, 64))
    # unknown (model,dataset) falls back to DEFAULT_BATCH (OOM-retry protects it anyway)
    assert fleet._batch_for(tables, "qwen2.5-3b", "nonesuch") == fleet.DEFAULT_BATCH
    assert fleet._batch_for(tables, "unknown-model", "cardio") == fleet.DEFAULT_BATCH


def _fake_run_one(calls):
    def run_one(ds, model, mode, *, split_idx, n_splits, max_steps, r, n_levels, batch_size, device):
        calls.append((model, mode, ds, split_idx, batch_size))
        metrics = {"auroc": 0.9, "auprc": 0.5, "auprc_gain": 0.1, "recall_at_1pct_fpr": 0.2}
        extra = {"run_metadata": {"checkpoint_kind": "base"},
                 "n_rows_scored": 10, "n_rows_expected": 10, "device_used": "cpu"}
        return metrics, "complete", extra
    return run_one


def test_fleet_shards_uses_per_dataset_batch_and_resumes(monkeypatch, tmp_path):
    import anodet.eval.exp2 as exp2
    calls = []
    monkeypatch.setattr(exp2, "run_one", _fake_run_one(calls))
    argv = ["exp2_fleet", "--datasets", "cardio,speech", "--models", "qwen2.5-3b",
            "--modes", "likelihood", "--seeds", "0", "--results-root", str(tmp_path), "--device", "cpu"]
    monkeypatch.setattr(sys, "argv", argv)

    assert fleet.main() == 0
    # 2 datasets x 1 model x 1 mode x 1 seed = 2 cells, each with its per-dataset Qwen batch
    assert ("qwen2.5-3b", "likelihood", "cardio", 0, 16) in calls
    assert ("qwen2.5-3b", "likelihood", "speech", 0, 2) in calls
    assert len(calls) == 2

    # RESUME: a second identical run skips both (their JSONs are status=='complete')
    calls.clear()
    assert fleet.main() == 0
    assert calls == []


def test_fleet_batch_override(monkeypatch, tmp_path):
    import anodet.eval.exp2 as exp2
    calls = []
    monkeypatch.setattr(exp2, "run_one", _fake_run_one(calls))
    argv = ["exp2_fleet", "--datasets", "cardio", "--models", "qwen2.5-3b", "--modes", "likelihood",
            "--seeds", "0", "--batch-size", "7", "--results-root", str(tmp_path), "--device", "cpu"]
    monkeypatch.setattr(sys, "argv", argv)
    assert fleet.main() == 0
    assert calls == [("qwen2.5-3b", "likelihood", "cardio", 0, 7)]  # override wins over the table


def test_fleet_max_cells_stops_cleanly(monkeypatch, tmp_path):
    import anodet.eval.exp2 as exp2
    calls = []
    monkeypatch.setattr(exp2, "run_one", _fake_run_one(calls))
    argv = ["exp2_fleet", "--datasets", "cardio,speech,wine", "--models", "qwen2.5-3b",
            "--modes", "likelihood", "--seeds", "0", "--max-cells", "1",
            "--results-root", str(tmp_path), "--device", "cpu"]
    monkeypatch.setattr(sys, "argv", argv)
    assert fleet.main() == 0
    assert len(calls) == 1  # stopped after one new cell
