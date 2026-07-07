# Results INDEX — artifact map

Machine system-of-record = per-cell JSON under `raw/<exp>/`. Human digest = `SUMMARY.md`.
Last updated: 2026-07-07 · git `51cfb0a`.

## Raw per-cell results (`results/raw/`)
| Experiment | Path | Cells | Status |
|---|---|---|---|
| M1 gate | `raw/exp1_repro/*.json` | 90 | ✅ complete |
| M2 Exp-2 A/B | `raw/exp2_odds/*.json` | 360 | ✅ complete |
| M3 Exp-3 security | `raw/exp3_security/*.json` | 60 | ✅ complete |
| M3 Exp-3b names | `raw/exp3b_names/*.json` | 6 | ✅ complete |
| M3.5 DA1 dissolving | `raw/da1_dissolving/*.json` | 8 | ✅ PASS (|Δ|=0.0054) |
| M4 Exp-4 ordering | `raw/exp4_serialization/*.json` | 24 | ✅ complete |
| M4 Exp-6 triage | `raw/exp6_triage/*.json` | 9 | ✅ complete |

## Tables (`results/tables/`)
| File | Contents |
|---|---|
| `exp1_repro.csv` | M1 per-dataset AUROC (mean±std over splits) vs published |
| `exp2_odds.csv` | M2 per (dataset, model, mode) metrics (mean±std over seeds) |
| `exp3_security.csv` | M3 security transfer metrics (all modes, all datasets) |
| `exp3_security_notime.csv` | M3 classical creditcard drop-Time corrected (T3 fix) |
| `exp3b_names.csv` | M3b semantic vs anon column names on pima |
| `da1_dissolving.csv` | M3.5 DA1 dissolving arm per-dataset AUROC |
| `ba1_binned_creditcard.csv` | M3.5 BA1 binned-creditcard ablation |
| `exp4_serialization.csv` | M4 Exp-4 AUROC by column ordering (pima + UNSW) |
| `exp5_pareto.csv` | Exp-5 Pareto (AUROC vs wall-time/1k rows) |
| `exp6_triage.csv` | M4 Exp-6 two-stage triage results by k% |
| `m6_stats.json` | M6 machine-readable stats for all RQs (Friedman, Holm-Wilcoxon, descriptives) |

## Figures (`results/figures/`)
| File | Contents |
|---|---|
| `exp2_cd_diagram.png` | M2 Friedman/Nemenyi critical-difference diagram (4 methods × 30 datasets) |
| `exp5_pareto.png` | Exp-5 Pareto scatter (AUROC vs cost/1k rows) |
| `exp3_security_bars.png` | RQ4 security: recall@1%FPR by method/dataset |
| `exp4_ordering.png` | RQ5 ordering sensitivity: AUROC by column ordering, pima vs UNSW |

## Backups (`results/backups/`) — write-once snapshots
| File | Contents |
|---|---|
| `exp2_odds_FINAL_360cells.tgz` | M2 complete 360-cell snapshot |
| `exp2_odds_snapshot_321cells.tgz` | M2 in-progress snapshot (superseded) |

## Cost records
| File | Contents |
|---|---|
| `exp2_cost.json` | M2 RunPod billing breakdown ($90.42) |

## Logs (`results/logs/fleet/`)
| Dir | Contents |
|---|---|
| `fleet/m3/` | M3 pod stdout logs (m3_sec.log, m3_run.log) |
| `fleet/p1/`–`p6/` | M2 fleet per-pod logs (run, qwen, smol) |
