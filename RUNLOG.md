# RUNLOG — compute-session ledger

Append-only. **One entry per compute session** (Kaggle / RunPod / local-GPU). This is the human-readable
companion to the machine system-of-record (per-cell JSON under `results/raw/<exp>/`, each with full
`RunMetadata`). Newest entries on top. Keep it factual: what ran, where, what landed, what failed + why, cost.

Conventions: record git SHA, GPU, exact command, cells
new/skipped/failed, cost, and where results/logs were saved. Always capture the run's stdout log to
`results/logs/`.

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
