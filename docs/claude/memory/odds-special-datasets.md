---
name: odds-special-datasets
description: How to source the 3 ODDS datasets NOT in adbench (arrhythmia/mulcross/seismic) — the Stony Brook ODDS site is TLS-broken
metadata: 
  node_type: memory
  type: reference
  originSessionId: 8c9d4f79-f597-4246-85b1-d42821895efe
---

The AnoLLM gate uses 30 ODDS datasets. **27 come from the adbench bundle** (jihulab mirror, auto-downloaded by
the fork on first `load_data`). **3 are NOT in adbench** and the fork (`third_party/AnoLLM/src/data_utils.py`)
requires manual files: **arrhythmia, mulcross, seismic**. Verified against the complete 47-file adbench
Classical listing — these 3 are genuinely absent (do NOT assume adbench ships arrhythmia; it does not).

**Source change (2026-06-30):** the fork points to `odds.cs.stonybrook.edu`, but that host's **TLS cert is
broken (`HANDSHAKE_FAILURE`)** — effectively dead. Maintainer Shebuti Rayana mirrors ODDS at **shebuti.com**.
Working sources, all wired into **`scripts/fetch_special_datasets.sh`** (idempotent, verifies each):
- **arrhythmia.mat** → `https://www.dropbox.com/s/lmlwuspn1sey48r/arrhythmia.mat?dl=1` (off shebuti.com/arrhythmia-dataset/). Keys `X`,`y`.
- **mulcross.arff** → OpenML data_id 40897 (`https://www.openml.org/api/v1/json/data/40897` → `.url`).
- **seismic-bumps.arff** → UCI `https://archive.ics.uci.edu/ml/machine-learning-databases/00266/seismic-bumps.arff`.

**arrhythmia disambiguation (critical):** use the **ODDS** version = **X 452×274, 66 outliers (14.6%)**. There is
a different DAMI/Goldstein arrhythmia (450×259, 45.8%) — WRONG for AnoLLM reproduction. The fetch script asserts
452×274/66 and refuses the wrong file. (Confirmed correct on pod B, 2026-06-30.)

**Fleet gotcha:** on a fresh pod, the gate's first datasets can race the ~6-min adbench bulk download
(FileNotFound). Either pre-run the download to completion, or re-run the gate after (it skips complete cells).
