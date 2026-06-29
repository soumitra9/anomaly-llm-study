# M1 Reproduction Gate — PRE-REGISTERED acceptance spec

**Status: pre-registered. Committed BEFORE the gate results were inspected.** This file fixes the gate's
pass/fail criteria in advance so the verdict is a test, not a moving target. Changing these thresholds after
seeing results, or "adding data and re-judging until it passes," is **forbidden** (optional-stopping / p-hacking).

_Pre-registered 2026-06-29, before reading any `results/raw/exp1_repro/` AUROC from the full gate run
`anollm-gate-360-s*`. Reproduction target: AnoLLM (Tsai et al., ICLR 2025), SmolLM-360M on 30 ODDS datasets._

## What is being tested (RQ1)
Does our pipeline reproduce AnoLLM's published per-dataset AUROC for SmolLM-360M on the 30 ODDS datasets,
within tolerance? Our run: SmolLM-360M, likelihood scoring (mean NLL over r=10 permutations), 3 splits,
`max_steps=2000`, "standard" binning — the same protocol as AnoLLM except fewer splits/permutations (a
deliberate, pre-registered reduction for the free-Kaggle budget; it widens our variance, reflected in C1's slack).

## Acceptance criteria (judged by `anodet/eval/verdict.py`)
- **C1 — aggregate mean.** `|mean_AUROC(ours, 360M, 30 ODDS) − mean_AUROC(AnoLLM published)| ≤ 0.02`.
  (Strict reproduction is ~1 pt; the 2 pt band pre-allows our 3-split / r=10 variance. Not to be widened post hoc.)
- **C2 — rank correlation.** `Spearman ρ(ours per-dataset, published per-dataset) ≥ 0.80` across the 30 datasets.
- **C3 — per-dataset band.** `≥ 24/30` datasets fall within AnoLLM's published `±1 std` band.
  - If trustworthy per-dataset published numbers cannot be sourced (see `configs/anollm_reference.yaml`), C3 is
    reported as **informational only** and the gate rests on C1 (+ C2 if per-dataset point estimates exist).

**PASS ⇔ C1 ∧ C2 ∧ C3** (with C3's informational caveat above).

## Escalation — used AT MOST ONCE, pre-committed (not iterated)
IF the *only* failed criterion is **C3**, AND the misses are attributable to our reduced-split variance
(our per-dataset bootstrap CIs overlap the published band), THEN run the **pre-specified** expansion exactly
once — **5 splits, SmolLM-360M, same datasets** — and re-judge against the **same** C1/C2/C3 thresholds.
No further expansion. No threshold changes.

## Hard stop (anti-sunk-cost, anti-p-hack)
A failure on **C1 or C2 ⇒ STOP and debug the pipeline.** No amount of added data rescues a mean-level or
rank-correlation failure, and no downstream experiment (Exp 2–6) proceeds until the gate passes. The existence
of build-ahead code (Phase A) does not justify proceeding on a failed gate.
