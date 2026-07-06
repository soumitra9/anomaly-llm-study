# RunPod fleet — CURRENT: M3.5 confound checks (pending) / M4 (next)

## Active
No active pods. M3 pod stopped 2026-07-05. M3.5 pod to be spun up next.

## M3.5 plan (pending)
Single A40 pod. DA1: 30 da1_dissolving cells (instruct+LoRA likelihood on ODDS × 3 seeds).
BA1: classical-only local re-run on binned creditcard. Estimate ~$3–5.

---
## Archived — M3 Exp-3/3b (✅ COMPLETE 2026-07-05)

1× A40 (`l2css8jckkkp0q`, CA-MTL-1, **$0.44/hr**). Uptime 29.6 h → **$13.03**.

| Pod | RunPod ID | result | cells |
|---|---|---|---|
| m3cc | `l2css8jckkkp0q` | ✅ COMPLETE | 60 exp3_security + 6 exp3b_names |

All 66 cells rsync'd and verified (status=complete). Logs in `results/logs/fleet/m3/`.
Pod stopped; disk persists (delete via MCP when M3.5 pod launched on fresh image).

## Merge → analysis
rsync pod `/workspace/results/raw/{exp3_security,exp3b_names}/` → local; expect 60 + 6 JSONs →
operational-metric tables, RQ4 bootstrap CIs, RQ3b ΔAUROC CI (no CD diagram — only 2–3 datasets).

---
## Archived — M2 Exp-2 fleet (360 cells, 2026-07-01 → 2026-07-04, COMPLETE)

6× A40, $2.64/hr total, $90.42 real billing. All pods torn down. Backup:
`results/backups/exp2_odds_FINAL_360cells.tgz`. Fleet scripts: `scripts/exp2_fleet.py`, `fleet_pull.sh`,
`fleet_watch.sh`, `pod_bootstrap.sh`. See git history / `RUNLOG.md` for pod IDs and recovery notes.

## Archived — M1 gate fleet (90 cells, 2026-06-30, COMPLETE)

5× A40, ~$21. See git history at commit `9470ec8`.
