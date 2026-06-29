"""Stats correctness (ranks, Friedman, Nemenyi CD, Holm-Wilcoxon, bootstrap) + figures render."""
import numpy as np
import pandas as pd
import pytest

from anodet.analysis import figures, stats
from anodet.metrics import auroc


def _scores():
    # method A dominates B on every dataset; C is middling. Higher = better.
    return pd.DataFrame({
        "A": [0.95, 0.92, 0.90, 0.93, 0.96, 0.91],
        "B": [0.70, 0.68, 0.72, 0.66, 0.71, 0.69],
        "C": [0.82, 0.80, 0.79, 0.84, 0.83, 0.81],
    }, index=[f"d{i}" for i in range(6)])


def test_average_ranks_best_is_rank1():
    r = stats.average_ranks(_scores())
    assert r.index[0] == "A" and abs(r["A"] - 1.0) < 1e-9  # A best on all -> mean rank 1
    assert r.index[-1] == "B"


def test_friedman_detects_difference():
    assert stats.friedman(_scores())["pvalue"] < 0.05


def test_nemenyi_cd_matches_formula():
    # k=4, n=10: 2.569 * sqrt(4*5/(6*10)) = 2.569 * sqrt(20/60)
    expected = 2.569 * np.sqrt(20 / 60)
    assert abs(stats.nemenyi_cd(4, 10) - expected) < 1e-6
    with pytest.raises(ValueError):
        stats.nemenyi_cd(99, 10)


def test_holm_wilcoxon_monotone_and_flags():
    df = stats.holm_wilcoxon(_scores(), baseline="B")
    assert set(df["method"]) == {"A", "C"}
    assert (df["p_holm"].values == np.maximum.accumulate(df["p_holm"].values)).all()  # monotone
    assert (df["median_delta"] > 0).all()  # both beat B


def test_bootstrap_delta_ci_excludes_zero_when_clearly_better():
    rng = np.random.default_rng(0)
    y = np.r_[np.zeros(180), np.ones(20)].astype(int)
    good = y + rng.normal(0, 0.3, len(y))   # strongly separates
    bad = rng.normal(0, 1, len(y))          # noise
    res = stats.bootstrap_delta_ci(y, good, bad, auroc, n_boot=300, seed=1)
    assert res["delta"] > 0 and res["excludes_zero"]


def test_figures_render(tmp_path):
    s = _scores()
    assert figures.cd_diagram(s, str(tmp_path / "cd.png")).exists()
    assert figures.per_dataset_bars(s.head(3), str(tmp_path / "bars.png")).exists()
    df = pd.DataFrame({"method": ["m1", "m2", "m3"], "auroc": [0.9, 0.8, 0.95], "cost": [10, 1, 50]})
    assert figures.pareto(df, str(tmp_path / "pareto.png")).exists()
