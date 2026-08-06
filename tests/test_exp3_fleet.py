"""M3 exp3_fleet: explicit cell construction (likelihood=qwen+creditcard-only, classical=model-indep) + resume."""
import sys

import scripts.exp3_fleet as fleet


def test_build_cells_structure():
    cells = fleet.build_cells(list(fleet.TASKS), ["smol-360", "qwen2.5-3b"],
                              ["likelihood", "prompted", "classical"], [0, 1, 2])
    lik = [c for c in cells if c["mode"] == "likelihood"]
    prm = [c for c in cells if c["mode"] == "prompted"]
    cls = [c for c in cells if c["mode"].startswith("classical:")]
    # likelihood: qwen only, credit-card tasks only (2 splits) × 3 seeds = 6
    assert len(lik) == 6
    assert all(c["model"] == fleet.LIKELIHOOD_MODEL for c in lik)
    assert all(c["dataset"] == "creditcard" for c in lik)
    assert not any(c["task"] == "unsw" for c in lik)          # never mode-A on UNSW (default)
    # prompted: 2 models × 3 tasks × 3 seeds = 18
    assert len(prm) == 18
    # classical: model-independent, 4 detectors × 3 tasks × 3 seeds = 36
    assert len(cls) == 36
    assert all(c["model"] == "classical" for c in cls)
    assert {c["mode"] for c in cls} == {f"classical:{d}" for d in fleet.CLASSICAL}
    # split round-trips into the task id (keeps cell keys unique for creditcard temporal/random)
    assert {c["task"] for c in cells} == {"creditcard-temporal", "creditcard-random", "unsw"}


def test_build_cells_likelihood_tasks_unsw():
    cells = fleet.build_cells(["unsw"], ["qwen2.5-3b"], ["likelihood"], [0],
                              likelihood_tasks=["unsw"])
    assert len(cells) == 1
    assert cells[0]["task"] == "unsw" and cells[0]["mode"] == "likelihood"


def test_build_cells_modes_filter():
    # only classical requested -> no GPU cells
    cells = fleet.build_cells(["unsw"], ["smol-360"], ["classical"], [0])
    assert len(cells) == 4 and all(c["mode"].startswith("classical:") for c in cells)


def _fake_run_one(calls):
    def run_one(dataset, model, mode, *, data_dir, n_levels, batch_size, device, n_top, **kw):
        calls.append((model, mode, dataset, kw.get("split"), kw.get("seed"), kw.get("r"), batch_size))
        return ({"auprc_gain": 1.0, "recall_at_1pct_fpr": 0.5}, "complete",
                {"run_metadata": {"dataset_content_hash": "x"}, "n_rows_scored": 10, "n_rows_expected": 10})
    return run_one


def test_fleet_runs_and_resumes(monkeypatch, tmp_path):
    import anodet.eval.exp3_security as exp3
    calls = []
    monkeypatch.setattr(exp3, "run_one", _fake_run_one(calls))
    argv = ["exp3_fleet", "--task-datasets", "creditcard-temporal", "--models", "qwen2.5-3b",
            "--modes", "likelihood,prompted", "--seeds", "0", "--r", "5",
            "--results-root", str(tmp_path), "--device", "cpu"]
    monkeypatch.setattr(sys, "argv", argv)
    assert fleet.main() == 0
    # 1 likelihood (qwen, cc-temporal, seed0, r=5) + 1 prompted (qwen) = 2 cells; split threaded to loader
    assert ("qwen2.5-3b", "likelihood", "creditcard", "temporal", 0, 5, 16) in calls
    assert ("qwen2.5-3b", "prompted", "creditcard", "temporal", 0, None, 16) in calls
    assert len(calls) == 2
    # resume: re-run skips both
    calls.clear()
    assert fleet.main() == 0
    assert calls == []
