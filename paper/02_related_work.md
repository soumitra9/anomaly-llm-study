# Related work (draft — framing only)

**LLMs for tabular anomaly detection.** *AnoLLM* (Tsai et al., ICLR 2025) fine-tunes small language models
(SmolLM-135M/360M) and scores rows by mean negative log-likelihood over random column permutations, reporting
competitiveness with classical detectors on ODDS. It does **not** run a same-model likelihood-vs-prompted
comparison, does not sweep open-weight model scale for *prompted* scoring, and evaluates primarily by AUROC
rather than fixed-FPR operational metrics. *AD-LLM* (Yang et al., ACL Findings 2025) and related studies find
contemporary LLMs often underperform classical methods — motivating our operating-regime framing rather than a
"gap closed" claim.

**Tabular serialization / generative tabular models.** *GReaT* and *TabLLM* serialize rows to text for
generation/classification; we reuse row serialization but study *anomaly scoring* and treat serialization
**order** as an explicit variable (RQ5), connecting to *CausalTAD*'s claim that column order matters — though
we test only whether a domain-informed order helps, **not** CausalTAD's causal-discovery mechanism.

**Benchmarks and classical/deep baselines.** *ADBench* and the ODDS library standardize datasets and the
classical+deep baseline panel (IForest, PCA, kNN, ECOD; DeepSVDD, RCA, SLAD, GOAD, NeuTraL, ICL, DTE, REPEN),
which we adopt for comparability.

**What is new here.** To our knowledge no prior work provides (i) a same-model, open-weight
likelihood-vs-prompted A/B, (ii) an evaluation under extreme imbalance and fixed-FPR alert budgets on security
data, and (iii) a constructive classical→LLM two-stage triage result. We position the paper as replication +
extension, stated plainly.
