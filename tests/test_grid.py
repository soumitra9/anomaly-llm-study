"""Grid runner: expansion, resumption (skip complete cells), manifest reconciliation."""
from anodet.eval.grid import (
    assert_grid_complete,
    expand_grid,
    pending_cells,
    run_grid,
    write_manifest,
)

CFG = {
    "experiment": "t",
    "axes": {
        "models": ["m1"],
        "modes": ["prompted"],
        "datasets": ["d1", "d2"],
        "seeds": [0, 1],
    },
}


def _run_cell(cell):
    return {"auroc": 0.9}, "complete", {"run_metadata": {}, "n_rows_scored": 10, "n_rows_expected": 10}


def test_expand_grid_size():
    assert len(expand_grid(CFG)) == 4


def test_run_grid_resumes_and_manifest(tmp_path):
    n1 = run_grid(CFG, tmp_path, _run_cell)
    assert n1 == 4
    # everything complete now -> second run does nothing
    assert run_grid(CFG, tmp_path, _run_cell) == 0
    assert pending_cells(CFG, tmp_path) == []
    write_manifest(CFG, tmp_path)
    assert (tmp_path / "MANIFEST.jsonl").exists()
    assert_grid_complete(CFG, tmp_path)  # must not raise


def test_assert_grid_complete_raises_when_missing(tmp_path):
    import pytest

    with pytest.raises(RuntimeError):
        assert_grid_complete(CFG, tmp_path)  # nothing run yet
