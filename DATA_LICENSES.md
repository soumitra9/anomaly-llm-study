# Data licenses, sources, and basis for use

No datasets are committed to this repo (`data/` is gitignored). Loaders re-fetch each dataset by a pinned
version and verify a content hash (recorded in each run's `RunMetadata`). This file records provenance and
license for every dataset used.

| Dataset | Source | Pinned version | License | Basis for use |
|---|---|---|---|---|
| **ODDS** (30 numeric sets, incl. `pima`, `breastw`, `wine`, `lympho`, …) | Stony Brook ODDS Library (odds.cs.stonybrook.edu) | per-file (record hash) | Academic use, citation required | Research replication of AnoLLM |
| **Credit Card Fraud** | Kaggle `mlg-ulb/creditcardfraud` (via Kaggle MCP) | **v3** (2018-03-23) | **ODbL 1.0** (attribution + share-alike) | Research; not redistributed (re-fetched by loader) |
| **UNSW-NB15** | `nids-datasets` pkg / UNSW (research.unsw.edu.au) | record pkg version + content hash | Academic-use license, citation required | Research; not redistributed |
| **UCI Pima / Wisconsin Breast Cancer** (column NAMES only, for Exp 3b) | UCI ML Repository | — | Open, citation required | Recover semantic feature names to align onto ODDS `pima`/`breastw` column order |
| *IEEE-CIS Fraud (optional)* | Kaggle competition `ieee-fraud-detection` | — | Competition rules | Optional extension only |

Notes:
- ODDS `.mat` files contain only `X` (matrix) + `y` (labels) — no column names. For the Exp 3b semantic
  ablation, names are recovered from the UCI originals (Pima, Wisconsin BC) and aligned to the `.mat`
  column order (verified Day-0 before coding).
- Each loader exposes `download() -> (path, version_id, content_hash)`; the content hash is stored in
  `RunMetadata` so a metric mismatch implicates code, not silent data drift.
