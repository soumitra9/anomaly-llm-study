# ROADMAP — execution status & next steps (the living tracker)

**This file is the single source of truth for *where we are and what's next*.** Keep it updated as work
lands. Companions: [`PLAN.md`](PLAN.md) = the research design (the science); approved build plan =
`~/.claude/plans/i-need-to-plan-ancient-dawn.md`; in-repo copy: `docs/claude/plans/i-need-to-plan-ancient-dawn.md`; long-form state =
agent memory `docs/claude/memory/project-state.md` (live copy also in `~/.claude/.../memory/`). If those ever disagree, **this file + git history win for status.**

_Last updated: 2026-07-07 · M4 complete (33/33 cells; $141.41 total)._

---

## TL;DR — current state (2026-07-06)
**M1 COMPLETE** (90/90, ~$21): C1+C2 PASS, credible partial repro. **M2 COMPLETE** (360/360, $90.42): likelihood ≫ prompted; no Qwen scale gain. **M3 COMPLETE** (66/66, ~$13.03). **M3.5 COMPLETE** — BA1+DA1 PASS. **M4 COMPLETE** (33/33, ~$4.80) — Exp 4: domain ordering NOT helpful; Exp 6: IForest dominates, triage adds no value (negative result). No active pods. Spend ≈ **$141.41**. Tests **85 green**.

---

## Milestones

| ID | Milestone | Maps to | Status | Evidence |
|----|-----------|---------|--------|----------|
| M0 | Scaffold + traceability + metrics + tests + AnoLLM submodule | impl-plan M0; PLAN §10 | ✅ done | commit `243fe34` |
| M1-env | Working AnoLLM stack on arm64 via uv (overrides) | impl-plan M1 | ✅ done | `96875eb`; `uv.lock` |
| M1-local | 3 scoring paths validated locally (breastw) | impl-plan M1 | ✅ done | `4c99eee` |
| M2-prep | Production reproduction runner + Kaggle/RunPod glue | impl-plan M1/M2 | ✅ done | `54c24c6`, `10d828b` |
| Infra | GitHub + RunPod MCP (Kaggle P100 retired) | — | ✅ done | repo public |
| **M1-GATE** | **Reproduce AnoLLM on ODDS (vs published)** | **PLAN Exp 1, RQ1** | ✅ **done** | 90 cells; `GATE_SPEC.md`; `results/raw/exp1_repro/` |
| **M2** | Exp 2 — model × scoring-mode on ODDS | PLAN Exp 2 (RQ2/RQ3) | ✅ **done** | 360 cells; `results/tables/exp2_odds.csv`; `RUNLOG.md` |
| **M3** | Exp 3/3b — security transfer + semantic ablation | PLAN Exp 3 (RQ4/RQ3b) | ✅ **done** | 66/66 cells; rsync'd + verified; `results/raw/exp3_security/` + `exp3b_names/` |
| **M3.5** | Dissolving arm + binned-creditcard + drop-Time classical | confound bounds | ✅ **done** | T3 done; BA1 PASS (|Δ|=0.0012); DA1 PASS (|Δ|=0.0054); `FLEET.md` |
| M4 | Exp 4/5/6 — ordering+binning, Pareto, two-stage triage | PLAN Exp 4–6 (RQ5–7) | ✅ **done** | 33/33 cells; rsync'd; tables+figures generated; pod stopped |
| M5 | Paid A100 burst — Qwen3-14B scale point | PLAN §9/§9a | ⏳ | cost-gated, ~$25–45 |
| M6 | Analysis & write-up (stats, figures) | PLAN §7/§13 | ✅ **done** | `m6_stats.py`/`m6_figures.py`; `paper/04_results.md`; `paper/05_discussion.md`; commit `c88e861` |
| Paper | Author the paper (LaTeX template + paper MCP) | PLAN §13 | ⏳ later phase | `paper/01-03` drafts exist |

**Critical path:** M1 → M2 → M3 ✅ → M3.5 ✅ → M4 ✅ → M6 ✅. **Next:** Paper (LaTeX draft). M5 14B burst is optional and off the critical path.

---

## M3 — COMPLETE ✅
- [x] 60/60 `exp3_security` + 6/6 `exp3b_names` — all `status=complete`, 0 failures
- [x] Pod `l2css8jckkkp0q` stopped; cost ~$13.03 (29.6 h × $0.44/hr); RUNLOG updated
- [x] Results rsync'd + verified locally: `results/raw/exp3_security/` + `results/raw/exp3b_names/`
- [ ] Formal analysis (RQ4 bootstrap CIs, RQ3b ΔAUROC CI) — deferred until M3.5 DA1 in hand

## M3.5 — COMPLETE ✅
- [x] **Drop-Time classical (T3):** KNN collapses 0.178 → 0.932 when Time excluded. 24-cell `exp3_security_notime` + 4-cell `ba1_binned_notime` saved. Corrected protocol documented.
- [x] **BA1 binned-creditcard:** mean |ΔAUROC| = 0.0012 → **PASS** (threshold 0.03). Sentence in `paper/03_method.md`.
- [x] **DA1 dissolving arm:** 8/8 done; mean |ΔAUROC(instruct+LoRA − base+LoRA)| = **0.0054** → **PASS** (threshold 0.02). Sentence in `paper/03_method.md`. Pod stopped (~$5.61).
- [ ] Delete stopped pods `l2css8jckkkp0q` (M3) + `xbga2ae1dqfp12` (M3.5 DA1) — disks still live

## M4 — COMPLETE ✅ (2026-07-07)
- [x] M4 code written + tested (85 tests green, `c3ee07b`)
- [x] Pod `pyinsl4hrttusc` (A40, $0.44/hr) run 2026-07-06 16:17Z → 2026-07-07 03:10Z (~10.9h, ~$4.80)
- [x] Exp 4 (serialization order): 24/24 cells — `results/raw/exp4_serialization/` rsync'd
- [x] Exp 6 (two-stage triage): 9/9 cells — `results/raw/exp6_triage/` rsync'd (1 incident: double-kwarg bug, fixed `c3ee07b`)
- [x] Exp 5 (Pareto): run locally — `results/tables/exp5_pareto.csv`, `results/figures/exp5_pareto.png`
- [x] All tables regenerated via `make_tables.py`
- [ ] Pod `pyinsl4hrttusc` — stop via RunPod console (MCP auth down)

## Immediate next actions (in order)
1. **STOP pod `pyinsl4hrttusc`** via RunPod console (GPU still billing; MCP auth down).
2. **M6** — Friedman/bootstrap on M4 results; write paper sections for RQ5/RQ6/RQ7.
3. (Housekeeping) Delete stopped pods (`l2css8jckkkp0q`, `xbga2ae1dqfp12`, `pyinsl4hrttusc`) to avoid disk charges.
4. **(housekeeping)** revoke the 2 GitHub tokens shared in chat.

---

## M1-GATE — DONE (archived checklist)
- [x] 90/90 cells merged+deduped; verdict vs `GATE_SPEC.md`: C1 PASS, C2 PASS, C3 19/30 → partial repro
- [x] C3 shortfall root-caused (released fork vs paper; grad-accum test refuted config hypothesis)
- [x] All M1 pods torn down; spend ≈ $21

## M2 — DONE (archived checklist)
- [x] 360/360 cells, 0 failures; analyzed (Friedman + Holm-Wilcoxon RQ2/RQ3)
- [x] Key finding: likelihood ≫ prompted; Qwen-3B no significant likelihood gain vs SmolLM-360M
- [x] Real cost $90.42; backup `results/backups/exp2_odds_FINAL_360cells.tgz`
- [x] Ops lesson: detached nohup teardown failed → M3 uses completion-triggered guardian (see plan)

---

## Decisions locked (don't relitigate)
- **Mode A = fine-tune BASE checkpoint with LoRA**; Mode B = frozen instruct sibling → same family+size, different recipe. Checkpoint confound bounded by M3.5 DA1 (`GATE_SPEC.md §DA1`; pre-registered).
- **Engine = HF Transformers + PEFT everywhere** (no vLLM in v1).
- **uv** for all env/exec (Python 3.10); package **`anodet`**. Overrides: `torch==2.3.1`, `pyod==2.0.1`, `USE_TF=0`.
- **Scale-up model = Qwen2.5-3B** (not Qwen3; transformers 4.48.2 incompatible with qwen3 arch).
- **M2/M3 Qwen steps = 1000** (D0: 2000 over-trains); SmolLM @2000.
- **M3 r=5** (cost lever; flat r-sensitivity from M1). Likelihood on credit-card only; not on UNSW.
- **Exp 3b** on `pima` (breastw backup); Pima column order verified 2026-07-04.
- Compute: **RunPod A40 ($0.44/hr)**; spend double-confirm gated; tear pods down when work ends.

## Open items / risks
- **Stopped pods** (`l2css8jckkkp0q` M3, `xbga2ae1dqfp12` M3.5) — disks still live; delete when ready.
- RunPod create-pod has no startup cmd → pods driven over SSH.
- **USER ACTION:** revoke the 2 GitHub tokens shared in chat.

## Key commands
```bash
uv run pytest                                    # 85 tests green
# M4 pod poll (SSH):
ssh -i ~/.ssh/id_ed25519_runpod_anomaly -p 22071 root@69.30.85.142 \
  'ls /workspace/results/raw/exp4_serialization/*.json | wc -l; ls /workspace/results/raw/exp6_triage/*.json 2>/dev/null | wc -l; tail -3 /workspace/m4_exp6.log'
# Post-rsync: local Pareto + tables
uv run python scripts/exp5_pareto.py
make tables figures
```
