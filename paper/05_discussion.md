# Discussion

## What the results say

**Scoring mode dominates scale.** The central finding across 360 ODDS cells is unambiguous: how you
score (likelihood vs prompted) matters far more than which model you use (SmolLM-360M vs
Qwen2.5-3B). Likelihood scoring ranks first on 23/30 datasets; prompted scoring ranks third or
fourth on 25/30. This replaces the intuition that larger, instruction-tuned models "ought to be
better" with a mechanistic account: prompted expected-value scoring collapses a fine-grained
per-token probability signal into a single prompted digit, discarding the token-level distributional
signal that likelihood scoring preserves.

**LLMs do not transfer to security data at operationally meaningful thresholds.** On credit-card
fraud and UNSW-NB15, classical detectors deliver recall@1%FPR of 0.59–0.68 (creditcard, ECOD/IForest)
while Qwen likelihood achieves only 0.14 and Qwen prompted only 0.003. AUROC numbers are closer —
0.95 for IForest vs 0.76 for Qwen likelihood on creditcard-random — but practitioners operating at
a fixed alert quota care about recall at the alert threshold, not area under the full curve.
The gap is large enough to be actionable: for security SOC use cases, classical detectors remain
the right choice over the tested LLMs.

**Serialization design choices are mostly free.** Domain-expert column ordering does not help (pima
tied at 0.449; UNSW arbitrary outperforms domain by 0.126 AUROC). Semantic column names do not help
(mean Δ = −0.007, n = 3 pairs). The implication is practical: practitioners can use the default
column order and anonymized column codes without sacrificing accuracy, removing two design choices
that would otherwise require domain expertise to optimise.

**The two-stage triage architecture does not solve the security transfer problem.** Negative results
should be reported and not buried. The IForest shortlist at k = 1% already captures the recoverable
anomalies; the LLM re-ranker does not re-order them usefully. At wider k (5–10%), the LLM's poor
recall actively hurts. This refutes the intuition that "cheap LLM re-ranking is always worth trying"
and provides an empirical bound: IForest's precision within its top-1% is high enough that the LLM
adds only noise.

## Limitations

**Replication gap on per-dataset AUROC (C3).** Nine of 30 per-dataset AUROCs fall outside the ±0.05
pre-registered band. We attribute this to SmolLM-360M's LoRA sensitivity at small dataset scale
(n < 200 training samples on 6 failing datasets) and to non-determinism in LoRA initialization.
The mean and rank-correlation criteria (C1, C2) pass; the per-dataset gap is a real limitation and
should inform future work on fine-tuning stability.

**Timing is partially approximated.** M1/M2 pod-level timing (222 s/1k rows for likelihood,
33 s/1k for prompted) is derived from RUNLOG pod uptime divided by cell count, not per-cell
wall-clock measurement. M4 cells have precise per-cell timing. The approximation is conservative
and directionally consistent.

**Security results rest on 2–3 datasets.** The Friedman test requires > 5 datasets for meaningful
power; we make no cross-dataset generalisation claim and phrase all security findings as per-dataset
descriptive evidence. Extending to a broader security benchmark (KDD Cup 99, CICIDS, NSL-KDD) is
the obvious next step.

**Checkpoint confound is bounded, not eliminated.** The dissolving arm shows the confound is small
(|ΔAuroc| = 0.005 < 0.02 threshold), but the likelihood-vs-prompted A/B still compares base+LoRA
vs. instruct (frozen). An exact same-weights comparison would require a base model that is also
instruction-tuned — a non-trivial requirement that future work should address.

**RQ3b, RQ5: n = 3 pairs per dataset.** Wilcoxon is underpowered (minimum achievable p = 0.25).
The ablations are exploratory and so labelled; they should not be treated as confirmatory evidence
for null hypotheses.

## Positioning

This work is an honest replication and extension, not a new detector. The value is in the
controlled A/B (mode held, scale varied; scale held, mode varied), in the operational metrics on
security data, and in the honest negative results on two-stage triage and semantic ablations.
Papers that report "LLMs are competitive" (AnoLLM) and "LLMs underperform classical methods"
(AD-LLM) are both correct — the answer depends on operating regime: AUROC on ODDS vs
recall@1%FPR on security data. Practitioners who read only AUROC tables will make wrong deployment
decisions.

## Future work

1. Scale the security evaluation to a broader benchmark (> 5 datasets for Friedman power).
2. Investigate LoRA fine-tuning stability on small tabular datasets — higher-variance seeds may
   benefit from ensemble or warm-start initialisation.
3. Test the two-stage design with a higher-recall shortlisting stage (e.g., an ensemble or
   density-based shortlist) — IForest near-ceiling is specific to the tested datasets.
4. Explore calibrated prompted scoring (temperature scaling, chain-of-thought) as an alternative
   to expected-value scoring; the current prompted baseline may understate instructed LLM capability.
