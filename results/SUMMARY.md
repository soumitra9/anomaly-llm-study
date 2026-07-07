# Results SUMMARY — Anomaly-Detection LLM Study (collated)

Single source of truth for everything run so far. Regenerate/refresh at the end of each milestone.
Per-cell JSON under `results/raw/<exp>/` is the machine system-of-record; this is the human digest.
Last updated: 2026-07-07 · git HEAD (M4 complete).

## Project spend to date ≈ **$141.41** (RunPod A40 SECURE @ $0.44/hr)
| Milestone | Cost | Note |
|---|---|---|
| M1 gate | ~$21 | 90 cells + config tests |
| D0 calibration | ~$0.65 | 1 pod, chose Qwen max_steps=1000 |
| M2 Exp-2 | **$90.42** | real billing; ~35% over est (Qwen r=10 on 280k-row test sets) |
| **M3 Exp-3/3b** | **~$13.03** | pod `l2css8jckkkp0q` stopped 2026-07-05; 29.6 h × $0.44/hr; 66/66 cells |
| **M3.5 DA1** | **~$5.61** | pod `xbga2ae1dqfp12` stopped 2026-07-06; 8/8 cells; DA1 PASS |
| **M4 Exp-4/5/6** | **~$4.80** | pod `pyinsl4hrttusc`; 10.9h × $0.44/hr; 33/33 cells; DONE 2026-07-07 03:10Z |

---

## M1 — Reproduction gate (RQ1) · COMPLETE (90/90 cells)
SmolLM-360M, likelihood, 30 ODDS × 3 splits, r=10. Verdict vs pre-registered `GATE_SPEC.md`:
- **C1 mean PASS** — ours 0.8505 vs published 0.865 (Δ 0.0145 ≤ 0.02)
- **C2 rank PASS** — Spearman 0.8754 ≥ 0.80
- **C3 band 19/30** (need 24) — root-caused to a **code-vs-paper difference in the released fork** (NOT our
  error; controlled effective-batch test refuted the config hypothesis). Hard-stop is C1/C2 only → not triggered.
- **Verdict: credible PARTIAL reproduction. No re-gate (proven futile).**
- Artifacts: `results/raw/exp1_repro/*.json` (90), `results/tables/exp1_repro.csv`.

## M2 — Exp 2 same-model A/B: likelihood vs prompted, scale (RQ2, RQ3) · COMPLETE (360/360 cells)
[smol-360, Qwen2.5-3B] × [likelihood, prompted] × 30 ODDS × 3 seeds. SmolLM @2000 steps, Qwen @1000 (D0).
- Mean AUROC: smol-L **0.843**, qwen-L **0.859**, smol-P **0.610**, qwen-P **0.493**.
- **Friedman p=6e-12.** Avg ranks (lower=better): smol-L 1.62, qwen-L 1.65 (tied, within CD=0.856),
  smol-P 3.20, qwen-P 3.53.
- **RQ2 (scoring mode) — likelihood ≫ prompted, both models:** Holm-Wilcoxon smol Δ+0.276 (p=4.7e-8),
  qwen Δ+0.354 (p=2.6e-7); both reject H0.
- **RQ3 (scale) — NO significant gain:** Qwen-3B vs SmolLM-360M on likelihood Δ≈0.000, p_holm=0.77 (fail to reject).
- Artifacts: `results/raw/exp2_odds/*.json` (360), `results/tables/exp2_odds.csv`,
  `results/figures/exp2_cd_diagram.png`, backup `results/backups/exp2_odds_FINAL_360cells.tgz`.

## M3 — Security transfer (RQ4) + semantic names (RQ3b) · ✅ COMPLETE (66/66 cells)
Pod `anomaly-m3-cc` (A40, `l2css8jckkkp0q`): **60/60** `exp3_security` + **6/6** `exp3b_names`.
All cells `status=complete`, 0 failures. Pod stopped 2026-07-05 (~$13.03). Results rsync'd and verified
locally in `results/raw/exp3_security/` (60 JSONs) + `results/raw/exp3b_names/` (6 JSONs).
Logs: `results/logs/fleet/m3/m3_sec.log`.

Preliminary findings (analysis pending M4):
- Classical baselines (IForest, PCA, KNN, ECOD) on creditcard + UNSW: AUROCs in `exp3_security/`
- Semantic vs anon column names on pima (Qwen2.5-3B prompted, seeds 0–2): AUROCs in `exp3b_names/`

## Post-M3 findings (2026-07-05) — three confounds addressed before M4

Code review identified three items actioned before M4:

1. **`two_stage_scores` tie-block fixed** (was: all non-shortlist rows collapsed to one constant →
   coarse/pessimistic ROC at operating points below the shortlist boundary). Fixed: non-shortlist rows now
   preserve classical rank in a lower band. Two regression tests added. 76 tests green.

2. **"Same-model" claim reworded** to "same-family, same-size" everywhere (paper/01-03, PLAN.md).
   Mode A uses base+LoRA; mode B uses frozen instruct — two variables change. Checkpoint confound
   empirically bounded by a planned **dissolving arm** (instruct-likelihood, ~$3–5).

3. **Serialization confound documented**: ODDS uses standard binning; Exp 3 security data uses raw
   floats. RQ4's within-experiment comparisons remain internally valid. Cross-experiment narrative
   bounded by a planned **binned-creditcard arm** (folds into Exp 4, ~$2–3).

## M3.5 — Confound checks (pre-registered in GATE_SPEC.md) · 🔄 IN PROGRESS

**Drop-Time classical (T3) — DONE locally (CPU, $0):**
KNN AUROC on creditcard-temporal collapses from 0.932 → 0.178 when `Time` feature is included (temporal
distribution shift). IForest/PCA/ECOD robust (|ΔAUROC| ≤ 0.025). Corrected 24-cell results in
`results/raw/exp3_security_notime/`. All reported classical creditcard results use drop-Time protocol.

**BA1 binned-creditcard — DONE locally (CPU, $0): PASS**
Switching creditcard from raw float to ODDS-style standard binning changes mean classical AUROC by
**0.0012** across 4 detectors (threshold 0.03 per GATE_SPEC §BA1). Serialization does not explain the
cross-domain gap. Results in `results/raw/ba1_binned_notime/`. Sentence written in `paper/03_method.md`.

**DA1 dissolving arm — ✅ COMPLETE: PASS**
Qwen2.5-3B-Instruct + LoRA likelihood, 8 ODDS datasets, seed=0, r=5, max_steps=1000. Mean |ΔAUROC| =
**0.0054** vs base+LoRA (threshold 0.02, GATE_SPEC §DA1). Checkpoint choice does not explain the A/B gap.
Results in `results/raw/da1_dissolving/` (8 JSONs). Pod stopped (~$5.61).

## M3.5 verdict summary
All three checks PASS. M3.5 complete. Checkpoint choice (DA1) and serialization format (BA1) do not
explain the observed gaps. Time feature (T3) corrected for all creditcard reporting.

## M4 — Exp 4/5/6 (RQ5–7) · ✅ COMPLETE (33/33 cells)

Pod `pyinsl4hrttusc` (A40) finished 2026-07-07 03:10Z. ~10.9h uptime × $0.44/hr ≈ **$4.80**.
Results rsync'd locally. Tables: `exp4_serialization.csv`, `exp5_pareto.csv`, `exp6_triage.csv`.

### Exp 4 — serialization order (RQ5) · 24/24 cells
Grid: Qwen2.5-3B prompted × {arbitrary, domain, random:0, random:1} × {unsw, pima} × seeds {0,1,2}.

| Ordering | Mean AUROC |
|---|---|
| arbitrary | **0.564** |
| random:0 | 0.550 |
| random:1 | 0.543 |
| domain | 0.501 |

**Finding (RQ5):** Domain-expert column ordering does not help prompted scoring — arbitrary order leads.
Domain is worst on unsw (0.554 vs 0.680 arbitrary). The LLM does not leverage column-order signals.

### Exp 5 — Pareto practicality (RQ6) · local (no GPU)
Table: `results/tables/exp5_pareto.csv`. Figure: `results/figures/exp5_pareto.png`.

| Method | Mean AUROC | Wall-sec / 1k rows |
|---|---|---|
| qwen-3b / likelihood | 0.859 | 222 s |
| smol-360 / likelihood | 0.843 | 222 s |
| qwen-3b / triage (exp6) | 0.687 | 54 s |
| smol-360 / prompted | 0.610 | 33 s |
| qwen-3b / arbitrary (exp4) | 0.564 | 28 s |
| qwen-3b / prompted | 0.493 | 33 s |

**Finding (RQ6):** Likelihood dominates on accuracy but costs ~4-8x more than prompted/triage. Triage at 54s/1k rows is a useful middle ground. Prompted alone is cheapest but weakest.

### Exp 6 — two-stage triage (RQ7) · 9/9 cells
Grid: Qwen2.5-3B + IForest × {creditcard-random, creditcard-temporal, unsw} × seeds {0,1,2}. k at 1%, 5%, 10%.

| Dataset | IForest AUROC | LLM AUROC | k=1% uplift | k=10% uplift |
|---|---|---|---|---|
| creditcard-random | 0.950 | 0.694 | 0.00 | -0.489 |
| creditcard-temporal | 0.940 | 0.688 | 0.00 | -0.455 |
| unsw | 0.961 | 0.680 | 0.00 | -0.089 |

**Finding (RQ7, negative result):** IForest alone dominates on security data (AUROC 0.94-0.96). LLM re-ranking adds zero uplift at k=1% and is harmful at k=10%. Two-stage triage provides no benefit over classical-only on these datasets.

## M5 (opt) → M6 → paper
M5 = optional Qwen3-14B A100 burst (~$25–45, cost-gated). M6 = final analysis + paper write-up.
