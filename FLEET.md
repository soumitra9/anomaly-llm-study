# RunPod fleet — M1 gate (90 cells = 30 datasets × 3 splits), launched 2026-06-30

5× NVIDIA A40 (SECURE, $0.44/hr each = **$2.20/hr total**). All at commit **d2b6061** (scoring fix).
Disjoint dataset partition → per-cell JSONs union with zero conflict. Each subset = 6 datasets × 3 splits = **18 cells**.
SSH key: `~/.ssh/id_ed25519_runpod_anomaly`. User `root`. Log per pod: `results/logs/gate_<POD>.log`.

| Pod | RunPod ID | SSH | datasets (6) | cells |
|---|---|---|---|---|
| **E** | h9iuwe1gsjp7su | 194.68.245.198:22046 | ionosphere, cardio, lymphography, http, smtp, mulcross | 18 |
| **A** | uxt0erpkqv8qfd | 69.30.85.213:22174 | speech, wbc, pima, yeast, ecoli, glass | 18 |
| **B** | er3e8xiq3y0jd8 | 69.30.85.138:22063 | arrhythmia, satellite, breastw, shuttle, thyroid, vertebral | 18 |
| **C** | xqfi5tpags89qe | 69.30.85.4:22076 | musk, satimage-2, mammography, annthyroid, seismic, heart | 18 |
| **D** | pnwq5rm0qvz2ry | 69.30.85.29:22003 | optdigits, letter_recognition, wine, vowels, covertype, pendigits | 18 |

LoRA (slow) datasets isolated one per pod: speech→A, arrhythmia→B, musk→C.

## Data-staging recovery (2026-06-30) — RESOLVED, automated
First launch surfaced two issues; both handled:
1. **Fresh-pod adbench race** (speech/satellite/annthyroid/mammography/musk/satimage-2/letter_recognition/optdigits
   FileNotFound'd before the ~6-min bulk download finished). Data present now → recovered by re-run.
2. **3 specials NOT in adbench** — staged via `scripts/fetch_special_datasets.sh`:
   arrhythmia→B (shebuti.com Dropbox mirror, verified ODDS 452×274/66), seismic→C (UCI), mulcross→E (OpenML).
**Auto-rerun watchers** attached to A/B/C/D: each waits (by gate PID) for the current pass to end, then
re-runs `kaggle_gate` (skips complete cells, retries failed — now all with data). Fleet self-heals to 90/90.

## Teardown (the instant a pod's 18 cells are done — never leave billing)
`stop-pod <id>` then `delete-pod <id>`. Confirm `list-pods` empty at the end.

## Merge
rsync each pod's `results/raw/exp1_repro/*.json` to local `results/raw/exp1_repro/` → 90 JSONs → verdict.
