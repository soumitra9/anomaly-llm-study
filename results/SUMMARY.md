# Results SUMMARY — Anomaly-Detection LLM Study (collated)

Single source of truth for everything run so far. Regenerate/refresh at the end of each milestone.
Per-cell JSON under `results/raw/<exp>/` is the machine system-of-record; this is the human digest.
Last updated: 2026-07-04 · git `c130526`.

## Project spend to date ≈ **$112** (RunPod A40 SECURE @ $0.44/hr)
| Milestone | Cost | Note |
|---|---|---|
| M1 gate | ~$21 | 90 cells + config tests |
| D0 calibration | ~$0.65 | 1 pod, chose Qwen max_steps=1000 |
| M2 Exp-2 | **$90.42** | real billing; ~35% over est (Qwen r=10 on 280k-row test sets) |
| **M3 (next)** | est ~$10 (cap $25) | not yet run |

---

## M1 — Reproduction gate (RQ1) · COMPLETE (90/90 cells)
SmolLM-360M, likelihood, 30 ODDS × 3 splits, r=10. Verdict vs pre-registered `GATE_SPEC.md`:
- **C1 mean PASS** — ours 0.8505 vs published 0.865 (Δ 0.0145 ≤ 0.02)
- **C2 rank PASS** — Spearman 0.8754 ≥ 0.80
- **C3 band 19/30** (need 24) — root-caused to a **code-vs-paper difference in the released fork** (NOT our
  error; controlled effective-batch test refuted the config hypothesis). Hard-stop is C1/C2 only → not triggered.
- **Verdict: credible PARTIAL reproduction. No re-gate (proven futile).**
- Artifacts: `results/raw/exp1_repro/*.json` (90), `results/tables/exp1_repro.csv`.

## M2 — Exp 2 same-model A/B: likelihood vs prompted, scale (RQ2, RQ3) · COMPLETE (360/360 cells)
[smol-360, Qwen2.5-3B] × [likelihood, prompted] × 30 ODDS × 3 seeds. SmolLM @2000 steps, Qwen @1000 (D0).
- Mean AUROC: smol-L **0.843**, qwen-L **0.859**, smol-P **0.610**, qwen-P **0.493**.
- **Friedman p=6e-12.** Avg ranks (lower=better): smol-L 1.62, qwen-L 1.65 (tied, within CD=0.856),
  smol-P 3.20, qwen-P 3.53.
- **RQ2 (scoring mode) — likelihood ≫ prompted, both models:** Holm-Wilcoxon smol Δ+0.276 (p=4.7e-8),
  qwen Δ+0.354 (p=2.6e-7); both reject H0.
- **RQ3 (scale) — NO significant gain:** Qwen-3B vs SmolLM-360M on likelihood Δ≈0.000, p_holm=0.77 (fail to reject).
- Artifacts: `results/raw/exp2_odds/*.json` (360), `results/tables/exp2_odds.csv`,
  `results/figures/exp2_cd_diagram.png`, backup `results/backups/exp2_odds_FINAL_360cells.tgz`.

## M3 — Security transfer (RQ4) + semantic names (RQ3b) · PLANNED (approved), not started
Complete Exp 3 (credit-card temporal+random + UNSW; prompted+classical both, likelihood on credit-card) +
Exp 3b (pima semantic-vs-anon), on smol-360 + Qwen2.5-3B. Est ~$10 (cap $25). Gated on Pima UCI-order check.
See plan file `~/.claude/plans/i-need-to-plan-ancient-dawn.md` (★★ POST-M2 section).

## Later — M4 (Exp 4/5/6, ~free) → M5 (opt Qwen3-14B A100 burst) → M6 (final stats) → paper
