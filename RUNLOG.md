# RUNLOG — compute-session ledger

Append-only. **One entry per compute session** (Kaggle / RunPod / local-GPU). This is the human-readable
companion to the machine system-of-record (per-cell JSON under `results/raw/<exp>/`, each with full
`RunMetadata`). Newest entries on top. Keep it factual: what ran, where, what landed, what failed + why, cost.

Conventions: record git SHA, GPU, exact command, cells
new/skipped/failed, cost, and where results/logs were saved. Always capture the run's stdout log to
`results/logs/`.

---

## 2026-08-06/07 · Revision Phase · RV1 + RV2 · ✅ COMPLETE
- **Pod:** `anomaly-revision-rv1` (`1y91hqyjou9pkx`), CA-MTL-1, A40 SECURE **$0.44/hr**.
- **Launched:** 2026-08-06 17:36Z. **Stopped:** 2026-08-07 (~21:22Z pull). Total uptime ≈ **27.8 h** (includes idle gaps between phases).
- **SSH:** `69.30.85.67:22132`, key `~/.ssh/id_ed25519_runpod_anomaly`. Repo rsync'd (private GitHub clone failed on pod).
- **§RV1 — UNSW likelihood:** 3/3 cells (`qwen2.5-3b__likelihood__unsw__seed{0,1,2}`). r=5, max_steps=1000. ~5 h/cell wall. AUPRC gain **7.17 / 7.67 / 8.22**; recall@1%FPR **0.273 / 0.309 / 0.324**. Beats M3 prompted UNSW seed0 (gain 3.99, recall@1%FPR 0.148).
- **§RV2 — Few-shot prompted:** 24/24 cells (`exp2_fewshot`, k=3 normals-only, 8 ODDS × 3 seeds). Fleet wall ≈ **2.9 h** (10400 s). 0 failed. Mean AUROC: zero-shot **0.468** → few-shot **0.759** (Δ +0.290); likelihood **0.773** on same 8 sets (~95% gap closure). Regressions: speech, vertebral.
- **Results:** rsync'd + verified locally. Backup: `results/backups/revision_20260807T212210Z.tgz`. Logs: `results/logs/fleet/revision/`.
- **Teardown:** `stop-pod` → status **EXITED** (disk retained on RunPod volume).
- **Cost:** 27.8 h × $0.44/hr ≈ **$12.21**. Project total ≈ **$153.62** (prior $141.41 + revision).
- **Incidents:** (1) Two failed pods (no PUBLIC_KEY → no SSH). (2) ~5.5 h idle after RV1 before RV2 manually started. (3) LaunchAgent blocked (`~/Library/LaunchAgents` root-owned) — manual pull used.

---

## 2026-08-07 · Phase 4 analysis · Revision RV1/RV2 · ✅ COMPLETE
- **Scope:** Deterministic analysis only (no GPU). Protocol comparability verified (breastw seed0: same split/serialization; only `n_shots=3` differs).
- **Scripts:** `PYTHONPATH=. uv run python scripts/make_tables.py exp3_security exp2_fewshot`; `scripts/m6_stats.py` (additive §RV1 + §RV2); `scripts/make_figures.py`.
- **Outputs:** `results/tables/exp3_security.csv` (3 UNSW likelihood rows), `results/tables/exp2_fewshot.csv`, `results/tables/m6_stats.json` (`rv1_unsw_likelihood`, `rv2_fewshot`), `results/figures/rv2_fewshot_vs_zeroshot.png`, `results/figures/rv1_unsw_likelihood.png`.
- **Key numbers (match raw JSONs):** RV1 likelihood mean gain **7.686**, recall@1%FPR **0.302** vs prompted seed0 gain **3.989**. RV2 mean AUROC zero-shot **0.468** → few-shot **0.759** (Δ **+0.290**); likelihood **0.773** (~**95%** gap closure). Regressions: speech, vertebral.
- **Tests:** `tests/test_revision_stats.py` added; **97 pytest green** locally.
- **Cost:** $0 (local CPU). Project total remains ≈ **$153.62**.

---

## 2026-08-07 · Phase 4b · RV2 significance + protocol · ✅ COMPLETE
- **Scope:** Additive analysis only (no GPU). Wilcoxon on likelihood vs few-shot AUROC gap; protocol comparability artifact; regression pattern on speech/vertebral.
- **Scripts:** `scripts/m6_stats.py` — `section_rv2_protocol`, extended `section_rv2` (`wilcoxon_primary`, `wilcoxon_sensitivity_cell_level`, `regression_analysis`).
- **Key results:** Surviving gap (likelihood − few-shot) mean **0.014** AUROC. **Primary Wilcoxon (n=8 dataset means): p=0.641, reject=False** → statistically indistinguishable (underpowered at n=8; min p≈0.008). Cell-level sensitivity (n=24, non-independent): p=0.317. Protocol check **PASS** 8/8 (seed0; identical split/serialization hashes). Regressions: speech (~400 features), vertebral (smallest n≈240, 6 features).
- **Outputs:** `results/tables/m6_stats.json` keys `rv2_protocol_comparability`, extended `rv2_fewshot`.
- **Tests:** 98 pytest green (`tests/test_revision_stats.py` extended).
- **Cost:** $0 (local CPU).

---

## 2026-07-07 · M6 Analysis + paper §4/§5 · ✅ COMPLETE
- **Scripts:** `scripts/m6_stats.py` (Friedman/Wilcoxon M2 verification + descriptive summaries for
  RQ3b, RQ4, RQ5, RQ7; CSV cross-check PASS) and `scripts/m6_figures.py` (two paper figures).
- **Outputs:** `results/tables/m6_stats.json`, `results/figures/exp3_security_bars.png` (RQ4),
  `results/figures/exp4_ordering.png` (RQ5).
- **Paper:** `paper/04_results.md` (§4, all RQs with verified numbers), `paper/05_discussion.md` (§5,
  limitations, positioning, future work). Fixed stale "constructive two-stage" claim in `paper/01_intro.md`
  and `paper/02_related_work.md` to honest negative-result framing.
- **Key confirmed numbers:** Friedman p=6.0×10⁻¹², smol-likelihood avg rank 1.62 vs qwen-prompted 3.53.
  RQ7 uplift at k=1% = 0.00 across all 9 cells. RQ5 UNSW: arbitrary 0.680 > domain 0.554 AUROC.
- **Cost:** $0 (local CPU only). Project total remains ≈ **$141.41**.
- **Commit:** `c88e861`.

---

## 2026-07-06/07 · M4 Exp 4 + Exp 6 · ✅ COMPLETE (33/33)
- **Pod:** `anomaly-m4-exp4exp6` (`pyinsl4hrttusc`), CA-MTL-1, $0.44/hr SECURE.
- **Launched:** 2026-07-06 16:17Z. **Finished:** 2026-07-07 03:10Z. Uptime: ~10.9h.
- **Git:** `289cb91` (M4 Phase 1 code); hot-patched to `c3ee07b` (exp6 bug fix).
- **Exp 4 — serialization order (RQ5):** 24/24 complete. Grid: qwen2.5-3b × {arbitrary, domain, random:0, random:1} × {unsw, pima} × seeds {0,1,2}. Key finding: arbitrary ordering beats domain (0.564 vs 0.501 AUROC) — domain-expert ordering does not help prompted scoring.
- **Exp 6 — two-stage triage (RQ7):** 9/9 complete (after retry at 23:31Z). Grid: qwen2.5-3b + iforest × {creditcard-random, creditcard-temporal, unsw} × seeds {0,1,2}. Negative result: IForest alone dominates (AUROC 0.94-0.96); LLM re-ranking adds 0 uplift at k=1%, negative at k=10%.
- **Incident:** Exp 6 crashed on first cell (double-kwarg `classical_detector`); fixed in `c3ee07b`; zero data loss; restarted cleanly.
- **Results:** rsync'd + verified locally: `results/raw/exp4_serialization/` (24 JSONs), `results/raw/exp6_triage/` (9 JSONs). Log: `results/logs/fleet/m4/m4_run.log`.
- **Exp 5 (Pareto):** run locally (no GPU). `results/tables/exp5_pareto.csv`, `results/figures/exp5_pareto.png`.
- **Cost:** 10.9h × $0.44/hr ≈ **$4.80**. Project total ≈ **$141.41**.

---

## 2026-07-06 · M3.5 DA1 dissolving arm · ✅ COMPLETE (8/8)
- **Pod:** `anomaly-m35-da1` (`xbga2ae1dqfp12`), CA-MTL-1, $0.44/hr SECURE.
- **Launched:** 2026-07-06 02:39Z. **Stopped:** 2026-07-06 ~15:25Z. Uptime: ~12.75 h.
- **Grid:** 8 cells — Qwen2.5-3B-Instruct + LoRA likelihood on 8 ODDS datasets (seed=0, r=5, max_steps=1000).
  Datasets: arrhythmia, breastw, cardio, ionosphere, shuttle, speech, vertebral, yeast.
- **DA1 verdict: PASS** — mean |ΔAUROC(instruct+LoRA − base+LoRA)| = **0.0054** (threshold 0.02; GATE_SPEC §DA1).
  Per-dataset deltas: arrhythmia +0.0053, breastw +0.0004, cardio −0.0166, ionosphere −0.0043,
  shuttle −0.0001, speech +0.0008, vertebral −0.0092, yeast +0.0063.
- **Results:** `results/raw/da1_dissolving/` (8 JSONs) rsync'd and verified.
- **Log:** `results/logs/m35_da1.log`.
- **Cost:** ~12.75 h × $0.44/hr ≈ **$5.61**. Project total ≈ **$136.61**.
- **M3.5 status:** All 3 checks complete — T3 DONE (local CPU), BA1 PASS (|Δ|=0.0012), DA1 PASS (|Δ|=0.0054).

---

## 2026-07-04 → 2026-07-05 · M3 Exp-3/3b · ✅ COMPLETE (66/66)
- **Pod:** `anomaly-m3-cc` (`l2css8jckkkp0q`), CA-MTL-1, $0.44/hr SECURE.
- **Launched:** 2026-07-04 19:59Z. **Stopped:** 2026-07-05 ~25:30Z. Uptime: 106562 s ≈ 29.6 h.
- **Grid:** 60 `exp3_security` (6 Qwen-likelihood + 18 prompted + 36 classical) + 6 `exp3b_names`. **All complete, 0 failures.**
- **Rsync:** `results/raw/exp3_security/` (60 JSONs) + `results/raw/exp3b_names/` (6 JSONs) verified local.
  All 66 cells status=complete confirmed by local scan.
- **Logs:** `results/logs/fleet/m3/m3_sec.log` (4.4 MB), `m3_run.log` local.
- **Cost:** 29.6 h × $0.44/hr ≈ **$13.03**. Project total ≈ **$131**.
- **Pod action:** stopped via MCP (`stop-pod`). Disk persists; delete after M3.5 if not needed.

---

## 2026-07-04 · M2 Exp-2 · ✅ COMPLETE (360/360) + analyzed
- **Result:** 360/360 cells, 0 failures. All pods torn down (list-pods empty); results triple-saved
  (`results/raw/exp2_odds/` + `results/backups/exp2_odds_FINAL_360cells.tgz` + all 6 pods' logs local).
- **Cost (real RunPod billing): $90.42** (07-01→07-04) — ~35% over the ~$60-70 estimate. Driver: Qwen2.5-3B
  likelihood r=10 scoring on huge test sets (http/covertype/mulcross ~3-7h/cell; p6 ran ~73h). `results/exp2_cost.json`.
- **Analysis (`aggregate`→`stats`→`figures`):** table `results/tables/exp2_odds.csv`, CD diagram
  `results/figures/exp2_cd_diagram.png`.
  - Friedman p=6e-12. Avg ranks: smol-L 1.62, qwen-L 1.65 (tied, within CD=0.856), smol-P 3.20, qwen-P 3.53.
  - **RQ2 (mode):** likelihood ≫ prompted, BOTH models (smol Δ+0.276 p_holm 4.7e-8; qwen Δ+0.354 p_holm 2.6e-7; both reject H0).
  - **RQ3 (scale):** Qwen-3B vs SmolLM-360M likelihood Δ≈0.000, p_holm 0.77, NOT significant — 8× scale gives no likelihood gain.
- **Ops incident:** teardown auto-gate was a detached nohup (harness-untracked → never notified me) AND timed out at 33h < p6's ~73h → p6 idled until caught manually. Fix for M3: completion-triggered teardown via a **cron guardian** (re-invokes me → MCP delete; proven to fire), scope-locked to budget up front (never budget-kill mid-run).

---

## 2026-07-01 · M2 Exp-2 FLEET · 6× RunPod A40 · 🟢 RUNNING (launched ~17:20Z)
- **Fleet:** 6× A40 SECURE ($2.64/hr total), CA-MTL-1. Base 9207575 + scp'd overlay (exp2_fleet.py,
  qwen_hparams.yaml, prompted.py). Map/IDs/shards + recovery playbook in `FLEET.md`.
- **Grid:** 360 cells = [smol-360, qwen2.5-3b] × [likelihood, prompted] × 30 ODDS × 3 seeds. Sharded 5
  datasets/pod (disjoint). **Config: SmolLM @2000 steps, Qwen @1000 steps** (D0 finding: 2000 over-trains
  Qwen — cardio AUROC 0.831@2000 vs 0.841@1000, and 3× cheaper). r=10, both modes.
- **Staging:** GOLDEN data bundle `/tmp/data_golden.tgz` (all 30 pre-built + specials, 48M) — deterministic,
  no adbench race. Pilot (p1) caught the failure mode first: wine/breastw adbench npz fail `allow_pickle=False`
  on a fresh pod → golden bundle fixes it (30/30 load verified on every pod's bootstrap).
- **Checkpointing/recovery:** local puller (`fleet_pull.sh`, 5-min, 3 retries) rsyncs every pod→local — local
  is the durable record; a pod/balance loss loses nothing (re-provision → rsync local UP → `is_complete` skips
  done). Watcher (`fleet_watch.sh`) emits SHARD_DONE/FAILS/UNREACHABLE/STALL(45min)/ALL_DONE.
- **Incident — p3 heart:** heart (267×44) at batch 32 ground ~36GB/~40+min/cell and stalled p3. Diagnosed NOT a
  bad pod (p2 runs fine at 37GB); fix = p3 runs its 4 other datasets normal, then **heart at `--batch-size 4`**.
  Recovered with zero lost cells (checkpoint skip). Documented in FLEET.md.
- **Progress at 19:26Z:** ~40/360 cells, **0 failures**, all 6 pods producing; AUROCs sane (breastw 0.990,
  pendigits 0.952, wine 0.950, wbc 0.928). Still in SmolLM phase; Qwen (bottleneck) ahead. **ETA ~15-18h.**
- **Cost so far:** ~$0.65 (D0) + fleet accruing (~$2.64/hr); projected M2 total ~$35-45.

---

## 2026-07-01 · M2 de-risk (Layer 0) · local CPU + smoke pods · ✅ code gate green (no fleet yet)
- **Host:** local Mac (CPU) for all code/analysis validation; 2 RunPod A40 smoke pods earlier (torn down).
- **Base SHA:** 9207575 (changes below are working-tree, uncommitted pending user approval to commit).
- **Purpose:** de-risk the M2 fleet BEFORE spending — the plan-approved gate. Found + fixed 3 gaps that
  would have caused fleet failure:
  - **G1 — no fleet runner.** Built `scripts/exp2_fleet.py`: per-pod dataset **sharding**, per-(model,dataset)
    **batch lookup**, skip-complete **resume**, time/cell **budgets**. Mirrors `kaggle_gate.py`.
  - **G2 — `run_prompted` could hard-fail on OOM.** Added deterministic **OOM-retry** (halve, floor 1) — the
    widest Qwen prompted sets now self-shrink; final batch recorded. (`run_likelihood` already had this.)
  - **G3 — no Qwen batch table.** Added `configs/qwen_hparams.yaml` (Qwen2.5-3B = min(32, max(2, smol//2)),
    anchored to the 2026-07-01 smoke: cardio 16 ✓, speech 2 ✓). OOM-retry is the safety net beneath it.
- **Validation (all green):**
  - `pytest`: **70 passed** (was 63; +7: fleet shard/skip/batch/override, prompted OOM-retry ×2, batch-table).
  - Real un-mocked A/B path on CPU (smol-135M, 2 steps): likelihood (LoRA) + prompted both wrote valid cell
    JSONs (correct `lora`/`precision`/`decode_config`); **resume verified** (re-run skipped complete cells).
  - Analysis half on a complete 3-dataset × 2-mode grid: `aggregate`→CSV, `stats` (avg-ranks + Holm-Wilcoxon),
    `figures.cd_diagram`→PNG all ran. (AUROCs meaningless at 2 steps — plumbing only, discarded.)
- **Smoke-pod findings (2 A40, torn down):** Qwen2.5-3B is the M2 cost driver — cardio (b16) ran 37+ min
  without completing; speech (b2) trained 3 min then scored ~17 min+. ~8× SmolLM cost, consistent with a 3B vs
  360M model. No clean per-cell number captured → **D0** (one clean cardio timing) is the last de-risk step.
- **Remaining before fleet:** D0 (1 pod, ~$0.50, ~1h) to firm the per-cell cost + confirm the 37-min run is
  expected cost not a bug. Then Layer 1 (full 360-cell fleet, ~$40–70).
- **Cost:** $0 tonight (local); smoke pods billed earlier + torn down (list-pods empty, confirmed).

---

## 2026-07-01 · M2 de-risk D0 · RunPod A40 (`jb2r5b7fk4dntc`, CA-MTL-1) · ✅ clean timing + step lever found
- **Purpose:** one clean Qwen2.5-3B likelihood cell to firm per-cell cost + confirm the smoke's 37-min cardio
  was expected 3B cost, not a bug. Driven via `scripts/exp2_fleet.py` (also validates the fleet runner + Qwen
  batch table on GPU). Data: cardio `6_cardio.npz` scp-staged; 3 uncommitted files scp'd onto a fresh clone.
- **cardio Qwen2.5-3B likelihood, batch 16, r=10:**
  - **@2000 steps:** train 3028.8s (50.5 min, 0.66 steps/s, **epoch 38.5**, loss 0.334) + score ~8 min =
    **58.4 min/cell**; **AUROC 0.831**, AUPRC 0.655. EXIT 0. → not a bug, just 2000 steps × a 3B model.
  - **@500 steps (calibration, warm pod):** train 757.6s (12.6 min, epoch 9.6, loss 0.414) + score ~8 min =
    **20.2 min/cell**; **AUROC 0.841** (≥ the 2000-step 0.831 → 2000 was over-fitting cardio).
- **Finding (fleet-shaping):** per-step time is ~1.5s at batch 16 regardless of dataset; 2000 steps = 38 epochs
  on cardio = gross over-training. **500 steps is 3× faster and ≥ as accurate on cardio.** Caveat: validated on
  ONE small set — large ODDS sets see fewer epochs at fixed steps, so a uniform cut risks under-training them.
  → **recommend max_steps=1000 for Qwen** (balanced: ~2× cheaper than 2000, safe margin over cardio's 500).
- **Teardown:** delete-pod immediately after cal500; `list-pods` empty (confirmed).
- **Cost:** ~$0.65 (≈1.5 pod-h @ $0.44/h A40 secure).

---

## 2026-06-30 · M1 gate · Kaggle session 1 (`anollm-gate-360-s1`) · ❌ infra-fail (10/90)
- **Host/GPU:** Kaggle, Tesla P100-PCIE-16GB. **Precision:** bf16 (emulated on Pascal → slow).
- **Cmd:** `kaggle_gate --datasets <30 ODDS> --models smol-360 --splits 3 --r 10 --time-budget-secs 36000 --device cuda`
- **Result:** 10 new, 0 skipped, **3 failed**; budget-stop at 36,287s (~10.1h wall).
  - Done (AUROC vs published 360M): breastw 0.991/0.995/0.997 (pub 0.993 ✓), wine 0.932/0.887/0.967 (pub 0.851),
    ecoli 0.863/0.858/0.860 (pub 0.804), lymphography 1.000 (pub 0.993 ✓).
  - **Failed:** cardio split0/1/2 — `CUDA OutOfMemoryError` (batch 32 on 16GB; AnoLLM batches assume 48GB).
- **Root causes (facts):** (1) ~50–66 min/cell — `max_steps=2000` × emulated bf16 on P100 (~0.5 steps/s) →
  90 cells ≈ 75–100 GPU-h, infeasible on free Kaggle; (2) OOM on wide datasets at hardcoded batch 32.
- **Outcome:** Kaggle P100 retired for this. Science reproduces; hardware unfit.
- **Artifacts:** 10 cell JSONs preserved in `results/raw/exp1_repro/` (gitignored); run log pasted into the
  session transcript (the per-cell `train_runtime` lines drove the diagnosis).
- **Cost:** $0 (free tier).
- **Fixes that followed (commit pending):** precision bf16-only-on-Ampere+ (`_select_precision`); per-dataset
  `(batch, lora)` from AnoLLM Table 7 (`configs/anollm_hparams.yaml`) incl. LoRA for arrhythmia/musk/speech;
  OOM-retry (halve batch). Next run: RunPod A40 48GB.
