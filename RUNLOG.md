# RUNLOG — compute-session ledger

Append-only. **One entry per compute session** (Kaggle / RunPod / local-GPU). This is the human-readable
companion to the machine system-of-record (per-cell JSON under `results/raw/<exp>/`, each with full
`RunMetadata`). Newest entries on top. Keep it factual: what ran, where, what landed, what failed + why, cost.

Conventions: link incidents to [POSTMORTEM.md](POSTMORTEM.md); record git SHA, GPU, exact command, cells
new/skipped/failed, cost, and where results/logs were saved. Always capture the run's stdout log to
`results/logs/`.

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
- **Outcome:** Kaggle P100 retired for this. Science reproduces; hardware unfit. Full analysis: POSTMORTEM.md.
- **Artifacts:** 10 cell JSONs preserved in `results/raw/exp1_repro/` (gitignored); run log pasted into the
  session transcript (the per-cell `train_runtime` lines drove the diagnosis).
- **Cost:** $0 (free tier).
- **Fixes that followed (commit pending):** precision bf16-only-on-Ampere+ (`_select_precision`); per-dataset
  `(batch, lora)` from AnoLLM Table 7 (`configs/anollm_hparams.yaml`) incl. LoRA for arrhythmia/musk/speech;
  OOM-retry (halve batch). Next run: RunPod A40 48GB.
