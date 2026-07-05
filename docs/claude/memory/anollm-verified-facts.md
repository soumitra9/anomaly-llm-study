---
name: anollm-verified-facts
description: Primary-source facts about AnoLLM (ICLR 2025) that correct wrong assumptions in project_idea.md
metadata: 
  node_type: memory
  type: project
  originSessionId: f0312d5f-9fe4-4ce2-a145-6b443f9d0b23
---

Verified against the AnoLLM ICLR 2025 PDF (proceedings.iclr.cc, hash 165bbd0a...) on 2026-06-28.

**Backbone (CRITICAL correction):** AnoLLM uses **SmolLM-135M and SmolLM-360M** (Allal et al. 2024), NOT "Llama2/Mistral-7B-class" as project_idea.md §3 claims. A SmolLM-1.7B variant was tested via LoRA only.

**Size ablation (Table 3a):** Bigger is NOT better. ODDS AUC-ROC: 135M=0.884, 360M=0.865, 1.7B=0.861. Mixed-type: 135M=0.803, 360M=0.811, 1.7B=0.812. They explicitly chose small models because size didn't help. This undercuts the brief's implicit "swap in bigger 7B-70B models → better likelihoods" hypothesis for likelihood scoring.

**Scoring:** anomaly score = average negative log-likelihood over r=21 random column permutations (Eqn 5). Textual columns get per-column length normalization (Eqn 6); column-name tokens excluded. Numerical columns use standard rescaling + rounding ("standard" binning beat equal-width/quantile/language/no-binning at 0.884).

**Baselines (11):** classical = IForest, PCA, KNN, ECOD; deep = DeepSVDD, RCA, SLAD, GOAD, NeuTraL, ICL, DTE, REPEN. (project_idea.md §7's list is slightly off — no "RDP" or "DeepIsolationForest" in AnoLLM's main panel; baselines adapted from the DTE/DTE repo + PyOD/DeepOD.)

**Datasets:** 30 ODDS (98.5% numerical columns, only 10/30 have human-readable column names) + 6 mixed-type: Fake job posts, **Fraud ecommerce** (151k, 9.36% anomaly), Lymphography, Seismic, **Vehicle insurance fraud** (15k, 5.99%), 20 newsgroup.

**Protocol:** uncontaminated unsupervised; train = 50% of normals, test = rest + all anomalies; 5 seeds averaged; primary metric AUC-ROC (AUC-PRC/F1 in appendix).

See [[project-premise-correction]] and [[related-work-verified]].
