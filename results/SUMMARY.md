# Results summary (local system of record)

Derived from `results/raw/` per-cell JSONs. Regenerate tables via `uv run python scripts/make_tables.py`; stats via `uv run python scripts/m6_stats.py`.

_Last updated: 2026-08-07 (Revision Phase compute + Phase 4 analysis complete)._

## Project spend

| Phase | Cost |
|-------|------|
| M1–M6 (through Jul 2026) | $141.41 |
| Revision pod `1y91hqyjou9pkx` (~27.8 h × $0.44/hr) | ~$12.21 |
| **Total** | **~$153.62** |

## §RV1 — UNSW likelihood (`exp3_security`)

Qwen2.5-3B base+LoRA, r=5, max_steps=1000, seeds 0–2.

| Seed | AUPRC gain | recall@1%FPR | wall (h) |
|------|------------|--------------|----------|
| 0 | 7.17 | 0.273 | 5.0 |
| 1 | 7.67 | 0.309 | 5.0 |
| 2 | 8.22 | 0.324 | 5.3 |

M3 prompted UNSW seed0 (reference): gain 3.99, recall@1%FPR 0.148.

## §RV2 — Few-shot prompted (`exp2_fewshot`)

Qwen2.5-3B-Instruct, k=3 normals-only exemplars, 8 DA1 ODDS datasets × 3 seeds = 24 cells.

### Mean AUROC by scoring mode (8 datasets)

| Mode | Mean AUROC |
|------|------------|
| Zero-shot prompted (M2) | 0.468 |
| Few-shot prompted (RV2) | 0.759 |
| Likelihood (M2) | 0.773 |

Mean ΔAUROC (few-shot − zero-shot) = **+0.290** (24 cells). Gap closure vs zero-shot→likelihood: **~95%**. Surviving gap (likelihood − few-shot): **0.014** mean AUROC.

### Significance (primary, n=8 dataset means)

| Test | p | Reject @0.05 | Interpretation |
|------|---|--------------|----------------|
| Wilcoxon (few-shot vs likelihood) | **0.641** | No | Statistically indistinguishable; underpowered at n=8 (min p≈0.008) |
| Sensitivity (n=24 cells, non-independent) | 0.317 | No | Footnote only; seeds not independent |

Supports narrowing M2 headline to **zero-shot expected-value prompting**.

### Protocol comparability (seed0, 8 datasets)

PASS on: `dataset_content_hash`, `serialization_template_hash`, `split_index_hash`, `n_rows_scored`, `decode_config.n_levels`. Hygiene: few-shot cells have `git_sha`=null (not a confound).

### Per-dataset (mean over 3 seeds)

| Dataset | Zero-shot | Few-shot | Likelihood | Δ(few−zero) |
|---------|-----------|----------|------------|-------------|
| arrhythmia | 0.558 | 0.711 | 0.821 | +0.152 |
| breastw | 0.180 | 0.943 | 0.990 | +0.763 |
| cardio | 0.429 | 0.736 | 0.853 | +0.307 |
| ionosphere | 0.390 | 0.937 | 0.941 | +0.547 |
| shuttle | 0.749 | 0.989 | 1.000 | +0.240 |
| speech | 0.579 | 0.484 | 0.469 | −0.095 |
| vertebral | 0.688 | 0.470 | 0.375 | −0.218 |
| yeast | 0.173 | 0.799 | 0.738 | +0.626 |

## Phase 4 analysis artifacts (local)

Regenerate with `PYTHONPATH=. uv run python scripts/make_tables.py exp3_security exp2_fewshot`, then `m6_stats.py` and `make_figures.py`.

| Artifact | Path |
|----------|------|
| UNSW security table (incl. 3 likelihood rows) | `results/tables/exp3_security.csv` |
| Few-shot ODDS table | `results/tables/exp2_fewshot.csv` |
| Stats JSON (§RV1 + §RV2 keys) | `results/tables/m6_stats.json` |
| RV2 grouped bar figure | `results/figures/rv2_fewshot_vs_zeroshot.png` |
| RV1 UNSW figure | `results/figures/rv1_unsw_likelihood.png` |

Protocol check (Step 2): breastw seed0 few-shot vs zero-shot — same `dataset_content_hash`, `serialization_template_hash`, `split_index_hash`; only `n_shots=3` differs.

## Backups

- Latest revision backup: `results/backups/revision_20260807T212210Z.tgz` (27 cells: 3 RV1 + 24 RV2)

## Open decision

Few-shot closes ~95% of the zero-shot→likelihood gap; surviving 0.014 AUROC gap is **not statistically significant** (Wilcoxon p=0.641, n=8). Pre-registered framing (`GATE_SPEC.md` §RV2) supports **narrowing the M2 headline to zero-shot expected-value prompting**. Regressions on speech/vertebral are descriptive nuance (shape extremes at n=8).
