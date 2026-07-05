---
name: kaggle-mcp
description: "Official Kaggle MCP is connected/authenticated — data download, GPU kernels, model weights"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 35bb7932-d37b-41f7-8f2b-bc3261e91022
---

The official Kaggle MCP (`mcp__kaggle__*`) is connected and authenticated in this project (confirmed 2026-06-29). Key tools for the anomaly-detection project:

- **Data:** `get_dataset_info`, `get_dataset_files_summary`/`list_dataset_files` (column metadata without downloading), `download_dataset(ownerSlug, datasetSlug, datasetVersionNumber, hashLink)` — version-pinned + hashable. Credit Card Fraud = `mlg-ulb/creditcardfraud`, **pin version 3**, single `creditcard.csv` ~150MB, 31 cols, license ODbL, 492/284,807 = 0.172%.
- **Competitions (separate API):** `get_competition`, `get_competition_data_files_summary`, `download_competition_data_files` — for IEEE-CIS = `ieee-fraud-detection`.
- **Compute:** `get_accelerator_quota` confirms **30 GPU-h/week** (108,000s; TPU 20h; weekly refresh). `create_notebook_session` (machineShape=GPU, dockerImage, enableInternet) + `get_notebook_session_status` + `download_notebook_output` + `cancel_notebook_session` → scriptable Kaggle GPU for the Exp-1 reproduction smoke-test.
- **Model weights:** `download_model_variation_version` (frameworks incl. vLLM/Transformers/GGUF) — HF fallback for SmolLM/Qwen/Gemma/Phi.
- ODDS is NOT on Kaggle (AnoLLM repo / Stony Brook); UNSW-NB15 via nids-datasets. Can mirror ODDS .mat to our own Kaggle Dataset via `upload_dataset_file`.

Wired into PLAN.md §2d, §9, §10. See [[compute-constraint]].