# RunPod fleet — CURRENT: M3.5 confound checks (pending) / M4 (next)

## Active — M3.5 DA1 pod

| Pod | RunPod ID | SSH | role | cells |
|---|---|---|---|---|
| **m35da1** | `xbga2ae1dqfp12` | 69.30.85.58:22004 | DA1 dissolving arm (8 cells) | 8 |

**Config:** 1× A40 SECURE, $0.44/hr, CA-MTL-1. Launched 2026-07-06 02:39Z.
**Cmd:** `uv run python -m anodet.eval.exp2 --config configs/da1_dissolving.yaml --device cuda --results-root /workspace/results --max-steps 1000 --r 5`
**Log:** `/workspace/results/logs/m35_da1.log`. Results → `/workspace/results/raw/da1_dissolving/`.
**ETA:** ~4–8 h (8 cells × ~30–60 min each; speech 400-feature = slow).
**Teardown:** stop after all 8 cells done + rsync verified. Evaluate DA1 against GATE_SPEC §DA1.

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
