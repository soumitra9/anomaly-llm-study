# RunPod fleet — M3 Exp-3/3b (security + semantic names), launched 2026-07-04

1× NVIDIA A40 (SECURE, **$0.44/hr**). SSH key `~/.ssh/id_ed25519_runpod_anomaly`, user `root`.
Log: `/workspace/results/logs/m3_sec.log`. Pod list for local tools: `/tmp/fleet_pods.txt`.

**Config:** single pod runs the full security grid via `exp3_fleet` (all task-datasets × all modes × seeds 0–2),
then `exp3b_run` (6 cells). Qwen likelihood uses **r=5** (cost lever). Classical cells are CPU-side within the
same runner. Grid = **60** `exp3_security` cells + **6** `exp3b_names` cells = **66** total.

| Pod | RunPod ID | SSH | role | cells |
|---|---|---|---|---|
| **m3cc** | `l2css8jckkkp0q` | 69.30.85.16:22015 | full Exp-3 grid (+ Exp-3b pending) | 60 + 6 |

**Progress (2026-07-05 ~10:00Z):** 20/60 `exp3_security` on-pod, **0 failures**. `creditcard-temporal` nearly
done (Qwen likelihood seed2 in progress). Remaining: `creditcard-random` (20 cells), `unsw` (20 cells).
`exp3b_names`: not started. `shard.done`: not yet. GPU ~100%, ~14 h uptime (~$6 accrued).

**Launch command (on pod):**
```bash
uv run python -m scripts.exp3_fleet \
  --task-datasets all --models smol-360,qwen2.5-3b \
  --modes likelihood,prompted,classical --seeds 0,1,2 --r 5 \
  --device cuda --results-root /workspace/results
```

**Cell breakdown (`exp3_security`):**
- Likelihood (Qwen only, credit-card temporal+random): 6 GPU cells
- Prompted (both models, all 3 tasks): 18 GPU cells
- Classical (iforest/pca/knn/ecod, all 3 tasks): 36 CPU cells

**Data staging:** M3 golden bundle (`scripts/build_m3_bundle.sh` → `/tmp/m3_data_golden.tgz`):
`creditcard.csv` + `unsw.parquet` + `pima/` ODDS cache.

## Teardown (only after shard.done + exp3b + rsync verify)
`delete-pod l2css8jckkkp0q`; confirm `list-pods` empty. Write `exp3_cost.json` + RUNLOG entry.

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
