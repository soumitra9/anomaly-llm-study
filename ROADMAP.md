# ROADMAP — execution status & next steps (the living tracker)

**This file is the single source of truth for *where we are and what's next*.** Keep it updated as work
lands. Companions: [`PLAN.md`](PLAN.md) = the research design (the science); approved build plan =
`~/.claude/plans/lets-now-very-meticulously-optimized-badger.md`; long-form state =
agent memory `project-state.md`. If those ever disagree, **this file + git history win for status.**

_Last updated: 2026-06-29 (trial complete; M2 built)._

---

## TL;DR — current state
Foundations + reproduction runner + **the full Exp 2 / M2 stack** are built, tested, and committed
(7 commits, `github.com/soumitra9/anomaly-llm-study`). The 3-dataset Kaggle GPU **trial COMPLETED**:
breastw CUDA AUROC **0.991** + wine 0.865 validate the CUDA path; lymphography exposed a real bug
(content-hash forced `dtype=float` → crashed on string categoricals like `'deformed'`) — **found &
fixed** (`io.frame_hash`, commit `51c00bb`, verified locally on lymphography). **Next decision: push the
fix to GitHub + launch the full 30-set gate.** M2 build (Exp 2 runner, mode-B runner, ODDS loaders,
classical panel) is done ahead of the gate.

---

## Milestones

| ID | Milestone | Maps to | Status | Evidence |
|----|-----------|---------|--------|----------|
| M0 | Scaffold + traceability + metrics + tests + AnoLLM submodule | impl-plan M0; PLAN §10 | ✅ done | commit `243fe34`; 22 tests green |
| M1-env | Working AnoLLM stack on arm64 via uv (overrides) | impl-plan M1 | ✅ done | `96875eb`; `uv.lock` |
| M1-local | 3 scoring paths validated locally (breastw) | impl-plan M1 | ✅ done | `4c99eee`; smoke scripts |
| M2-prep | Production reproduction runner (`anodet.eval.exp1`) + Kaggle glue | impl-plan M1/M2 | ✅ done | `54c24c6`, `10d828b` |
| Infra | Push to GitHub + Kaggle MCP + phone-verify (internet) | — | ✅ done | repo public; trial running |
| **M1-GATE** | **Reproduce AnoLLM on ODDS (vs published)** | **PLAN §7, Exp 1** | 🔄 **in progress** | trial v2 RUNNING |
| M2 | Exp 2 — model × scoring-mode on ODDS | PLAN Exp 2 (RQ2/RQ3) | ⏭️ next | — |
| M3 | Exp 3/3b — security transfer + semantic ablation | PLAN Exp 3 (RQ4/RQ3b) | ⏳ | — |
| M4 | Exp 4/5/6 — ordering, Pareto, two-stage triage | PLAN Exp 4–6 (RQ5–7) | ⏳ | — |
| M5 | Paid A100 burst — Qwen3-14B scale point | PLAN §9/§9a | ⏳ | cost-gated, ~$25–45 |
| M6 | Analysis & write-up (stats, figures) | PLAN §7/§13 | ⏳ | — |
| Paper | Author the paper (LaTeX template + paper MCP) | PLAN §13 | ⏳ later phase | out of scope until provided |

**Critical path:** M1-GATE → M2 → M3 → M4/M6. The M5 14B burst is **not** on the critical path for the
two headline findings (likelihood-vs-prompted A/B and semantic transfer both run free on M2/M3).

---

## M1-GATE — detailed checklist (where we are now)
- [x] Reproduction runner built (`anodet/eval/exp1.py`) + validated locally (breastw AUROC 0.980)
- [x] Kaggle path prepped (`scripts/kaggle_gate.py`, `scripts/KAGGLE.md`)
- [x] Code on GitHub; Kaggle MCP working; account phone-verified (notebook internet on)
- [x] Trial v1 → caught "no internet" failure in 33s; root-caused to phone verification
- [x] **Trial v2 (`anollm-repro-trial-v2`) COMPLETE** — breastw CUDA AUROC **0.991**, wine 0.865 (CUDA
      path validated); lymphography crashed → real bug found & fixed (`io.frame_hash`, commit `51c00bb`)
- [ ] **Push fix to GitHub** (Kaggle clones from there) ← *NEXT*
- [ ] Full 30-set gate (`kaggle_gate --full`: 30 ODDS × 5 splits × SmolLM-135M/360M)
- [ ] Compare to AnoLLM published (mean AUROC within ~1pt + per-dataset rank corr + ±std band) → **verdict**

## Immediate next actions (in order)
1. **Push** the frame_hash fix + M2 build to GitHub so the Kaggle gate clones working code.
2. Launch full gate (`kaggle_gate --full`); resumable per-cell JSON across the 30 GPU-h/wk quota.
3. Compare to AnoLLM published → gate verdict (the hard stop for everything downstream).
4. **(housekeeping)** revoke the 2 GitHub tokens shared in chat (no longer needed — tokenless clone).

## M2 build — DONE ahead of the gate (commit `2f0ed17`)
- [x] `anodet/scoring/prompted.py` committed (mode-B expected-value runner; was complete, untracked)
- [x] `anodet/eval/exp2.py` + `configs/exp2.yaml` (360-cell A/B grid; CLI validated on CPU)
- [x] `anodet/data/` loaders (`odds`, `serialize`, `odds_names`) + `anodet/baselines/classical.py` (PyOD panel)
- [x] tests extended → 30 green; smoke_pipeline still green (IForest 0.991 / mode-A 0.978 / mode-B 0.090)

## Phase A — build-everything-non-GPU ahead of the gate — DONE (commits `6a741a3`..`73bf49d`, 53 tests green)
All **provisional** → must be re-validated on real data in **Phase B** after the verdict.
- [x] **GATE_SPEC.md** pre-registered (C1 mean Δ≤0.02, C2 Spearman≥0.80, C3 ≥24/30 band) BEFORE any verdict
- [x] **A1** `anodet/eval/verdict.py` + `configs/anollm_reference.yaml` (per-dataset numbers PENDING eyes-on)
- [x] **A2–A4** `anodet/analysis/{aggregate,stats,figures}.py` + `Makefile` + `make_tables/figures.py`
- [x] **A5** `anodet/data/{creditcard,unsw}.py` (split/leakage-screen/reweight)
- [x] **A6** `anodet/triage/two_stage.py` + `anodet/eval/{exp3_security,exp3b_names,exp4_serialization}.py`
- [x] paper framing prose (`paper/01_intro,02_related_work,03_method.md`)
- [ ] **A7 deep baselines (DeepOD) — DEFERRED**: deepod not in the uv env; adding it mid-gate-campaign risks
      the pinned torch/pyod stack the Kaggle gate depends on. Off critical path (classical panel covers the
      beats-best-classical tally). Revisit in M3.
- [ ] **PENDING (gate-blocking for C2/C3):** transcribe AnoLLM per-dataset ODDS AUROC (eyes-on, 2nd-checked)
      into `configs/anollm_reference.yaml` before the verdict.

---

## Decisions locked (don't relitigate)
- **Mode A = fine-tune INSTRUCT checkpoint with LoRA**; Mode B = same instruct weights frozen → clean A/B.
- **Engine = HF Transformers + PEFT everywhere** (no vLLM in v1) → dissolves cross-engine parity gap.
- **uv** for all env/exec (Python 3.10); our package is **`anodet`** (renamed from `src` to avoid the
  fork's `src` clash). Env overrides: `setuptools`, `override-dependencies=[torch==2.3.1, pyod==2.0.1]`,
  `USE_TF=0`, single-process gloo group.
- **3 seeds**; r tiered (r=10 confirmatory, r=5 expensive, r=21 on small curve sets; per-perm NLLs cached).
- **Exp 3b** on named ODDS (`pima`, `breastw` backup), not credit-card. **Repo public** for now (user choice).
- Compute: free Kaggle/Mac for M1–M4; one ~$25–45 RunPod A100 burst for 14B (M5), **double-confirm gated**.

## Open items / risks
- Trial outcome gates everything (pending).
- Kaggle MCP has been flaky (disconnect/reconnect) — re-search tools if absent.
- Full gate = bulk of free Kaggle quota (30 GPU-h/wk) over a few weeks; resumable per-cell JSON handles
  the 12h session limit.

## Key commands
```bash
uv run pytest                       # 22 metric/determinism/grid tests
uv run python -m anodet.eval.exp1 --dataset breastw --model smol --max-steps 10 --r 2 --device cpu  # local cell
# Kaggle: scripts/KAGGLE.md  (trial: kaggle_gate --datasets lymphography,wine,breastw --splits 1 ...; full: --full)
```
