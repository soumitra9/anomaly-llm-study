# Data licenses, sources, and basis for use

No datasets are committed to this repo (`data/` is gitignored). Loaders re-fetch each dataset by a pinned
version and verify a content hash (recorded in each run's `RunMetadata`). This file records provenance and
license for every dataset used.

| Dataset | Source | Pinned version | License | Basis for use |
|---|---|---|---|---|
| **ODDS** (27 of 30 sets) | adbench bundle (jihulab mirror, via the AnoLLM fork) | per-file (record hash) | Academic use, citation required | Research replication of AnoLLM |
| **ODDS specials: arrhythmia, mulcross, seismic** (3 of 30 — NOT in adbench) | arrhythmia: shebuti.com Dropbox mirror; mulcross: OpenML id 40897; seismic: UCI 00266 | content hash; arrhythmia pinned to ODDS 452×274/66 | Academic use, citation required | Same; staged by `scripts/fetch_special_datasets.sh` |
| **Credit Card Fraud** | Kaggle `mlg-ulb/creditcardfraud` (via Kaggle MCP) | **v3** (2018-03-23) | **ODbL 1.0** (attribution + share-alike) | Research; not redistributed (re-fetched by loader) |
| **UNSW-NB15** | `nids-datasets` pkg / UNSW (research.unsw.edu.au) | record pkg version + content hash | Academic-use license, citation required | Research; not redistributed |
| **UCI Pima / Wisconsin Breast Cancer** (column NAMES only, for Exp 3b) | UCI ML Repository | — | Open, citation required | Recover semantic feature names to align onto ODDS `pima`/`breastw` column order |
| *IEEE-CIS Fraud (optional)* | Kaggle competition `ieee-fraud-detection` | — | Competition rules | Optional extension only |

Notes:
- **ODDS source change (2026-06-30):** the canonical `odds.cs.stonybrook.edu` host has a broken TLS cert
  (`HANDSHAKE_FAILURE`) and is effectively unreachable. The fork's `src/data_utils.py` still points there for
  arrhythmia/mulcross/seismic. The maintainer (Shebuti Rayana) mirrors ODDS at **shebuti.com**; arrhythmia.mat
  is the Dropbox link `https://www.dropbox.com/s/lmlwuspn1sey48r/arrhythmia.mat?dl=1` (off `shebuti.com/arrhythmia-dataset/`).
  27/30 ODDS sets come from adbench; **arrhythmia/mulcross/seismic are NOT in adbench** (verified against the
  complete 47-file adbench Classical listing) and are staged via `scripts/fetch_special_datasets.sh`.
- **arrhythmia disambiguation:** use the ODDS version (**452×274, 66 outliers, 14.6%**), NOT the DAMI/Goldstein
  version (450×259, 45.8%). The fetch script asserts the ODDS shape and refuses the wrong one.
- ODDS `.mat` files contain only `X` (matrix) + `y` (labels) — no column names. For the Exp 3b semantic
  ablation, names are recovered from the UCI originals (Pima, Wisconsin BC) and aligned to the `.mat`
  column order (verified Day-0 before coding).
- Each loader exposes `download() -> (path, version_id, content_hash)`; the content hash is stored in
  `RunMetadata` so a metric mismatch implicates code, not silent data drift.
