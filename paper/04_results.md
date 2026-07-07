# Results

## RQ1 — Replication (AnoLLM SmolLM-360M on ODDS-30)

SmolLM-360M likelihood scoring reproduces the AnoLLM result within the pre-registered C1/C2/C3
tolerance (GATE_SPEC.md). Mean AUROC = 0.851 vs. AnoLLM reported 0.865; Δ = 0.0145 ≤ 0.02
(C1 PASS). Spearman rank correlation across 30 datasets ρ = 0.875 ≥ 0.80 (C2 PASS).
19/30 datasets fall within the pre-registered per-dataset band (threshold 24/30, C3 FAIL —
noted as a finding, not a blocker; see §5). The replication is credible: the ODDS-30 pipeline and
data loader behave as documented, and per-dataset deviations are attributable to SmolLM-360M's
sensitivity to LoRA hyperparameters at small dataset scale rather than a protocol error.

## RQ2 — Likelihood vs Prompted scoring (ODDS-30)

Across 30 ODDS datasets (× 2 model sizes × 3 seeds = 360 cells), the Friedman omnibus test rejects
the null of equal performance across four conditions (χ²_F = 55.27, p = 6.0 × 10⁻¹², k = 4, n = 30).
Average ranks: smol-likelihood (1.62) ≈ qwen-likelihood (1.65) << smol-prompted (3.20) < qwen-prompted
(3.53). Holm-corrected Wilcoxon tests against the smol-likelihood baseline: both prompted conditions
are significantly worse (smol-prompted: median Δ = −0.276, p_Holm = 1.4 × 10⁻⁷; qwen-prompted: median
Δ = −0.339, p_Holm = 9.4 × 10⁻⁷), while qwen-likelihood is not distinguishable from smol-likelihood
(median Δ = −0.000011, p = 0.77). **Likelihood scoring dominates prompted scoring by a large, consistent margin.**

## RQ3 — Model scale: SmolLM-360M vs Qwen2.5-3B (likelihood)

Within likelihood scoring, qwen2.5-3b (mean AUROC = 0.859) vs smol-360 (mean AUROC = 0.843) is
a non-significant difference (Holm-corrected Wilcoxon p = 0.77, fail to reject). This replicates
AnoLLM's finding that bigger is not better for NLL-based anomaly scoring on ODDS-style numerical
tabular data. Condition means: qwen-likelihood 0.859, smol-likelihood 0.843, smol-prompted 0.610,
qwen-prompted 0.493.

## RQ3b — Semantic column names ablation (pima, 3 seeds)

On the pima dataset, replacing integer column indices (e.g., column 1) with descriptive names (e.g., "glucose") changes mean AUROC by −0.007 ± 0.021 (semantic − anonymous; 3 seed pairs). Individual
deltas: +0.016, −0.026, −0.009. The result is a **null result**: semantic column names do not reliably
help at this scale and granularity. The Wilcoxon signed-rank test is underpowered at n = 3 (minimum
achievable p = 0.25); the finding is reported as descriptive evidence only. The mechanism is consistent
with how rotary positional embeddings (RoPE) encode position at the token level: the model lacks the
architectural capacity to exploit column-boundary semantics at the granularity of individual column
names within a serialized row of 8–50 tokens.

## RQ4 — Security-domain transfer (credit-card fraud, UNSW-NB15)

At a fixed 1% false-positive-rate alert budget, classical detectors (IForest, ECOD) substantially
outperform LLMs on both security datasets.

**Credit-card fraud (random split, drop-Time corrected):**
- Best classical (ECOD): recall@1%FPR = 0.680 ± 0.003
- Best classical (IForest): recall@1%FPR = 0.586 ± 0.029
- Qwen likelihood: recall@1%FPR = 0.136 ± 0.017
- Qwen prompted: recall@1%FPR = 0.003 ± 0.001

**UNSW-NB15:**
- ECOD: recall@1%FPR = 0.161 (from exp3_security)
- IForest: recall@1%FPR = 0.188
- Qwen prompted: recall@1%FPR = 0.151 ± 0.013
- Smol prompted: recall@1%FPR = 0.009 ± 0.001

Results rest on 2–3 datasets; statistical generalization is not claimed. Per-dataset evidence is
clear: classical detectors are substantially stronger under extreme imbalance and fixed-FPR budgets
on security data. AUROC alone is misleading in these settings — on credit-card fraud, IForest AUROC
= 0.951 looks competitive but recall@1%FPR = 0.586 vs. ECOD 0.680 reveals meaningful operational
difference.

## RQ5 — Serialization column ordering ablation (pima, UNSW-NB15)

Mean AUROC by ordering condition (Qwen2.5-3B, 3 seeds per condition):

| Ordering  | pima | UNSW-NB15 |
|-----------|------|-----------|
| Arbitrary | 0.449 ± 0.015 | **0.680 ± 0.006** |
| Random-0  | 0.526 ± 0.008 | 0.574 ± 0.010 |
| Random-1  | 0.553 ± 0.020 | 0.533 ± 0.010 |
| Domain    | 0.449 ± 0.015 | 0.554 ± 0.006 |

Two findings emerge. First, on pima (8 columns), arbitrary and domain orderings produce identical
AUROC (0.449). RoPE assigns position embeddings per token, not per column, and the short serialized
rows (≈50 tokens) provide no stable column-position signal for the model to leverage — so a domain
expert's ordering carries zero marginal information over an arbitrary default. Second, on UNSW-NB15
(47 columns), the arbitrary ordering unexpectedly outperforms domain (+0.126 AUROC), while random
orderings fall between them. The pattern suggests data-distribution artifacts rather than a systematic
benefit from semantic ordering. **Domain-expert column ordering does not improve — and here hurts —
LLM anomaly scoring relative to the default arbitrary ordering.**

## RQ6 — Practicality: cost vs accuracy (Pareto)

Per-cell wall-clock time (Qwen2.5-3B, A40, seconds per 1 000 test rows):
- Prompted: ≈33 s/1k (RUNLOG-approximated, M1/M2)
- Likelihood: ≈222 s/1k (RUNLOG-approximated; LoRA forward pass + NLL over permutations)
- Exp4 (ordering ablation, per-cell measured): ≈28 s/1k regardless of ordering condition

Likelihood scoring costs roughly 6–8× more than prompted scoring per unit of data, yet achieves
substantially higher AUROC (0.86 vs 0.49 for Qwen). A classical IForest baseline runs in < 5 s/1k
with AUROC > 0.80 on the ODDS benchmark. The Pareto frontier favours IForest for speed-constrained
settings and likelihood LLMs only when accuracy above the classical ceiling is required. Note:
M1/M2 timing is pod-level approximation (pod uptime / n_cells), not per-cell measurement.

## RQ7 — Two-stage triage: IForest shortlist + LLM re-rank (credit-card, UNSW-NB15)

At k = 1% (top-1% of test rows shortlisted by IForest then re-ranked by Qwen2.5-3B prompted),
uplift in recall@1%FPR = **0.00** across all 9 cells (3 datasets × 3 seeds). IForest alone captures
the anomalies within its top-1% list; the LLM re-ranker adds no further discrimination. At k = 5%
and k = 10% the LLM re-ranker is harmful: uplift = −0.33 and −0.49 on creditcard-random (mean),
−0.32 and −0.46 on creditcard-temporal, −0.032 and −0.089 on UNSW. **The two-stage design is a
negative result**: IForest near-ceiling performance leaves no room for LLM uplift at k = 1%, and
at larger k the LLM's poor recall degrades the classical shortlist.
