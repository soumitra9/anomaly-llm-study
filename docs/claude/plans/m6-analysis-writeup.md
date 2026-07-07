# M6 Plan — Analysis, Statistics, Figures, and Paper Write-up

**Created:** 2026-07-07 (post-M4 completion)
**Prereqs:** M1+M2+M3+M3.5+M4 all complete. All raw JSONs local. All tables in `results/tables/`.

---

## Where we stand: data inventory

| Experiment | Cells | Table | Answers |
|---|---|---|---|
| exp1_repro | 90 | `exp1_repro.csv` | RQ1 |
| exp2_odds | 360 | `exp2_odds.csv` | RQ2, RQ3 |
| exp3_security | 60 | `exp3_security.csv` | RQ4 |
| exp3b_names | 6 | `exp3b_names.csv` | RQ3b |
| exp3_security_notime | 24 | `exp3_security_notime.csv` | RQ4 (corrected protocol) |
| ba1_binned_creditcard | 4 | `ba1_binned_creditcard.csv` | BA1 confound check (PASS) |
| da1_dissolving | 8 | `da1_dissolving.csv` | DA1 confound check (PASS) |
| exp4_serialization | 24 | `exp4_serialization.csv` | RQ5 |
| exp5_pareto | n/a | `exp5_pareto.csv` | RQ6 |
| exp6_triage | 9 | `exp6_triage.csv` | RQ7 |

---

## Current findings summary (all RQs)

### RQ1 — Reproduction (COMPLETE, analyzed in M1)
- C1 PASS: ours 0.8505 vs published 0.865 (Δ=0.0145 ≤ 0.02)
- C2 PASS: Spearman ρ=0.8754 ≥ 0.80
- C3: 19/30 → partial repro, root-caused to code-vs-paper difference in released fork

### RQ2 — Scoring mode (COMPLETE, analyzed in M2)
- Likelihood >> prompted for both models (Friedman p=6e-12)
- Holm-Wilcoxon: smol Δ+0.276 p=4.7e-8, qwen Δ+0.354 p=2.6e-7

### RQ3 — Scale (COMPLETE, analyzed in M2)
- No significant gain: qwen-3B vs smol-360M on likelihood, Δ≈0.000, p_holm=0.77

### RQ3b — Semantic column names (DATA COLLECTED, stats PENDING)
- Raw: anon AUROC 0.455, semantic AUROC 0.449 (ΔAUROC = −0.006, semantic slightly worse)
- **Needs:** bootstrap CI on ΔAUROC, n_boot=1000

### RQ4 — Security transfer (DATA COLLECTED, stats PENDING)
- Recall@1%FPR: classical 0.53-0.69 (creditcard), 0.16-0.19 (UNSW) vs LLM prompted ≈0.007-0.08
- Classical clearly dominates on operational metrics
- **Needs:** per-dataset bootstrap CI on best-LLM − best-classical on recall@1%FPR and AUPRC-gain

### RQ5 — Serialization order (DATA COLLECTED, stats PENDING)
- arbitrary 0.564 > random:0 0.550 > random:1 0.543 > domain 0.501 (mean AUROC)
- Surprising: domain-expert ordering is the worst, not the best
- **Needs:** Wilcoxon test (arbitrary vs mean-of-randoms as control, and domain vs random control), across 6 cells each

### RQ6 — Pareto practicality (COMPLETE, no stats needed — descriptive)
- Likelihood dominates accuracy; 4-8× slower than prompted
- Triage at 54s/1k rows is a useful middle ground (AUROC 0.687)

### RQ7 — Two-stage triage (DATA COLLECTED, stats PENDING)
- Negative result: IForest alone dominates (AUROC 0.94-0.96)
- LLM triage: zero uplift at k=1%, negative uplift at k=5-10%
- **Needs:** bootstrap CI on Recall@1%FPR(two-stage) − Recall@1%FPR(classical-alone) per dataset

---

## M6 Phase plan

### Phase 1 — Confirmatory statistics (script: `scripts/m6_stats.py`)

Write a single script that produces all test results to `results/tables/m6_stats.json`.

#### 1a. RQ3b bootstrap (pima semantic vs anon)
```python
# Load exp3b_names raw JSONs
# Bootstrap CI on ΔAUROC = semantic − anon across seeds
# Report: delta, [lo, hi], excludes_zero
```

#### 1b. RQ4 bootstrap per-dataset (security, best-LLM vs best-classical)
```python
# For each dataset in {creditcard-random, creditcard-temporal, unsw}:
#   best_llm = likelihood on creditcard, prompted on unsw (where likelihood not run)
#   best_classical = iforest (confirmed drop-Time; use exp3_security_notime)
#   metric: recall_at_1pct_fpr (primary), auprc_gain (secondary)
#   bootstrap_delta_ci(y_true, llm_scores, classical_scores, metric_fn, n_boot=2000)
# NOTE: n=2 datasets for creditcard (two splits), n=1 for UNSW → report as per-dataset evidence, NOT Friedman
```

#### 1c. RQ5 Wilcoxon (ordering sensitivity)
```python
# Load exp4_serialization raw JSONs per-seed
# Wilcoxon signed-rank: domain vs random_mean (average of random:0 + random:1), 6 paired obs (2 datasets × 3 seeds)
# Wilcoxon: arbitrary vs domain, arbitrary vs random_mean
# Holm-Bonferroni correct across the 2 tests
# Report p-values and effect sizes (Hodges-Lehmann)
# NOTE: small n=6 → report p-value but acknowledge limited power
```

#### 1d. RQ7 bootstrap (triage recall uplift)
```python
# For each dataset in {creditcard-random, creditcard-temporal, unsw}:
#   Load raw Exp6 JSONs — need per-instance scores (check if stored)
#   If per-instance NOT stored: bootstrap over seeds (n=3) → report seed mean ± std only
#   Metric: k1pct_recall_at_fpr(two-stage) − k1pct_recall_at_fpr(classical_alone)
```

**CONFIRMED (checked 2026-07-07):** Exp6 JSONs store only aggregate scalars per cell (no per-instance score arrays). `extra.full_triage_results` contains k-sweep aggregate dicts only. Therefore RQ7 statistical test is **seed-level only (n=3 per dataset)** — too few for a meaningful formal test. Report: mean ± std across 3 seeds per dataset. The null result is clear enough without a formal test (uplift = 0.00 on all seeds at k=1%).

---

### Phase 2 — Figures (script: `scripts/m6_figures.py` or extend `scripts/make_figures.py`)

#### Figure 1 — CD diagram (already have for M2; regenerate cleanly)
- Input: `exp2_odds.csv`, all 4 conditions (smol-L, qwen-L, smol-P, qwen-P)
- Output: `results/figures/exp2_cd_diagram.png` ← already exists

#### Figure 2 — Security operational metrics bar chart (RQ4)
- Grouped bar: metric = recall@1%FPR; x = {creditcard-random, creditcard-temporal, unsw}; groups = {best-LLM, iforest, pca, ecod}
- Use `exp3_security_notime.csv` (drop-Time corrected protocol)
- Output: `results/figures/exp3_security_bars.png`

#### Figure 3 — Ordering sensitivity (RQ5)
- Bar or scatter: x = {arbitrary, random:0, random:1, domain}; y = AUROC; separate series for pima/unsw
- 3-seed error bars
- Output: `results/figures/exp4_ordering.png`

#### Figure 4 — Pareto (already have)
- Output: `results/figures/exp5_pareto.png` ← already exists; may want to relabel axes

#### Figure 5 — Triage vs classical (RQ7) — optional
- Recall@k% curve for each dataset: classical-only vs two-stage
- Output: `results/figures/exp6_triage_recall.png`

---

### Phase 3 — Paper sections to write

#### §4 Results — one sub-section per RQ

**§4.1 RQ1 — Reproduction**
- C1/C2 PASS; C3 19/30 partial; root cause (released fork).

**§4.2 RQ2/RQ3 — Scoring mode and scale**
- Likelihood >> prompted (Friedman p=6e-12; Wilcoxon smol p=4.7e-8, qwen p=2.6e-7).
- No scale gain (p_holm=0.77). CD diagram as Figure 1.

**§4.3 RQ3b — Semantic column names**
- ΔAUROC = −0.006 (95% CI: [lo, hi]); null result, consistent with RQ5.

**§4.4 RQ4 — Security transfer**
- Classical dominates at operational metrics. Per-dataset bootstrap CIs.
- Scope caveat: n=2-3 datasets — per-dataset evidence only, no Friedman.

**§4.5 RQ5 — Serialization ordering**
- Domain ordering not helpful (arbitrary beats domain by 0.06 AUROC on UNSW).
- Wilcoxon p-values. Consistent with RQ3b: LLMs do not use column-order signals.

**§4.6 RQ6 — Pareto**
- Table/figure: likelihood best accuracy, 4-8× more expensive. Triage is middle ground.

**§4.7 RQ7 — Two-stage triage (negative result)**
- IForest alone: AUROC 0.94-0.96. Triage uplift at k=1%: 0.00 across all datasets.
- Bootstrap CI confirms no significant uplift. Honest negative finding.

#### §5 Discussion
- Why does prompted fail where likelihood succeeds? (no gradient signal in frozen inference)
- Why does triage fail? (IForest already near-perfect on tabular numeric security data; LLM prompted is noisy)
- Why does domain ordering not help? (attention-based models are partially order-invariant at this scale/context length)
- Limitations: n=2-3 security datasets, small number of model pairs, ICLR2025 fork discrepancy (RQ1 C3)

---

### Phase 4 — Paper housekeeping

- Update `paper/01_intro.md` abstract numbers with final values
- Verify all claims against `docs/claude/memory/anollm-verified-facts.md` and `related-work-verified.md`
- Add `TODO: verify-vs-PDF` flags for any unverified citations
- Ensure `paper/03_method.md` has the DA1 and BA1 sentences (already written in M3.5)

---

## Execution order and time estimates

| Step | Effort | Dependencies |
|---|---|---|
| Check exp6 JSON for per-instance scores | 5 min | none |
| Write `scripts/m6_stats.py` | 60-90 min | above |
| Generate `results/tables/m6_stats.json` | 5 min local | above |
| Write `scripts/m6_figures.py` | 45-60 min | tables exist |
| Generate all figures | 5 min local | above |
| Write §4 Results in `paper/04_results.md` | 90-120 min | stats + figures |
| Write §5 Discussion in `paper/05_discussion.md` | 60-90 min | §4 |
| Update §1 intro numbers | 20 min | §4 |
| Final GitHub push | 5 min | all above |

**Total estimated effort: ~5-8h (all local, no compute cost, no GPU needed)**

---

## Key constraints and guardrails

1. **Security stats use bootstrap per-dataset, NEVER Friedman/Nemenyi** (n=2-3 datasets = no power). Must state scope explicitly in paper.
2. **RQ7 is a negative result — report it honestly** as such. Do not re-gate or look for subgroup wins post-hoc.
3. **RQ3b is a null result** — ΔAUROC = −0.006 is within noise. Report the CI and let it be null.
4. **RQ5 Wilcoxon at n=6 is underpowered** — report p-value but explicitly call out limited power. The effect direction is clear (domain is worst) even if the test has low power.
5. **M5 (Qwen3-14B A100 burst)** remains optional and cost-gated (~$25-45). Can be deferred to revision if reviewers ask for a larger scale point. Do NOT block paper on M5.
6. All paper claims must be traceable to raw JSONs or the pre-registered `GATE_SPEC.md`.

---

## Files to create in M6

- `scripts/m6_stats.py` — all confirmatory stats, writes `results/tables/m6_stats.json`
- `scripts/m6_figures.py` — all paper figures not yet generated
- `paper/04_results.md` — §4 Results draft
- `paper/05_discussion.md` — §5 Discussion draft
- `results/tables/m6_stats.json` — machine-readable stat test outputs
- `results/figures/exp3_security_bars.png`
- `results/figures/exp4_ordering.png`
- `results/figures/exp6_triage_recall.png` (optional)
