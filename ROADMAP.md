# ROADMAP — execution status & next steps (the living tracker)

**This file is the single source of truth for *where we are and what's next*.** Keep it updated as work
lands. Companions: [`PLAN.md`](PLAN.md) = the research design (the science); approved build plan =
`~/.claude/plans/i-need-to-plan-ancient-dawn.md`; in-repo copy: `docs/claude/plans/i-need-to-plan-ancient-dawn.md`; long-form state =
agent memory `docs/claude/memory/project-state.md` (live copy also in `~/.claude/.../memory/`). If those ever disagree, **this file + git history win for status.**

_Last updated: 2026-07-05 · HEAD `94d2c42`._

---

## TL;DR — current state (2026-07-05)
**M1 gate COMPLETE** (90/90, ~$21): C1+C2 PASS; C3 19/30 (code-vs-paper, not our error) → credible partial
repro, no re-gate. **M2 Exp-2 COMPLETE** (360/360, **$90.42**, analyzed): likelihood ≫ prompted (RQ2);
no significant Qwen scale gain on likelihood (RQ3). **M3 Exp-3/3b RUNNING** on 1× RunPod A40
(`anomaly-m3-cc`, launched 2026-07-04 ~19:59Z): **20/60** `exp3_security` cells on-pod, **0 failures**;
`exp3b_names` (6 cells) not started yet. Project spend ≈ **$118** ($112 prior + ~$6 M3 accruing).
Tests **74 green**. Fleet map: `FLEET.md`; runner `scripts/exp3_fleet.py` + `scripts/exp3b_run.py`.

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
| **M3** | Exp 3/3b — security transfer + semantic ablation | PLAN Exp 3 (RQ4/RQ3b) | 🔄 **executing** | 34/60 on-pod; `FLEET.md`; `scripts/exp3_fleet.py` |
| **M3.5** | Dissolving arm + binned-creditcard + drop-Time classical | confound bounds | ⏭️ after M3 | ~$5–8; see PLAN.md §M3.5 |
| M4 | Exp 4/5/6 — ordering+binning, Pareto, two-stage triage | PLAN Exp 4–6 (RQ5–7) | ⏳ | — |
| M5 | Paid A100 burst — Qwen3-14B scale point | PLAN §9/§9a | ⏳ | cost-gated, ~$25–45 |
| M6 | Analysis & write-up (stats, figures) | PLAN §7/§13 | ⏳ | — |
| Paper | Author the paper (LaTeX template + paper MCP) | PLAN §13 | ⏳ later phase | `paper/01-03` drafts exist |

**Critical path:** M1 → M2 → **M3 (active)** → M4/M6. M5 14B burst is optional and off the critical path.

---

## M3 — detailed checklist (where we are now)
- [x] Pre-flight: Pima UCI-order gate PASS (`anodet/data/odds_names.py`, 2026-07-04)
- [x] Security loaders validated on real data (`data/creditcard.csv`, `data/unsw.parquet`)
- [x] `scripts/exp3_fleet.py` + `scripts/exp3b_run.py` + tests (`test_exp3_fleet.py`, 74 pytest green)
- [x] M3 golden bundle script (`scripts/build_m3_bundle.sh`)
- [x] Pod provisioned + full `exp3_fleet` launched (`r=5`, all modes, seeds 0–2)
- [ ] **exp3_security → 60/60** on-pod (20 done; creditcard-temporal nearly complete; creditcard-random + unsw ahead)
- [ ] **exp3b_names → 6/6** (pima semantic vs anon, Qwen prompted; after or alongside security grid)
- [ ] Rsync results + logs → local; write `exp3_cost.json`; **teardown pod**; RUNLOG completion entry
- [ ] Analysis: operational metrics, RQ4 bootstrap CIs, RQ3b ΔAUROC CI; refresh `SUMMARY.md`

## Immediate next actions (in order)
1. Monitor M3 pod (`anomaly-m3-cc`) — 34/60 done, 0 failures; Qwen likelihood cells are bottleneck.
2. On `shard.done` + exp3b complete: rsync results+logs → local, teardown pod, record cost, analyze.
3. **M3.5 (one short pod, ~$5–8):** dissolving arm (instruct-likelihood, ~8 ODDS, 1 seed, Qwen first)
   + binned-creditcard arm (folds into Exp 4) + drop-Time classical CPU re-run ($0).
4. **M4** (Exp 4/5/6) — after M3.5 results in hand.
5. **(housekeeping)** revoke the 2 GitHub tokens shared in chat.

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
- **Mode A = fine-tune INSTRUCT checkpoint with LoRA**; Mode B = same instruct weights frozen → clean A/B.
- **Engine = HF Transformers + PEFT everywhere** (no vLLM in v1).
- **uv** for all env/exec (Python 3.10); package **`anodet`**. Overrides: `torch==2.3.1`, `pyod==2.0.1`, `USE_TF=0`.
- **Scale-up model = Qwen2.5-3B** (not Qwen3; transformers 4.48.2 incompatible with qwen3 arch).
- **M2/M3 Qwen steps = 1000** (D0: 2000 over-trains); SmolLM @2000.
- **M3 r=5** (cost lever; flat r-sensitivity from M1). Likelihood on credit-card only; not on UNSW.
- **Exp 3b** on `pima` (breastw backup); Pima column order verified 2026-07-04.
- Compute: **RunPod A40 ($0.44/hr)**; spend double-confirm gated; tear pods down when work ends.

## Open items / risks
- M3 results currently **on-pod only** — no local `results/raw/exp3_*` yet (pull before teardown).
- Qwen likelihood cells dominate M3 wall-clock; single-pod ETA ~1–2 days for full 60+6 grid.
- RunPod create-pod has no startup cmd → pods driven over SSH.
- **USER ACTION:** revoke the 2 GitHub tokens shared in chat.

## Key commands
```bash
uv run pytest                                    # 74 tests green
# M3 pod poll (SSH):
ssh -i ~/.ssh/id_ed25519_runpod_anomaly -p 22015 root@69.30.85.16 \
  'ls /workspace/results/raw/exp3_security/*.json | wc -l; tail -3 /workspace/results/logs/m3_sec.log'
# After M3 completes:
uv run python -m scripts.make_tables   # aggregate exp3 → CSV (when analysis wired)
```
