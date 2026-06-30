# Blameless postmortem — M1 reproduction-gate, Kaggle session 1 (`anollm-gate-360-s1`)

**Date:** 2026-06-30. **Author:** project log. **Status:** session 1 COMPLETE; gate NOT finished (10/90 cells).
**Framing:** blameless — the goal is to record *what happened and why*, in facts, so the next run is fixed.
No part of this is fact-by-assumption; every number below is quoted from the Kaggle run log or the per-cell
result JSONs. Where something is a *projection* (e.g. speed on hardware we have not run), it is labelled
**[PROJECTION]**.

---

## 1. What we set out to do
Run the M1 reproduction gate: SmolLM-360M, likelihood scoring, **30 ODDS datasets × 3 splits = 90 cells**,
`max_steps=2000`, `r=10`, on a free Kaggle GPU, with a 10h (`--time-budget-secs 36000`) clean-exit budget and
resumable per-cell JSON. Goal: reproduce AnoLLM's published per-dataset AUROC (GATE_SPEC C1/C2/C3).

## 2. What actually happened (facts from the run log)
- GPU assigned: **Tesla P100-PCIE-16GB** (log line: `CUDA? True Tesla P100-PCIE-16GB`). Precision used:
  **bf16** (from each result JSON's `run_metadata.precision`).
- Session ran **~10.1h wall** (`GATE_SESSION_DONE_OK` at 36,393s) and exited cleanly at the budget
  (`[budget] time budget 36000s exceeded (36287s) — stopping cleanly`).
- Final summary line: **`this session: 10 new, 0 skipped, 3 failed`**.
- Setup overhead before the first cell: clone ~3.5s, `pip install uv` ~5s, **`uv sync` ~88s**, then the
  **adbench bulk dataset download ~380s** (122s→501s) — it fetches *all* adbench datasets (CIFAR/MNIST/MVTec/
  SVHN/NLP-BERT/47 Classical) though we use ~4.

### Per-cell facts (train_runtime from the log; AUROC from JSONs)
| cell | train_runtime | steps/s | wall/cell | AUROC |
|---|---|---|---|---|
| wine s0/s1/s2 | 3986 / 4001 / 3991 s | ~0.50 | ~4.0–4.4k s | 0.932 / 0.887 / 0.967 |
| breastw s0/s1/s2 | 2975 / 2975 / 2975 s | ~0.67 | ~3.06k s | 0.991 / 0.995 / 0.997 |
| **cardio s0/s1/s2** | — | — | ~2–3 s | **FAIL (CUDA OOM)** |
| ecoli s0/s1/s2 | 3599 / 3599 / 3598 s | ~0.56 | ~3.64k s | 0.863 / 0.858 / 0.860 |
| lymphography s0 | 3684 s | ~0.54 | ~3.71k s | 1.000 |

→ **~50–66 min of training per cell** (≈0.5–0.67 optimizer steps/sec for ~2000 steps). Scoring (r=10) was
small: 18s (wine) to 83s (breastw). 10 cells consumed essentially the whole 10h budget.

### The failure
**cardio split0/1/2 all failed:** `OutOfMemoryError: CUDA out of memory. Tried to allocate 826.00 MiB`.
cardio = 1,831 rows, **21 features** → longer serialized sequences → `batch_size=32` did not fit in the
P100's 16GB. The 3 fails were fast (~2–3s each), so they cost negligible time; they just produced no JSON,
which is why cardio is absent from the output and only 10 cells landed.

## 3. What went RIGHT
The science reproduces where it ran. Versus AnoLLM's published SmolLM-360M numbers:
- **breastw 0.991 / 0.995 / 0.997** vs published **0.993** — essentially exact. ✓
- **lymphography 1.000** (1 split) vs **0.993** — within tolerance. ✓
- wine ~0.93 vs 0.851 and ecoli ~0.86 vs 0.804 run *high* — but these are tiny, high-variance datasets and
  only 4 of 30; not interpretable yet. The pipeline + full-fine-tune path are correct on real CUDA.

## 4. Root causes (facts)
1. **Throughput — `max_steps=2000` on a P100 with emulated bf16.** P100 (Pascal) has **no hardware bf16**, so
   torch emulates it (slow), and the P100 is an old card; result ~0.5 steps/s → ~50–66 min/cell →
   **90 cells ≈ ~75–100 GPU-h** (≈ 3–4 weeks at Kaggle's 30 GPU-h/week). The gate cannot finish in the free
   budget at these settings.
2. **OOM — `batch_size=32` hardcoded.** AnoLLM's batch sizes (their Table 7) were tuned for a **48GB A6000**;
   on a **16GB P100** the wider datasets (cardio 21f, and by extension arrhythmia 274f, speech 400f, musk 166f,
   optdigits 64f, …) exceed memory at batch 32.

## 5. Why it wasn't caught earlier (blameless process factors)
- **The trial under-tested by design.** The pre-flight trial used `max_steps=300` (6.7× fewer than the real
  2000) and only **3 narrow datasets** (lymphography/wine/breastw). It correctly validated the CUDA *path*,
  but by construction it could not reveal (a) the true per-cell time at 2000 steps, nor (b) the OOM on a wide
  dataset. *Lesson: a pre-flight should include one cell at full settings and one wide-feature dataset.*
- **The ETA was extrapolated without scaling by step count.** Per-cell time from the 300-step trial was used
  without multiplying by ~6.7× for 2000 steps → the "~10–15 GPU-h for 90 cells" estimate was ~6× too low.
  *Lesson: scale ETAs by the actual run parameters, not the probe's.*
- **bf16 was selected unconditionally for any CUDA device** in `run_likelihood`, with no check for whether the
  GPU has hardware bf16 (Ampere+). On Pascal/Turing this silently falls back to slow emulation.

## 6. Required code fixes (for the next run, independent of where it runs)
- **Precision:** select bf16 only on Ampere+ (compute capability ≥ 8.0); else fp16 (or fp32). Off-by-default
  emulated bf16 is the main avoidable slowdown.
- **Batch size / OOM:** use AnoLLM's per-dataset batch sizes (their Table 7) and/or auto-reduce batch on OOM
  (catch + retry at smaller batch, optionally with gradient accumulation to preserve the effective batch).
- (Quality-of-life, not correctness:) pre-stage only the needed ODDS `.npz` files instead of the full adbench
  bundle; this is minor (~6 min/session) but trivial to cut on a persistent-disk host.

---

## 7. RunPod analysis — what we'd run, ETA, cost

### What we'd run
Finish the gate: **80 cells remaining** (90 total − 10 done; the 10 done are bf16 and stay valid if we keep
bf16 on an Ampere card). Optionally rerun all 90 for single-precision purity (+10 cells).

### Why a RunPod GPU fixes both root causes
An **Ampere/Ada GPU has hardware bf16** (fixes the emulation slowdown) and **≥40–48GB** options (fixes the OOM
→ we can use AnoLLM's real batch sizes = *more* faithful). RunPod also gives a **persistent disk**, so the
adbench download + `uv sync` happen **once**, not per session.

### Per-cell time
- **FACT (P100, emulated bf16, 2000 steps):** ~50–66 min/cell.
- **[PROJECTION] on Ampere/Ada hardware bf16:** typical 360M fine-tuning runs ~10–25× faster than this P100
  measurement → **~3–7 min/cell**. This is a projection, NOT measured. **The honest way to make it a fact is a
  1-cell timing probe as the first paid action (a few cents).** We should not commit the full run on a
  projection.

### Cost model (FACT: rates pasted from the RunPod console, 2026-06-30)
| GPU | mem | bf16 | $/hr (FACT) | notes |
|---|---|---|---|---|
| **RTX A6000** | **48GB** | **yes (Ampere)** | **$0.33** | cheapest w/ enough mem; **AnoLLM's actual GPU** → max fidelity |
| A40 | 48GB | yes (Ampere) | $0.35 | ~tied with A6000; 48GB no-OOM |
| L40 | 48GB | yes (Ada) | $0.69 | faster, pricier |
| RTX 6000 Ada | 48GB | yes (Ada) | $0.74 | faster, pricier |
| L40S | 48GB | yes (Ada) | $0.79 | faster, pricier |
| A100 PCIe | 80GB | yes | $1.19 | fastest/biggest of the sane options |
| A100 SXM | 80GB | yes | $1.39 | fastest |
| RTX 5090 | 32GB | yes (Blackwell) | $0.69 | very fast; 32GB may OOM the *widest* sets |
| L4 | 24GB | yes (Ada) | $0.44 | low-power/slow; 24GB; not recommended |

**Total to finish the gate** = 80 cells. Per-cell on Ampere/Ada bf16 is **[PROJECTION] ~3–7 min/cell** (P100
fact was ~50–66 min on *emulated* bf16; hardware bf16 + a modern card is ~10–25× faster). → ~4.3–9.6 GPU-h
incl. ~0.3h one-time setup. At the pasted rates:
- **RTX A6000 ($0.33/hr) → ~$1.4–3.2** ◀ recommended
- A40 ($0.35) → ~$1.5–3.4
- L40 ($0.69) → ~$3–6.6
- A100 PCIe ($1.19) → ~$5–11.4
- A100 SXM ($1.39) → ~$6–13.3

So finishing the gate is **~$2–3 on the A6000/A40**, a few hours of wall-clock — vs ~3–4 weeks (and OOMs) on
free P100. (Even re-running all 90 cells fresh is ~$2–4 on the A6000.)

**Broader implication:** at $0.33/hr the A6000 also makes **M2 (Exp 2, ~360 cells)** affordable (~$5–10), so a
RunPod A6000 may be the right *workhorse* for the whole compute plan — total M1+M2 likely **<$15**, far under
the ~$100 budget. The "free-Kaggle-for-the-bulk" assumption is undermined by the P100 being too slow/small.

### Recommendation
1. Apply the two code fixes (precision: bf16 only on Ampere+; batch/OOM: AnoLLM per-dataset batch sizes +
   OOM-retry).
2. **GPU: RTX A6000 48GB @ $0.33/hr** — cheapest, no-OOM, hardware bf16, and *the same card AnoLLM used*
   (most faithful). A40 @ $0.35 is an equal fallback. A100 PCIe @ $1.19 only if wall-clock speed matters more
   than the ~$8 difference.
3. **Probe 1 cell first** to turn per-cell time from projection → fact (~$0.03–0.10), then run the rest.
4. Tear the pod down the instant it finishes (`stop`+`delete`); log `cost.json`. **Double-confirm before any
   spend** (standing guardrail).

---

## 8. Decision (rates now known — section 7 updated with the pasted console prices)
Recommended path: **RTX A6000 48GB @ $0.33/hr** (cheapest + 48GB no-OOM + hardware bf16 + AnoLLM's actual
GPU). Probe 1 cell, then finish the 80 remaining cells. Projected total **~$2–3**. Per the standing guardrail,
no pod is created/started without the user's explicit double-confirmation.
