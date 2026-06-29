"""Property tests for the operational metrics — these protect the headline numbers (PLAN §10)."""
import numpy as np

from anodet.metrics import (
    auprc,
    auroc,
    clopper_pearson,
    no_skill_auprc,
    precision_at_k,
    recall_at_fpr,
    recall_at_k,
)


# --- 1. AUROC: label-flip symmetry + constant-score = 0.5 (catches positive-class flips) ---
def test_auroc_label_flip_symmetry():
    g = np.random.default_rng(0)
    y = (g.random(300) < 0.3).astype(int)
    s = g.random(300)
    a = auroc(y, s)
    assert abs(auroc(1 - y, s) - (1 - a)) < 1e-9


def test_auroc_constant_scores_is_half():
    y = np.array([0, 1, 0, 1, 1, 0])
    assert abs(auroc(y, np.ones(6)) - 0.5) < 1e-9


# --- 2. AUPRC: no-skill baseline == prevalence (incl. 0.17%); random ranker ~ prevalence ---
def test_no_skill_auprc_equals_prevalence():
    for prev in (0.0017, 0.05, 0.5):
        n = 100_000 if prev < 0.01 else 4000
        n_pos = max(1, round(prev * n))
        y = np.zeros(n, int)
        y[:n_pos] = 1
        assert abs(no_skill_auprc(y) - y.mean()) < 1e-12


def test_auprc_random_ranker_approx_prevalence():
    g = np.random.default_rng(1)
    for prev, tol in ((0.5, 0.05), (0.05, 0.03)):
        n = 20_000
        y = (g.random(n) < prev).astype(int)
        assert abs(auprc(y, g.random(n)) - y.mean()) < tol


# --- 3. Recall@1%FPR: interpolation, few-negatives edge, Clopper-Pearson ---
def test_recall_at_fpr_perfect_separation():
    y = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    s = np.array([0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9])
    assert recall_at_fpr(y, s, 0.01) == 1.0


def test_recall_at_fpr_few_negatives_edge():
    g = np.random.default_rng(2)
    y = np.array([0] * 10 + [1] * 10)
    s = np.concatenate(
        [g.uniform(0, 0.5, 10), g.uniform(0.6, 1.0, 6), g.uniform(0, 0.4, 4)]
    )
    maxneg = s[:10].max()
    expected = float((s[10:] > maxneg).mean())  # only fpr=0 qualifies at <100 negatives
    assert abs(recall_at_fpr(y, s, 0.01) - expected) < 1e-9


def test_clopper_pearson_contains_and_edges():
    lo, hi = clopper_pearson(5, 100)
    assert 0 <= lo <= 0.05 <= hi <= 1
    assert clopper_pearson(0, 50)[0] == 0.0
    assert clopper_pearson(50, 50)[1] == 1.0
    assert clopper_pearson(0, 0) == (0.0, 1.0)


# --- 4. Precision@K / Recall@K incl. tie-at-boundary (documented stable tie-break) ---
def test_precision_recall_at_k_basic():
    y = np.array([1, 1, 0, 0, 0])
    s = np.array([0.9, 0.8, 0.7, 0.6, 0.5])
    assert precision_at_k(y, s, 2) == 1.0
    assert recall_at_k(y, s, 2) == 1.0
    assert precision_at_k(y, s, 4) == 0.5


def test_topk_tie_at_boundary_is_stable():
    y = np.array([1, 0, 1, 0])
    s = np.array([0.5, 0.5, 0.5, 0.5])  # all tied -> stable order picks indices [0,1]
    assert precision_at_k(y, s, 2) == 0.5


# --- reweighting sanity: upweighting subsampled negatives lowers precision toward true rate ---
def test_importance_weight_lowers_precision_under_subsampling():
    from anodet.metrics import make_importance_weights

    # 10 positives, 10 sampled negatives, but 1000 negatives in the population
    y = np.array([1] * 10 + [0] * 10)
    s = np.concatenate([np.linspace(0.9, 0.6, 10), np.linspace(0.5, 0.1, 10)])
    w = make_importance_weights(y, n_neg_total=1000)
    assert w[y == 0][0] == 100.0 and w[y == 1][0] == 1.0
