---
name: related-work-verified
description: AD-LLM and CausalTAD verified against primary sources
metadata: 
  node_type: memory
  type: reference
  originSessionId: f0312d5f-9fe4-4ce2-a145-6b443f9d0b23
---

Verified 2026-06-28.

**AD-LLM** — Yang et al., ACL Findings 2025 (arxiv 2412.11142; aclanthology 2025.findings-acl.79). Benchmarks LLMs for anomaly detection on **TEXT/NLP** data across three tasks: zero-shot detection, data augmentation, model selection. Models: GPT-4, Llama 3.1. NOT tabular — cite as related work, don't fork. Repo: github.com/USC-FORTIS/AD-LLM (MIT).

**CausalTAD** — "Injecting Causal Knowledge into LLMs for Tabular Anomaly Detection," arXiv:2602.07798 (Feb 2026). Confirmed real. Two modules: (1) **causal-driven column ordering** (modeled as a linear ordering problem) and (2) **causal-aware column reweighting** (weight columns by causal strength). Reports avg AUC-ROC ~0.80 → 0.83 on six benchmarks; experiments across 30+ datasets; claims to beat SOTA. NOTE: project_idea.md §8 Experiment 4 only tests column ORDERING — CausalTAD's full method also includes reweighting, so cite precisely. Likely builds on AnoLLM-style serialization (uses same column-permutation serialization framing).

**Li et al. 2024 — "Anomaly Detection of Tabular Data Using LLMs"** (arXiv 2406.16308; IJCAI 2024). CRITICAL prior work for novelty defense. Does ZERO-SHOT / prompted **batch-level** tabular anomaly detection on ODDS with GPT-4 (finds outliers within a presented batch), plus a synthetic-data fine-tuning strategy. Finds GPT-4 on par with SOTA transductive methods. => Prompted tabular anomaly scoring is NOT new. Our defensible differentiation: per-row (not batch-level) scoring, OPEN-WEIGHT (not GPT-4), a controlled same-model A/B vs likelihood scoring, and security/operational metrics. Must cite and differentiate explicitly.

Other must-cite related work: AD-LLM (text, prompted); **TabLLM** (Hegselmann AISTATS 2023, serialize rows->text for LLM zero/few-shot — basis of "feature names carry meaning"); **GReaT** (Borisov ICLR 2023, LLM tabular gen via serialization+permutation — AnoLLM's NLL/permutation lineage); **ADBench** (Han NeurIPS 2022, standard tabular AD benchmark); June 2026 blog "Zero-Shot Anomaly Detection with LLMs: How GPT-4 Performs on Tabular Data"; "LLM as an Algorithmist" arXiv 2510.03904 (may pre-empt the scaling claim — check). mala-lab/Awesome-Anomaly-Detection-Foundation-Models = curated list.

See [[anollm-verified-facts]].
