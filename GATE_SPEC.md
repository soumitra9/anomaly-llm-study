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
- **C3 — per-dataset band.** `≥ 24/30` datasets fall within AnoLLM's published band, where
  `band = max(±1 published std, ±0.02)`.
  - If trustworthy per-dataset published numbers cannot be sourced (see `configs/anollm_reference.yaml`), C3 is
    reported as **informational only** and the gate rests on C1 (+ C2 if per-dataset point estimates exist).

  **Pre-results refinement (2026-06-29, before any of our gate results existed).** While *sourcing the
  reference* (not our results), we found the paper reports per-dataset standard *error* (Table 11), and for 6
  "easy" datasets (http, musk, mulcross, shuttle, satellite, satimage-2) the 360M SE is 0.000 → a literal
  `±1 std` band has **zero width**, making C3 require a near-exact match there. We therefore add a `±0.02`
  absolute floor to the band. This is a legitimate refinement, not goalpost-moving: it is (a) decided before
  any of our results existed, (b) driven by a property of the *published* SEs, not our data, (c) documented
  here, and (d) the 0.02 floor equals C1's aggregate tolerance, so per-dataset and aggregate use the same
  reproduction tolerance. C1 and C2 are unchanged.

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

---

# M3.5 Confound-Bounding Gates — PRE-REGISTERED

**Status: pre-registered 2026-07-05, before M3.5 runs exist.** These criteria close the dissolving arm and
binned-creditcard arm as confound checks. They must not be changed after seeing results.

_Same anti-p-hacking discipline as C1/C2/C3: the tolerance is the number, not a number chosen to match
the result. Both thresholds are anchored to C1's 0.02 reproduction tolerance — internally consistent and
not post-hoc._

## DA1 — Dissolving arm (checkpoint-difference confound)

**What it tests:** Does LoRA fine-tuning the *instruct* checkpoint and scoring by likelihood yield
the same AUROC as fine-tuning the *base* checkpoint (Mode A as run in Exp 1/2)? If yes, the
two-variable A/B (base+LoRA vs frozen-instruct) is not confounded by the checkpoint choice.

**Protocol:** Qwen2.5-3B-Instruct + LoRA likelihood on the same ~8 ODDS datasets as used in M2,
1 seed, r=5. Compared to the corresponding Qwen2.5-3B base+LoRA cells already in `results/raw/exp2_odds/`.

**Pre-registered criterion:**

```
DA1 PASS: |mean AUROC(instruct+LoRA) − mean AUROC(base+LoRA)| < 0.02
          computed as seed-mean per dataset, then averaged across the ~8 ODDS test sets.

DA1 PASS → one sentence in §method/§RQ2:
           "Fine-tuning the instruct checkpoint instead of the base yields mean ΔAUROC = X
            (< 0.02 pre-registered tolerance); the checkpoint difference does not explain
            the likelihood-vs-prompted gap."

DA1 FAIL → report as a finding, not a failure:
           "Instruct fine-tuning yields meaningfully different likelihood scores (ΔAUROC = X).
            The A/B comparison controls model size but not checkpoint recipe; this is reported
            as a caveat in §method and the finding is described in §RQ2."
           M4 proceeds regardless — DA1 FAIL changes the claim, not the schedule.
```

**Scope-lock:** DA1 FAIL does not trigger a new compute run. The result is reported either way.

## BA1 — Binned-creditcard arm (serialization confound)

**What it tests:** Does switching creditcard-temporal from raw float serialization (Exp 3 protocol)
to standard binned serialization (ODDS protocol) materially change the AUROC of classical baselines?
If not, cross-domain comparisons are not primarily confounded by serialization.

**Protocol:** Re-run the 4 classical baselines on creditcard-temporal, binned serialization, 1 seed.
Compare to the raw-float classical cells already in `results/raw/exp3_security/`.

**Pre-registered criterion:**

```
BA1 PASS: |mean AUROC(binned classical) − mean AUROC(raw classical)| < 0.03
          averaged across the 4 classical detectors (iforest, pca, knn, ecod).

BA1 PASS → one sentence in §method:
           "Switching to ODDS-style binned serialization on credit-card data changes mean
            classical AUROC by X (< 0.03 pre-registered tolerance); serialization format
            does not explain the cross-domain gap."

BA1 FAIL → binned arm becomes a full condition in Exp 4 (serialization axis);
           all cross-domain narrative sentences are qualified with binning as a co-variable.
           M4 proceeds regardless — BA1 FAIL adds a condition, not a new milestone.
```

**Note:** BA1 uses a 0.03 tolerance (vs DA1's 0.02) because creditcard classical AUROC has higher
variance than ODDS mean AUROC (extreme imbalance, smaller effective positives). Pre-committed.

## Scope-lock for both arms

M3.5 is a confound-bounding exercise, not a new experiment. DA1 and BA1 each yield exactly one sentence
in the paper regardless of pass/fail. **Neither result spawns a new compute run before M4.** M4 starts
immediately after M3.5 results are evaluated against DA1/BA1.

---

# Revision Phase — PRE-REGISTERED (2026-08-06)

**Status: pre-registered before any revision GPU runs.** Addresses reviewer items 1 and 3 (see
`ROADMAP.md` §Revision Phase). Same anti-p-hacking discipline as C1/C2/C3: thresholds and protocols
are fixed here; results are reported honestly whichever way they go.

## RV1 — UNSW-NB15 likelihood arm (reviewer item 3)

**What it tests:** Does Qwen2.5-3B base+LoRA likelihood scoring on UNSW-NB15 match the protocol of
the existing M3 credit-card likelihood cells, filling the missing strongest-LLM-mode arm on the second
security dataset?

**Protocol (must match M3 credit-card likelihood exactly):**
- Model: `qwen2.5-3b`, mode A (base + LoRA likelihood)
- Dataset: `unsw` (UNSW-NB15 via `prepare_unsw`, `max_test_neg=40000` + all positives)
- Seeds: {0, 1, 2}
- **`r=5`** (verified: `results/logs/fleet/m3/m3_run.log` line 1 "full security run r=5"; NOT r=10)
- **`max_steps=1000`** (D0-validated Qwen steps; same as M3 security likelihood)
- Batch: default `exp3_fleet` (16); OOM-retry beneath
- Results: `results/raw/exp3_security/` with cell keys `qwen2.5-3b__likelihood__unsw__seed{N}`
- **Metadata requirement:** record `r_permutations=5` and `max_steps=1000` in run_metadata (M3
  creditcard cells have `r_permutations: null`; RV1 cells must be self-auditable)

**Pre-registered reporting:**
- Add UNSW likelihood row to security comparison table (AUROC, recall@1%FPR with importance weights)
- If likelihood underperforms prompted on UNSW, report honestly; do not restrict conclusion without data

**Measure-first:** run seed 0 only; extrapolate cost from wall-time before seeds 1–2. Cost decomposes
into fixed LoRA fine-tune (~max_steps=1000) + variable scoring pass (r=5 × test rows); do not
linearly multiply full wall-time across seeds without separating the fixed training component.

## RV2 — Few-shot prompted baseline (reviewer item 1)

**What it tests:** Does a stronger prompted baseline (normals-only few-shot exemplars) materially close
the likelihood-vs-prompted AUROC gap on ODDS, or does likelihood still dominate?

**Protocol:**
- Model: `qwen2.5-3b-instruct` (frozen), scorer: expected value over digit tokens (same as Mode B)
- **Few-shot:** `k=3` exemplar rows drawn from **normal training rows only** (`y_train==0`; leakage-free
  under AnoLLM split protocol where all anomalies are in test)
- Exemplar selection: deterministic given seed (`numpy.random.default_rng(seed)` sample without replacement)
- Datasets: 8 ODDS sets matching DA1 dissolving arm — `arrhythmia`, `breastw`, `cardio`, `ionosphere`,
  `shuttle`, `speech`, `vertebral`, `yeast`
- Seeds (ODDS split indices): {0, 1, 2}
- Mode tag: `prompted-fewshot` (distinct from M2 `prompted` zero-shot cells)
- Experiment root: `results/raw/exp2_fewshot/` (does not overwrite M2 JSONs)
- Compare to existing zero-shot `results/raw/exp2_odds/` qwen prompted cells on same (dataset, seed)

**Pre-registered reporting:**
- Report mean ΔAUROC(few-shot − zero-shot) across the 8 datasets × 3 seeds (descriptive)
- If few-shot closes a material fraction of the likelihood gap, narrow the headline claim to the
  expected-value zero-shot instantiation; report as finding, not failure
- If few-shot does not close the gap, state that likelihood dominates even with normals-only few-shot

**Scope-lock:** RV2 does not add chain-of-thought, temperature scaling, or calibration in v1.
