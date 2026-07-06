# ROADMAP — execution status & next steps (the living tracker)

**This file is the single source of truth for *where we are and what's next*.** Keep it updated as work
lands. Companions: [`PLAN.md`](PLAN.md) = the research design (the science); approved build plan =
`~/.claude/plans/i-need-to-plan-ancient-dawn.md`; in-repo copy: `docs/claude/plans/i-need-to-plan-ancient-dawn.md`; long-form state =
agent memory `docs/claude/memory/project-state.md` (live copy also in `~/.claude/.../memory/`). If those ever disagree, **this file + git history win for status.**

_Last updated: 2026-07-06 · HEAD `79d71e0` (M3.5 complete)._

---

## TL;DR — current state (2026-07-06)
**M1 gate COMPLETE** (90/90, ~$21): C1+C2 PASS; C3 19/30 (code-vs-paper, not our error) → credible partial
repro, no re-gate. **M2 Exp-2 COMPLETE** (360/360, **$90.42**, analyzed): likelihood ≫ prompted (RQ2);
no significant Qwen scale gain on likelihood (RQ3). **M3 Exp-3/3b COMPLETE** (66/66, **~$13.03**):
results rsync'd + verified locally. **M3.5 COMPLETE** — T3 done, BA1 PASS (|Δ|=0.0012), DA1 PASS
(|Δ|=0.0054). No active pods. Project spend ≈ **$136.61**. Tests **80 green**. Fleet map: `FLEET.md`.

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
| M4 | Exp 4/5/6 — ordering+binning, Pareto, two-stage triage | PLAN Exp 4–6 (RQ5–7) | ⏳ | — |
| M5 | Paid A100 burst — Qwen3-14B scale point | PLAN §9/§9a | ⏳ | cost-gated, ~$25–45 |
| M6 | Analysis & write-up (stats, figures) | PLAN §7/§13 | ⏳ | — |
| Paper | Author the paper (LaTeX template + paper MCP) | PLAN §13 | ⏳ later phase | `paper/01-03` drafts exist |

**Critical path:** M1 → M2 → M3 ✅ → M3.5 ✅ → **M4 (next)** → M6. M5 14B burst is optional and off the critical path.

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

## Immediate next actions (in order)
1. **M4** (Exp 4/5/6 — serialization order, Pareto, two-stage triage). Plan pod + config.
2. (Optional housekeeping) Delete stopped pods to avoid disk charges.
3. **(housekeeping)** revoke the 2 GitHub tokens shared in chat.

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
uv run pytest                                    # 80 tests green
# DA1 pod poll (SSH):
ssh -i ~/.ssh/id_ed25519_runpod_anomaly -p 22004 root@69.30.85.58 \
  'ls /workspace/results/raw/da1_dissolving/*.json | wc -l; tail -3 /workspace/results/logs/m35_da1.log'
```
