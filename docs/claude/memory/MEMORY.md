# Memory Index

- [Project state](project-state.md) — CURRENT (2026-07-05): M1 + M2 COMPLETE. **M3 RUNNING** on RunPod `anomaly-m3-cc` (20/60 exp3_security on-pod, 0 failures). Project spend ≈$118. See repo `ROADMAP.md` + `FLEET.md`.

- [User profile](user-profile.md) — Autodesk researcher leading an anomaly-detection replication+extension paper
- [AnoLLM verified facts](anollm-verified-facts.md) — primary-source corrections to project_idea.md's assumptions about AnoLLM
- [Project premise correction](project-premise-correction.md) — the brief's "open LLMs lost to classical" framing is not what AnoLLM actually found
- [Related work verified](related-work-verified.md) — AD-LLM and CausalTAD verified against primary sources
- [Compute constraint](compute-constraint.md) — no local GPU; hosted-API + small-CPU split, or rent cloud GPU; model lineup
- [Kaggle MCP](kaggle-mcp.md) — official Kaggle MCP connected; data download, GPU kernels, model weights
- [RunPod cost guardrail](runpod-cost-guardrail.md) — NEVER spin up/charge RunPod without asking the user TWICE
- [ODDS special datasets](odds-special-datasets.md) — arrhythmia/mulcross/seismic are NOT in adbench; Stony Brook ODDS site is TLS-broken → use shebuti.com (arrhythmia Dropbox), OpenML, UCI; staged by scripts/fetch_special_datasets.sh; arrhythmia MUST be 452×274/66 (ODDS), not DAMI 450×259
