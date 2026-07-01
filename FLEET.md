# RunPod fleet — M2 Exp-2 (360 cells), launched 2026-07-01

6× NVIDIA A40 (SECURE, $0.44/hr each = **$2.64/hr total**). Base commit 9207575 + scp'd overlay
(`scripts/exp2_fleet.py`, `configs/qwen_hparams.yaml`, `anodet/scoring/prompted.py` — the push to main was
gated). SSH key `~/.ssh/id_ed25519_runpod_anomaly`, user `root`. Per-pod logs `/workspace/results/logs/`.

**Config:** each pod runs `exp2_fleet` twice — `smol-360 --max-steps 2000`, then `qwen2.5-3b --max-steps 1000`
(D0: 2000 over-trains Qwen; 1000 gives AUROC 0.841≥0.831 @ 3× less cost). Both modes (likelihood,prompted),
seeds 0,1,2, r=10. Disjoint dataset shards → per-cell JSON keys never collide → merge = union.
Grid = 2 models × 2 modes × 30 datasets × 3 seeds = **360 cells** (60 per pod).

| Pod | RunPod ID | SSH | shard (5 datasets) | slow set |
|---|---|---|---|---|
| **p1** | hr8ihfg9w4ihfw | 69.30.85.101:22032 | breastw, ecoli, wine, cardio, speech | speech |
| **p2** | bpsq1knsn60j2b | 69.30.85.58:22122  | lymphography, vertebral, wbc, yeast, arrhythmia | arrhythmia |
| **p3** | exrvejc9u6h4rb | 69.30.85.39:22066  | heart, glass, ionosphere, letter_recognition, musk | musk |
| **p4** | f5qxg5awcvdqoe | 69.30.85.25:22117  | pima, pendigits, satimage-2, satellite, mammography | — |
| **p5** | 0muthcvex9zzky | 69.30.85.41:22166  | thyroid, vowels, seismic, optdigits, shuttle | — |
| **p6** | dmv1g23myuqdf7 | 69.30.85.16:22157  | annthyroid, smtp, http, mulcross, covertype | — |

Wide/slow LoRA sets isolated one per pod: speech→p1, arrhythmia→p2, musk→p3.

**p3 heart special-handling (2026-07-01):** heart (267×44) at batch 32 ground extremely slowly (~36GB, ~40+min/cell)
and stalled p3. Fix: p3 runs glass/ionosphere/letter_recognition/musk at normal batch, then **heart in a
separate invocation at `--batch-size 4`** (bounds memory + speeds per-step). If heart still misbehaves at bs4,
isolate + investigate its max_length; the other 48 p3 cells are unaffected.

## Checkpointing / recovery (the durable-record guarantee)
- **Local puller** `bash scripts/fleet_pull.sh 300` (running locally, reads `/tmp/fleet_pods.txt`): every 5 min
  rsyncs each pod's `/workspace/results/raw/exp2_odds/` → local `results/raw/exp2_odds/` (3 retries/pod).
  **Local is the system of record** — completed cells survive any pod/balance loss.
- **Resume after a pod dies / balance runs out:** add balance → re-provision the pod → scp bootstrap + tarballs
  → `bash pod_bootstrap.sh "<that pod's shard>" none` (idempotent, verifies loads) → **rsync local results UP**
  to `/workspace/results/raw/exp2_odds/` → re-launch the same two `exp2_fleet` commands. `is_complete` skips
  done cells → zero double-compute.
- **Data staging = GOLDEN bundle** `/tmp/data_golden.tgz` (all 30 datasets pre-built + specials; 48M). Bootstrap
  extracts it into `data/` — deterministic, no adbench download race, no per-pod special fetch. Proven 30/30 load.

## Teardown (the instant a pod's shard 60 cells are done + rsynced — never idle-bill)
`delete-pod <id>`; confirm `list-pods` empty at the end. Write cost.json + RUNLOG entry.

## Merge → analysis
rsync all 6 pods → local; dedupe by cell key (filename); expect **360** JSONs → `make_tables` (aggregate) →
`stats` (Friedman/Nemenyi CD + Holm-Wilcoxon RQ2/RQ3) → `figures`.

---
_M1 gate fleet (5×A40, 90 cells, 2026-06-30) archived in git history at commit 9470ec8._
