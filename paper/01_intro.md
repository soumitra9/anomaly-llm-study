# Introduction (draft — framing only)

Tabular anomaly detection underpins fraud, intrusion, and fault monitoring, and classical detectors
(Isolation Forest, kNN, ECOD) remain strong, cheap baselines. Recent work asks whether large language models
can detect anomalies over serialized tabular rows. AnoLLM (Tsai et al., ICLR 2025) showed that small language
models scoring rows by **likelihood** are competitive on the ODDS benchmark, while AD-LLM and others report
that contemporary LLMs still **underperform** classical methods in many settings. The state of the field is
therefore not "the gap has closed" but a more precise, unresolved question:

> **Under what operating regime — model scale, scoring mode, data semantics, imbalance, and alert budget —
> do open-weight LLMs help for tabular anomaly detection, and where do classical detectors still dominate?**

We address this as an **honest replication and extension** of AnoLLM, not a new detector. Our contributions:

1. **A controlled, same-model likelihood-vs-prompted A/B on open-weight models.** Prior work conflates model
   choice with scoring method. We hold the model weights fixed and vary only the scoring mode — (A) negative
   log-likelihood over column permutations vs (B) a prompted, continuous *expected-value* score over verbalizer
   tokens — isolating the effect of the scoring mechanism (RQ2, RQ3).
2. **Re-evaluation under realistic operating conditions on security data** — extreme class imbalance and
   **fixed-false-positive-rate** budgets on credit-card fraud and UNSW-NB15 — where AUROC alone is misleading
   (RQ4), plus a semantic-column-name ablation (RQ3b) and a serialization-order ablation (RQ5).
3. **A constructive two-stage result**: even where LLMs are weak *standalone*, a cheap classical detector
   followed by an LLM re-ranker can improve the operating point at a fixed alert budget (RQ7).

We first reproduce AnoLLM within a pre-registered tolerance (RQ1) to validate the pipeline, then report where
modern small open models and prompted scoring change the picture — and, importantly, where they do not.
