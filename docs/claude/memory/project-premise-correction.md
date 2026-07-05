---
name: project-premise-correction
description: "The brief's motivating premise (\"open LLMs lost to classical detectors\") is not what AnoLLM actually found"
metadata: 
  node_type: memory
  type: project
  originSessionId: f0312d5f-9fe4-4ce2-a145-6b443f9d0b23
---

project_idea.md §1 motivates the paper by saying the 2024/25 teams "found the open models LOST to the classical statistical tools." Verified against primary sources, this is imprecise and must be reframed:

- **AnoLLM (tabular, ICLR 2025):** open small LLMs were COMPETITIVE — they WIN on the 6 mixed-type datasets (SmolLM-360M avg 0.810 AUROC vs best deep baseline ~0.746) and perform ON PAR with KNN/ICL/DTE on the 30 numerical ODDS sets. AnoLLM did not "lose."
- **AD-LLM (ACL Findings 2025):** this is the source of the more negative framing, but it is TEXT/NLP anomaly detection (news/spam/reviews), not tabular — so it doesn't directly support a claim about tabular numeric data.

**Why this matters:** the paper's "has the gap closed?" hook needs a precisely-stated baseline gap. The honest gap is narrower and more nuanced than "LLMs lost": LLMs already match/beat classical on mixed-type/semantic data, and tie on pure-numeric. The genuinely open questions are (a) whether MODERN models beat SmolLM at likelihood scoring given AnoLLM's finding that size didn't help, and (b) whether PROMPTED suspiciousness scoring (never tested by AnoLLM, and which DOES scale with instruction-tuning) changes the picture, especially on semantically-rich security data.

**How to apply:** rewrite §1/§9 framing to state the real prior finding. Note AnoLLM ALREADY covers fraud-ecommerce + vehicle-insurance-fraud, so the security novelty rests on (1) extreme-imbalance credit-card fraud (~0.17%), (2) network intrusion (NSL-KDD/UNSW-NB15), (3) prompted scoring mode, (4) operational metrics. See [[anollm-verified-facts]].
