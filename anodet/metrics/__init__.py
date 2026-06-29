"""Evaluation metrics — operational + imbalance-honest (PLAN §6).

AUROC (tie-aware), AUPRC vs no-skill prevalence, Precision@top-N, Recall@fixed-false-alarms,
Recall@1%FPR with Clopper-Pearson CIs, importance reweighting for subsampled negatives, and
bootstrap CIs. Pure numpy/scipy/sklearn — no GPU, fully unit-tested.
"""
from .metrics import (  # noqa: F401
    auprc,
    auprc_gain,
    auroc,
    bootstrap_ci,
    clopper_pearson,
    make_importance_weights,
    no_skill_auprc,
    precision_at_k,
    prevalence,
    recall_at_fixed_false_alarms,
    recall_at_fpr,
    recall_at_k,
)
