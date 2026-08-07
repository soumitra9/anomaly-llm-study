# ROADMAP — execution status & next steps (the living tracker)

**This file is the single source of truth for *where we are and what's next*.** Keep it updated as work
lands. Companions: [`PLAN.md`](PLAN.md) = the research design (the science); approved build plan =
`~/.claude/plans/i-need-to-plan-ancient-dawn.md`; in-repo copy: `docs/claude/plans/i-need-to-plan-ancient-dawn.md`; long-form state =
agent memory `docs/claude/memory/project-state.md` (live copy also in `~/.claude/.../memory/`). If those ever disagree, **this file + git history win for status.**

_Last updated: 2026-08-07 · Revision compute + Phase 4 analysis complete._

---

## TL;DR — current state (2026-08-07)
**M1–M6 COMPLETE.** Paper submitted (`paper/draft_v1/main.pdf`, 7 pages); **Weak Accept** review received. **Revision compute COMPLETE:** RV1 (3/3) + RV2 (24/24); backup `results/backups/revision_20260807T212210Z.tgz`. **Phase 4 analysis COMPLETE:** tables (`exp3_security.csv`, `exp2_fewshot.csv`), `m6_stats.json` §RV1/§RV2, figures (`rv2_fewshot_vs_zeroshot.png`, `rv1_unsw_likelihood.png`). Pod `1y91hqyjou9pkx` **stopped** (EXITED). **Next:** narrative decision (item 1), then `draft_v1_revised` integration. RunPod: **0 running pods**. Project spend ≈ **$153.62**. Tests **97 green**.

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
| Paper | Author + submit LaTeX draft | PLAN §13 | ✅ submitted | `paper/draft_v1/main.pdf` (Jul 13) |
| **Revision** | Address reviewer feedback + resubmit | review response | 🔄 **analysis done** | RV1 3/3 + RV2 24/24; Phase 4 tables/stats/figures done; `draft_v1_revised/` pending |

**Critical path:** M1 → M2 → M3 ✅ → M3.5 ✅ → M4 ✅ → M6 ✅ → Paper ✅ submitted → **Revision Phase**. M5 14B burst remains optional and off the critical path.

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
- [x] Deleted stopped pods `l2css8jckkkp0q` (M3) + `xbga2ae1dqfp12` (M3.5 DA1)

## M4 — COMPLETE ✅ (2026-07-07)
- [x] M4 code written + tested (85 tests green, `c3ee07b`)
- [x] Pod `pyinsl4hrttusc` (A40, $0.44/hr) run 2026-07-06 16:17Z → 2026-07-07 03:10Z (~10.9h, ~$4.80)
- [x] Exp 4 (serialization order): 24/24 cells — `results/raw/exp4_serialization/` rsync'd
- [x] Exp 6 (two-stage triage): 9/9 cells — `results/raw/exp6_triage/` rsync'd (1 incident: double-kwarg bug, fixed `c3ee07b`)
- [x] Exp 5 (Pareto): run locally — `results/tables/exp5_pareto.csv`, `results/figures/exp5_pareto.png`
- [x] All tables regenerated via `make_tables.py`
- [x] Pod `pyinsl4hrttusc` — stopped

## Revision Phase — compute complete (2026-08-07)

**Verdict:** Weak Accept (4/5). Overall recommendation: paper just clears the bar; reservations on prompted baseline strength, UNSW likelihood gap, and scoping.

### RV1 + RV2 results (system of record: `results/raw/`)

**§RV1 — UNSW likelihood** (`exp3_security`, qwen2.5-3b, r=5, max_steps=1000, seeds 0–2):

| Seed | AUPRC gain | recall@1%FPR |
|------|------------|--------------|
| 0 | 7.17 | 0.273 |
| 1 | 7.67 | 0.309 |
| 2 | 8.22 | 0.324 |

vs M3 prompted UNSW seed0: gain 3.99, recall@1%FPR 0.148. Likelihood is the stronger LLM mode on UNSW.

**§RV2 — Few-shot prompted** (`exp2_fewshot`, k=3 normals-only, 8 DA1 ODDS datasets × 3 seeds = 24 cells):

| Metric | Zero-shot prompted | Few-shot prompted | Likelihood |
|--------|-------------------|-------------------|------------|
| Mean AUROC (8 sets) | 0.468 | **0.759** | 0.773 |

Mean ΔAUROC (few-shot − zero-shot) = **+0.290** (24 cells). Few-shot closes **~95%** of the zero-shot→likelihood gap (0.468→0.773). **Not uniform:** large gains on breastw (+0.76), yeast (+0.63), ionosphere (+0.55); regressions on speech (−0.10) and vertebral (−0.22).

**Open narrative decision (pre-registered in GATE_SPEC §RV2):** few-shot materially strengthens prompted Mode B on these 8 sets — narrow the headline "likelihood dominates prompted" to the **zero-shot expected-value instantiation** tested in M2, or report as a fifth honest finding. Artifacts: `results/tables/exp2_fewshot.csv`, `results/figures/rv2_fewshot_vs_zeroshot.png`, `m6_stats.json` keys `rv2_fewshot`.

**Phase 4 artifacts:** `results/tables/exp3_security.csv` (UNSW likelihood rows), `exp2_fewshot.csv`, `m6_stats.json` (`rv1_unsw_likelihood`, `rv2_fewshot`), `results/figures/rv1_unsw_likelihood.png`, `rv2_fewshot_vs_zeroshot.png`.

**Ops:** Pod `1y91hqyjou9pkx` (A40 SECURE $0.44/hr, CA-MTL-1); RV1 ~5 h/cell; RV2 ~2.9 h total fleet time; `stop-pod` 2026-08-07; pull+verify backup `revision_20260807T212210Z.tgz`.

### Reviewer feedback (verbatim)

```
======= Review 1 =======

*** Strong aspects: Comments to the author: what are the strong aspects of the paper?

• Rigorous, pre-registered methodology: replication gates (C1–C3) and confound checks were fixed before generating results, with explicit hard-stop decision rules. This is well above the norm and makes the findings credible. • Clean controlled A/B design: holding model family and size fixed while varying only the scoring mode (likelihood vs. prompted) is a well-constructed comparison, and the same serialization is shared across modes within each comparison. • Honest, explicit negative results: the paper foregrounds three negative findings (domain ordering, semantic names, two-stage triage), which is valuable and rarely reported. • Thorough confound controls: DA1 (checkpoint confound, mean |ΔAUROC| = 0.0054), BA1 (credit-card binning, Δ = 0.0012), and T3 (Time-feature leakage collapsing kNN AUROC from 0.932 to 0.178) show careful experimental hygiene. • Appropriate statistics: Friedman omnibus (χ² = 55.27, p = 6.0×10⁻¹²), Nemenyi critical-difference diagram, and Holm-corrected Wilcoxon tests are the right tools and are applied correctly. • Genuinely useful practical message: the demonstration that strong ODDS AUROC (e.g., IForest 0.951) does not translate to fixed-budget recall (recall@1%FPR 0.586) is an actionable warning for practitioners. • Careful scoping of claims: every claim is bounded to the datasets, metrics, and methods actually tested; Table I is an exemplary summary of regimes and supported claims. • Reproducibility hygiene: pinned dependencies (torch 2.3.1, transformers 4.48.2), recorded seeds/splits/hyperparameters, and transparent handling of run-to-run variance (0.851 replication vs. 0.843 comparison run).

*** Weak aspects: Comments to the author: what are the weak aspects of the paper?

• Weak, single prompted baseline: Mode B is one narrow instantiation (expected value over digit tokens from a single forward pass) with no few-shot, chain-of-thought, calibration, or temperature scaling. Because a central result is "likelihood dominates prompted," this conclusion may partly reflect the weakness of the chosen prompted baseline rather than an intrinsic advantage of likelihood scoring. • Checkpoint confound in the core A/B: Mode A (base + LoRA) and Mode B (frozen instruct) differ in both scoring method and checkpoint, so scoring mode and fine-tuning are partly conflated. DA1 bounds this confound but does not eliminate it. • Security evaluation rests on only two datasets: with n = 2 no cross-dataset test is possible, which limits how far the headline "classical beats LLM at fixed FPR" can generalize. • Likelihood arm missing on UNSW-NB15: it was omitted for GPU budget, so on the second security dataset the LLM side is represented only by the weak prompted mode; the strongest LLM configuration is untested there, weakening the UNSW conclusion. • Underpowered ablations: the semantic-name and serialization-order ablations use n = 3 seed pairs (minimum achievable Wilcoxon p = 0.25), so the null results are weak, exploratory evidence rather than conclusions. • C3 replication gate failed with no identified cause: only 19 of 30 datasets fell within the pre-registered per-dataset band (threshold 24), and the source of deviation is unexplained. Since the extensions build on this base, the unresolved per-dataset shortfall matters. • Narrow scale range: the study covers only 360M–3B parameters, so the "scale does not help" claim does not speak to the 7B+ range that many open-weight practitioners actually deploy. • Single hand-designed domain ordering: one manually defined ordering per dataset makes it hard to generalize the null result; a single instance cannot rule out that some informed ordering helps. • Limited novelty by design: this is a replication and evaluation study rather than a new method. That is a legitimate and useful contribution, but the novelty ceiling is inherently lower.

*** Recommended changes: Recommended changes. Please indicate any changes that should be made to the paper if accepted.

Strengthen the prompted baseline with at least one stronger variant (few-shot, calibrated/temperature-scaled, or chain-of-thought), or explicitly narrow the "likelihood dominates prompted" claim to the expected-value prompting instantiation tested.
Address the checkpoint confound directly: run a 2×2 (base vs. instruct) × (LoRA vs. frozen) on at least a subset, or expand DA1, so scoring mode is isolated from the fine-tuning/checkpoint difference.
Add the Qwen2.5-3B likelihood arm on UNSW-NB15, or clearly restrict the UNSW-NB15 conclusion to prompted-only LLM scoring, since the strongest LLM mode is currently missing there.
Expand the security panel beyond two datasets (the paper's own >5-dataset future work) to enable cross-dataset statistics and a defensible generalization of the fixed-FPR result.
Increase seeds/pairs for the semantic-name and serialization-order ablations beyond n = 3, or label them explicitly as exploratory and avoid drawing any conclusion from them.
Investigate the C3 failure: report which datasets fell outside the band and give candidate explanations (LoRA instability on small tabular data, preprocessing, tokenizer differences), consistent with the paper's own future-work note on LoRA stability.
State the scale caveat (360M–3B) prominently next to the scale claim, and, if feasible, add one 7B-scale point to test whether the null on model scale persists.
Test more than one domain-informed ordering, or state explicitly next to the claim that a single hand-designed ordering cannot rule out informed orderings in general.
Consider adding a short compute/cost table alongside Fig. 4 to reinforce the practicality argument (e.g., wall-time and GPU-hours per dataset for each mode).
Define "regime-dependent" crisply in the introduction, and surface the Table III footnote (likelihood arm evaluated on credit-card only) near its first mention to avoid over-reading the security comparison.

*** Technical content and scientific rigour: Good - Significant technical content with basically correct argumentation. (3)

*** Novelty and originality: Moderate - an alternative approach to an existing problem. (3)

*** Overall Recommendation: Weak Accept: You think the paper is only just good enough to be accepted, but have no problem with it being rejected if that is the view of others. (4)

Regards, The conference chairs
```

### Revision response plan (10 items → action)

| # | Reviewer item | Action |
|---|---------------|--------|
| 1 | Strengthen prompted baseline or narrow claim | **Done (§RV2):** few-shot mean AUROC 0.759 vs zero-shot 0.468; **decision pending** — likely narrow claim (see results above). |
| 2 | Checkpoint 2×2 or expand DA1 | **Scope:** DA1 already bounds at 0.0054; cite in response. |
| 3 | UNSW likelihood arm | **Done (§RV1):** 3/3 seeds; likelihood beats prompted on UNSW (gain 7.2–8.2 vs 3.99). |
| 4 | Expand security panel | **Scope:** future work (>5 datasets). |
| 5 | Underpowered ablations (n=3) | **Scope:** label exploratory (already in draft). |
| 6 | C3 failure unexplained | **Write:** grad-accum investigation + failing-dataset list. |
| 7 | Scale 360M–3B only | **Scope:** caveat sentence next to scale claim. |
| 8 | Single domain ordering | **Scope:** caveat sentence next to RQ5 claim. |
| 9 | Compute/cost table | **Write:** table from existing timing numbers. |
| 10 | Define regime-dependent; Table III footnote | **Write:** intro + first mention. |

**Pre-registered compute (done):** `GATE_SPEC.md` §RV1 + §RV2. Actual revision pod cost ≈ **$12.21** (~27.8 h × $0.44/hr, includes idle gaps between phases).

**RunPod (2026-08-07):** pod `1y91hqyjou9pkx` EXITED. `list-pods` → 0 running.

**Phase 0 (user):** Confirm in EDAS: Review 2?, revision deadline?, response-letter format?, CARS 2026 page limit?

---

## Immediate next actions (in order)
1. **Narrative decision** — review Phase 4 artifacts; decide item-1 framing (narrow zero-shot claim vs fifth finding).
2. **Integrate** — `paper/draft_v1` → `paper/draft_v1_revised`; free-win text + new results; response letter.
3. (Optional) M5 Qwen2.5-14B burst, cost-gated ~$25–45, off critical path.

_(Housekeeping done: stopped pods deleted; GitHub tokens revoked. RunPod `list-pods` empty as of 2026-08-06.)_

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
- **Revision deadline / EDAS format** — confirm in Phase 0 (user action).
- **Page budget** — current draft 7 pages; target ~8 (provisional); confirm CARS 2026 limit before integration.
- RunPod create-pod has no startup cmd → pods driven over SSH; MCP verified 2026-08-06.

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
