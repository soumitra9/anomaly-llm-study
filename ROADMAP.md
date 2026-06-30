# ROADMAP — execution status & next steps (the living tracker)

**This file is the single source of truth for *where we are and what's next*.** Keep it updated as work
lands. Companions: [`PLAN.md`](PLAN.md) = the research design (the science); approved build plan =
`~/.claude/plans/lets-now-very-meticulously-optimized-badger.md`; long-form state =
agent memory `project-state.md`. If those ever disagree, **this file + git history win for status.**

_Last updated: 2026-06-29 (trial complete; M2 built)._

---

## TL;DR — current state (2026-06-30, evening; HEAD `d2b6061`)
Foundations + Exp 2/M2 stack + all non-GPU code built, tested (**63 green**), pushed. **M1 gate is
EXECUTING on a 5-pod RunPod A40 fleet** (Kaggle P100 RETIRED — emulated bf16 too slow + OOMs; see
`POSTMORTEM.md`). 90 cells = 30 ODDS × 3 splits, SmolLM-360M, likelihood, max_steps=2000, r=10, ~$11 total,
self-healing to 90/90. Fleet map/dashboard: `FLEET.md` + `scripts/fleet_status.sh`.
Two A40-era fixes landed: **precision-by-capability + per-dataset batch/OOM-retry** (`5d63344`), and a
**scoring-batch decouple** proven AUROC-neutral (`d2b6061`, dAUROC 0.0008). Data-staging resolved: 27/30 ODDS
via adbench; arrhythmia/mulcross/seismic staged from working mirrors (ODDS Stony Brook site is TLS-broken —
see `DATA_LICENSES.md` + `scripts/fetch_special_datasets.sh`).

---

## Milestones

| ID | Milestone | Maps to | Status | Evidence |
|----|-----------|---------|--------|----------|
| M0 | Scaffold + traceability + metrics + tests + AnoLLM submodule | impl-plan M0; PLAN §10 | ✅ done | commit `243fe34`; 22 tests green |
| M1-env | Working AnoLLM stack on arm64 via uv (overrides) | impl-plan M1 | ✅ done | `96875eb`; `uv.lock` |
| M1-local | 3 scoring paths validated locally (breastw) | impl-plan M1 | ✅ done | `4c99eee`; smoke scripts |
| M2-prep | Production reproduction runner (`anodet.eval.exp1`) + Kaggle glue | impl-plan M1/M2 | ✅ done | `54c24c6`, `10d828b` |
| Infra | GitHub + RunPod MCP (Kaggle P100 retired) | — | ✅ done | repo public; 5-pod A40 fleet live |
| **M1-GATE** | **Reproduce AnoLLM on ODDS (vs published)** | **PLAN §7, Exp 1** | 🔄 **executing on 5-pod A40 fleet** | 90 cells running; `FLEET.md` |
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
- [x] Reproduction runner + Kaggle/RunPod glue (`anodet/eval/exp1.py`, `scripts/kaggle_gate.py`)
- [x] Kaggle P100 attempt → infra-fail (emulated bf16 too slow, OOMs); retired. Root causes fixed (`5d63344`).
- [x] Migrated to RunPod A40 fleet; smoke battery passed (wine 6.5× faster, cardio no-OOM, parity wine 0.933≈P100 0.932)
- [x] Scoring-batch fix proven AUROC-neutral (`d2b6061`); special datasets staged (arrhythmia/mulcross/seismic)
- [ ] **Fleet → 90/90** (5 pods, disjoint partition, auto-rerun watchers self-heal race + special cells) ← *IN PROGRESS*
- [ ] Merge 90 JSONs → local; **teardown all pods** (never leave billing); `cost.json` + RUNLOG entry
- [ ] `verdict.py` vs `GATE_SPEC.md` (C1/C2/C3); HARD-STOP on C1/C2 fail → **verdict**

## Immediate next actions (in order)
1. Monitor the fleet to 90/90 via `scripts/fleet_status.sh`; confirm watchers recover all failed cells, 0 fails.
2. rsync all pods' `results/raw/exp1_repro/*.json` → local (90 disjoint); **stop+delete every pod**; write `cost.json`.
3. `uv run python -m anodet.eval.verdict` vs GATE_SPEC → gate verdict (hard stop for everything downstream).
4. **(housekeeping)** revoke the 2 GitHub tokens shared in chat (tokenless clone works).

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
- [x] **AnoLLM per-dataset reference transcribed** (eyes-on, 2nd-checked) into `configs/anollm_reference.yaml`
      from ICLR-2025 Table 10 (mean) + Table 11 (SE), 360M column; self-check mean=0.8651 == paper Avg 0.865.
- [x] **C3 band ±0.02 floor** (pre-results refinement, documented in `GATE_SPEC.md`) — 6 datasets had published
      SE=0 → zero-width band. Verdict tooling now fully unblocked (C1∧C2∧C3). 54 tests green.

**Gate verdict is fully prepared** — when the 90 cells complete, the loop runs `uv run python -m
anodet.eval.verdict` for an automatic C1∧C2∧C3 judgment vs the pre-registered spec.

---

## Decisions locked (don't relitigate)
- **Mode A = fine-tune INSTRUCT checkpoint with LoRA**; Mode B = same instruct weights frozen → clean A/B.
- **Engine = HF Transformers + PEFT everywhere** (no vLLM in v1) → dissolves cross-engine parity gap.
- **uv** for all env/exec (Python 3.10); our package is **`anodet`** (renamed from `src` to avoid the
  fork's `src` clash). Env overrides: `setuptools`, `override-dependencies=[torch==2.3.1, pyod==2.0.1]`,
  `USE_TF=0`, single-process gloo group.
- **3 seeds**; r tiered (r=10 confirmatory, r=5 expensive, r=21 on small curve sets; per-perm NLLs cached).
- **Exp 3b** on named ODDS (`pima`, `breastw` backup), not credit-card. **Repo public** for now (user choice).
- Compute: **RunPod A40 ($0.44/hr) is the workhorse** (Kaggle P100 retired — too slow/small); M5 14B may use A100.
  RunPod spend is **double-confirm gated** ([[runpod-cost-guardrail]]); tear pods down the instant work ends.

## Open items / risks
- **M1 gate verdict gates everything** (in progress on the fleet).
- RunPod create-pod has no startup cmd → pods driven over SSH; `pkill -f <name>` self-kills the SSH session (kill by PID).
- Fresh-pod adbench race: first datasets can FileNotFound before the ~6-min bulk download finishes → pre-download or re-run.
- ODDS Stony Brook host is TLS-broken → arrhythmia/mulcross/seismic via mirrors ([[odds-special-datasets]]).
- **USER ACTION:** revoke the 2 GitHub tokens shared in chat.

## Key commands
```bash
uv run pytest                       # 63 tests green
bash scripts/fleet_status.sh        # poll all 5 RunPod gate pods (cells done/18, GPU, fails)
bash scripts/fetch_special_datasets.sh   # stage arrhythmia/mulcross/seismic (not in adbench)
uv run python -m anodet.eval.verdict     # gate verdict vs GATE_SPEC after 90 cells land
```
