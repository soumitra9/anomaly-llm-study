# Results INDEX — artifact map

Machine system-of-record = per-cell JSON under `raw/<exp>/`. Human digest = `SUMMARY.md`.
Last updated: 2026-07-05 · git `94d2c42`.

## Raw per-cell results (`results/raw/`)
| Experiment | Path | Cells |
|---|---|---|
| M1 gate | `raw/exp1_repro/*.json` | 90 (local) |
| M2 Exp-2 A/B | `raw/exp2_odds/*.json` | 360 (local) |
| M3 Exp-3 security | `raw/exp3_security/*.json` | 20/60 (on-pod; pull pending) |
| M3 Exp-3b names | `raw/exp3b_names/*.json` | 0/6 (on-pod; not started) |

## Tables (`results/tables/`)
| File | Contents |
|---|---|
| `exp1_repro.csv` | M1 per-dataset AUROC (mean±std over splits) vs published |
| `exp2_odds.csv` | M2 per (dataset, model, mode) metrics (mean±std over seeds) |

## Figures (`results/figures/`)
| File | Contents |
|---|---|
| `exp2_cd_diagram.png` | M2 Friedman/Nemenyi critical-difference diagram (4 methods × 30 datasets) |

## Backups (`results/backups/`) — immutable per-milestone snapshots
| File | Contents |
|---|---|
| `exp2_odds_FINAL_360cells.tgz` | M2 complete 360-cell snapshot |
| `exp2_odds_snapshot_321cells.tgz` | M2 in-progress snapshot (superseded by FINAL) |

## Cost records
| File | Contents |
|---|---|
| `exp2_cost.json` | M2 RunPod billing breakdown ($90.42) |

## Logs (`results/logs/fleet/<pod>/`)
Per-pod stdout for the M2 fleet (p1–p6): train_runtime timings, OOM-retry events, per-cell AUROCs.
