# Has the Gap Closed? A Replication and Extension Study of Open-Source LLMs for Security-Specific Tabular Anomaly Detection
 
A project brief — paper concept, prior work, datasets, models, and a build plan.
 
---
 
## 1. The idea, in plain terms
 
Anomaly detection means finding the suspicious rows in a big pile of data — the one fraudulent transaction, the one intrusion attempt, the one bot account, hidden among thousands of normal ones.
 
For years this has been solved with classical statistics and ML (clustering, isolation forests, density-based scoring). In late 2024/early 2025, two research teams tested something new: can you just describe a row of data in plain English and ask an open-source LLM "does this look suspicious?" — with no special training? They found the open models **lost** to the classical statistical tools.
 
That test is now a bit stale: it used 2024-era open models (which have improved a lot since), and it only tested generic textbook-style benchmark data, not security-specific data (fraud, intrusions, abuse).
 
**This paper re-runs that test with today's open models, on security-specific data, and asks: has the gap closed?**
 
---
 
## 2. Abstract (draft — to be revised once results are in)
 
> Recent work has explored whether large language models can perform anomaly detection by converting structured records into text and scoring their likelihood or suspiciousness. Early results suggest open-source LLMs often underperform classical anomaly detectors on tabular benchmarks (AD-LLM, AnoLLM). However, those studies evaluated 2024-era open-weight models, almost exclusively on generic, domain-agnostic outlier datasets, leaving open whether the conclusion holds for current open-weight models and for security-specific domains — fraud and network intrusion — where feature semantics may be more amenable to a pretrained model's world knowledge than abstract statistical features are. This paper presents a replication and extension study: we re-evaluate current-generation open-weight models against an established panel of classical anomaly detectors, on both the original ODDS benchmark (for direct comparability to prior work) and newly added security-specific tabular datasets. We compare two LLM scoring modes — AnoLLM-style likelihood scoring and direct prompted suspiciousness scoring — and report not only AUROC/AUPRC but operational metrics that matter for security use (precision@K, recall@K, recall at a fixed low false-positive rate) alongside runtime and deployment cost. We additionally test whether causally-informed feature serialization, shown to help on generic data, transfers to security domains. We report where, and by how much, the 2024-era gap has closed, and what conditions, if any, make locally-deployed open models practically viable for security analytics.
 
*(This is a placeholder written before running any experiments — its job is to keep the project honest about what it's claiming. Rewrite it last, after Section 8's results are in, not before.)*
 
---
 
## 3. Why this is worth doing — the actual gap in the literature
 
| Paper | Venue | Code | Covers | Doesn't cover |
|---|---|---|---|---|
| **AD-LLM** | ACL Findings 2025 | [github.com/USC-FORTIS/AD-LLM](https://github.com/USC-FORTIS/AD-LLM) | First LLM-for-anomaly-detection benchmark — but for **text/NLP** categories (news, spam, reviews) | Tabular/numeric data; security domains; current-gen models (only tested Llama 3.1) |
| **AnoLLM** | ICLR 2025 | [github.com/amazon-science/AnoLLM-large-language-models-for-tabular-anomaly-detection](https://github.com/amazon-science/AnoLLM-large-language-models-for-tabular-anomaly-detection) | **Tabular** anomaly detection — serializes rows to text, scores via LLM likelihood, benchmarked on 30 ODDS datasets + 6 mixed-type sets | Security-specific datasets; current-gen open models (used Llama2/Mistral-7B-class backbones); operational/imbalance-aware metrics |
| **CausalTAD** | Feb 2026 (arXiv:2602.07798) | — | Shows column-ordering during serialization matters — causal-aware ordering raises AUC on the benchmarks it tests | Still generic benchmark data, not security-specific |
 
Paper: AD-LLM — [arxiv.org/abs/2412.11142](https://arxiv.org/abs/2412.11142)
Paper: AnoLLM — [OpenReview](https://openreview.net/forum?id=7VkHffT5X2) / [Amazon Science page](https://www.amazon.science/publications/anollm-large-language-models-for-tabular-anomaly-detection)
 
> **Before locking the related-work section, re-read the AnoLLM and CausalTAD papers directly.** Both have now been described secondhand a couple of times in this project (by me and by outside feedback), and a couple of specifics — exactly how AnoLLM aggregates likelihood across column permutations, and exactly how many benchmarks CausalTAD reports gains on — haven't been independently verified against the primary PDF. Five minutes against the source avoids citing a detail that turns out to be slightly off.
 
**The two honest, defensible deltas for this paper:**
1. **Current-generation open models** that postdate both benchmarks.
2. **Security-specific tabular domains** (fraud, network intrusion) instead of generic outlier datasets.
Be upfront in the paper that this is a replication-plus-extension, not a brand-new method. That's a strength, not a weakness — reviewers respect honest framing.
 
---
 
## 4. What we're building on (fork this, don't start from scratch)
 
**Use AnoLLM's repo as the base:** [github.com/amazon-science/AnoLLM-large-language-models-for-tabular-anomaly-detection](https://github.com/amazon-science/AnoLLM-large-language-models-for-tabular-anomaly-detection)
 
It already has:
- tabular-row-to-text serialization
- classical baseline detectors wired up via PyOD/DeepOD (Isolation Forest, DeepSVDD, REPEN, RDP, RCA, GOAD, NeuTraL, SLAD, DeepIsolationForest)
- ready-to-run scripts: `scripts/exp1-mixed_benchmark/run_anollm.sh`, `run_baselines.sh`, `scripts/exp2-odds/run_anollm.sh`, `run_baselines.sh`
What needs to change:
- swap the LLM backbone(s) to current models (see §6)
- add 1–2 new security-specific datasets (see §5b) alongside their existing ODDS suite
- keep the ODDS runs as-is — that's your apples-to-apples comparison point against the original paper's published numbers
(AD-LLM's repo is worth citing as related work, but not worth forking — wrong data modality for this idea.)
 
---
 
## 5. Datasets
 
### 5a. Baseline — for direct comparability to AnoLLM's published numbers
- **ODDS Library** (30 datasets, mostly numerical) — [odds.cs.stonybrook.edu](https://odds.cs.stonybrook.edu/) — already wired into the AnoLLM repo, no extra work needed.
### 5b. New — the security-specific extension (the actual novel contribution)
- **Credit Card Fraud Detection** — [kaggle.com/datasets/mlg-ulb/creditcardfraud](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud) — 284,807 transactions, 492 frauds, fully labeled, classic and easy to start with.
- **IEEE-CIS Fraud Detection** — [kaggle.com/c/ieee-fraud-detection](https://www.kaggle.com/c/ieee-fraud-detection) — larger, messier, more realistic mixed-type fraud data if you want a harder second dataset. *(Optional extension — add later, not in the first pass.)*
- **NSL-KDD** (network intrusion) — [unb.ca/cic/datasets/nsl.html](https://www.unb.ca/cic/datasets/nsl.html)
- **CICIDS2017** (network intrusion) — [unb.ca/cic/datasets/ids-2017.html](https://www.unb.ca/cic/datasets/ids-2017.html) *(Optional extension — add later, not in the first pass.)*
- **UNSW-NB15** (network intrusion) — [research.unsw.edu.au/projects/unsw-nb15-dataset](https://research.unsw.edu.au/projects/unsw-nb15-dataset)
- **Convenience loader for the network sets:** [github.com/rdpahalavan/nids-datasets](https://github.com/rdpahalavan/nids-datasets) — a Python package that downloads pre-curated UNSW-NB15 and CICIDS2017 in flow-level/packet-level form. Saves a lot of manual preprocessing.
**Minimum viable dataset set for the first pass:** ODDS subset (comparability) + Credit Card Fraud (clean, numeric, easy) + NSL-KDD or UNSW-NB15 (one network-intrusion set). That's enough for a real first paper. Fewer datasets with clean, rigorous analysis beats many datasets with messy preprocessing — add IEEE-CIS or CICIDS2017 later only if time allows.
 
---
 
## 6. Models to test
 
### Tier 1 — established, high-confidence, safe to cite as-is
- **Llama 3.1 8B / 3.3 70B** (Meta) — [huggingface.co/meta-llama](https://huggingface.co/meta-llama)
- **Mistral 7B Instruct v0.3 / Mixtral 8x7B** (Mistral AI) — [huggingface.co/mistralai](https://huggingface.co/mistralai)
- **Qwen2.5 7B / 14B Instruct** (Alibaba) — [huggingface.co/Qwen](https://huggingface.co/Qwen)
- **Gemma 2 9B** (Google) — [huggingface.co/google](https://huggingface.co/google)
- **Phi-4 14B** (Microsoft) — [huggingface.co/microsoft/phi-4](https://huggingface.co/microsoft/phi-4)
### Tier 2 — newer 2026-generation options (verify exact model-card name on Hugging Face before locking in — naming shifts fast in this space)
- **Qwen3** (7B/8B/14B) — Apache 2.0, currently a popular default "run locally" choice
- **Gemma 3** (4B/9B/27B)
- **Mistral Small 3.1** (24B) — strong 7B-class-equivalent option
- **Phi-4-mini** (3.8B) — runs on very modest hardware, good for a "smallest viable model" data point
- **DeepSeek distilled variants** (1.5B/7B/14B) — MIT licensed
**Suggested model line-up:** one per weight tier — Phi-4-mini (small), Llama 3.1 8B or Qwen2.5 7B (medium), Mistral Small 3.1 or Qwen2.5 14B (larger), optionally a 70B-class model if compute allows. Don't compare five models of the same size — the interesting question is whether a bigger local model justifies its extra compute cost, which needs a real size spread to answer.
 
---
 
## 7. Classical baselines (already wired up if you fork AnoLLM)
Isolation Forest, DeepSVDD, REPEN, RDP, RCA, GOAD, NeuTraL, SLAD, DeepIsolationForest — all via [PyOD](https://github.com/yzhao062/pyod) / [DeepOD](https://github.com/xuhongzuo/DeepOD). No need to implement these — just point them at the new datasets. The goal isn't to beat every baseline; it's to answer "are modern LLMs now competitive, and under what conditions?"
 
---
 
## 8. Experimental design — what, why, how, for each experiment
 
### 8.0 Metrics used across every experiment (define once, reuse everywhere)
 
Don't rely on AUC-ROC alone — security anomaly detection is severely class-imbalanced, and AUC-ROC can look deceptively good on 99%+-normal data.
 
| Metric | Why it's here |
|---|---|
| AUROC | standard ranking metric, comparable to AnoLLM's published numbers |
| AUPRC | more honest than AUROC under severe class imbalance |
| Precision@K | mirrors how a security analyst actually works — they inspect a fixed number of top alerts, not a fully ranked list |
| Recall@K | how many true anomalies are caught within that same top-K alert budget |
| Recall at 1% FPR | the metric that matters when alert fatigue is the real operational constraint |
| Runtime per 10K/100K rows | LLM scoring can be meaningfully slower than classical detectors — report it, don't bury it |
| Hardware footprint / cost | VRAM at the quantization level used, or $ cost for a hosted API — this is what makes "locally deployable" a real claim instead of a tagline |
| Parse-failure rate | how often a prompted score had to be retried or discarded — a real practicality cost specific to prompted scoring |
 
Compute Precision@K / Recall@K at a couple of fixed, realistic alert budgets (e.g., top 1% and top 5% of rows by score) rather than one arbitrary K.
 
Five experiments follow, each isolating one variable, in the order you should actually run them — each depends on the last being trustworthy.
 
### Experiment 1 — Reproduce the published baseline (sanity check)
 
- **What:** Run AnoLLM's own code, completely unmodified, on its original 30-dataset ODDS suite, using the same model and scoring setup described in their paper.
- **Why:** If you can't reproduce their published numbers within a small tolerance, every later experiment is built on a broken foundation — and this is the cheapest possible place to catch that, before you've written a single line of new code.
- **How:**
  1. Clone the repo and install the exact dependency versions it specifies.
  2. Run `scripts/exp2-odds/run_anollm.sh` and `scripts/exp2-odds/run_baselines.sh` exactly as shipped, no edits.
  3. Record per-dataset AUROC and AUPRC.
  4. Compare against the numbers in AnoLLM's own results tables.
  5. **Acceptance bar:** within ~2-3 AUROC points per dataset. If a dataset is further off than that, debug before moving on — don't proceed on a shaky foundation.
- **Output:** a reproduction table (dataset x method x AUROC) that becomes the fixed reference point every later experiment gets compared against.
### Experiment 2 — Swap in current-generation models, two scoring modes, same data (closes delta #1)
 
- **What:** Replace AnoLLM's original LLM backbone with each model from the Tier 1/Tier 2 shortlist (Section 6), re-run on the same 30 ODDS datasets, same serialization — but now score every model **two ways**, not one:
  - **(a) Likelihood scoring** — AnoLLM's own negative-log-likelihood method over the serialized row text.
  - **(b) Prompted suspiciousness scoring** — ask the model directly to rate each row 0-100 for how anomalous it looks, using the same row text as input.
- **Why:** Swapping the model alone only tells you *whether* performance changed. Comparing two scoring modes tells you *why*: does a newer model help because it assigns better likelihoods to anomalous rows, or because an instruction-tuned model can directly reason about suspiciousness when asked? That's a more interesting question than "which model wins," and it's nearly free to add since you're already running every model on every dataset regardless.
- **How:**
  1. Leave AnoLLM's row-to-text serialization untouched for both scoring modes — don't introduce a second variable here.
  2. **Make and document one methodological decision before running anything:** likelihood scoring needs token-level log-probabilities, and not every hosted inference endpoint exposes those. Pick one of two paths and apply it consistently across every model:
     - run models where you can get log-probs (locally, or via an API that exposes them), keeping AnoLLM's exact NLL-based scoring for mode (a); or
     - for any model where log-probs aren't available, report only mode (b) for that model and say so explicitly — don't silently substitute one scoring method for another between models.
  3. Run every model, both modes, on all 30 ODDS datasets.
  4. Metrics: the full set in §8.0 (AUROC, AUPRC, Precision@K, Recall@K, Recall@1%FPR), computed separately for each scoring mode, plus a summary count of how many of 30 datasets each LLM/mode combination beats the best classical baseline on.
  5. **Explicitly out of scope for this pass:** a third "few-shot prompted scoring" mode (show the model labeled normal/anomalous examples before scoring). It's a reasonable follow-up, not a v1 requirement — see §8.6.
- **Output:** an updated version of AnoLLM's comparison table, now with a model-generation axis *and* a scoring-mode axis.
### Experiment 3 — Security-domain transfer (closes delta #2)
 
- **What:** Take the 2-3 most interesting model/scoring-mode combinations from Experiment 2, plus the full classical-baseline panel, and run them on the new security-specific datasets — Credit Card Fraud and NSL-KDD/UNSW-NB15 first, IEEE-CIS/CICIDS2017 if time allows.
- **Why:** Tests whether domain matters, independent of model generation or scoring mode. Security datasets often have semantically rich, human-readable column names (transaction amount, login attempts, packet count) — very different from ODDS's often-anonymized statistical features. An LLM's pretrained world knowledge might transfer better here, or it might not. Either outcome is a real, publishable finding — see §8.5 for how to frame each possible result.
- **How:**
  1. Build a row-to-text serialization template per new dataset, following the same general pattern AnoLLM uses for ODDS (feature name + value to a short natural-language sentence).
  2. For severely imbalanced data (Credit Card Fraud is well under 1% positive), keep the test set's natural imbalance intact for honest evaluation.
  3. Run the identical models, scoring modes, and baselines used in Experiment 2 — no new variables.
  4. Metrics: the full set in §8.0, with AUPRC, Precision@K, and Recall@1%FPR weighted more heavily in your interpretation here than AUROC — that's the whole point of including them.
- **Output:** a head-to-head table — LLM vs. classical, ODDS vs. security data — that lets you state directly whether the gap got bigger, smaller, or stayed the same on security-relevant data.
### Experiment 4 — Serialization sensitivity (a cheap bonus finding)
 
- **What:** On one or two of the new security datasets, test two column-ordering strategies for the row-to-text step: (a) default/arbitrary order, vs. (b) a domain-logical order — e.g. for fraud, identity fields, then transaction fields, then behavioral/velocity fields, then outcome.
- **Why:** CausalTAD (Feb 2026) found this matters on generic data — causal-aware column ordering improved AUROC. You're already writing new serialization code for the new datasets anyway, so testing both orderings is nearly free, and it's a second clean, citable finding even if your main result is a wash.
- **How:**
  1. Fix one model (the best performer from Experiment 3) and one dataset.
  2. Run the full pipeline twice, changing only the column order.
  3. Compare AUROC and report the delta.
- **Output:** one table or figure showing whether CausalTAD's effect, found on generic data, also holds on security data.
- **Explicitly out of scope for this pass:** the fuller serialization matrix (random permutations, JSON vs. natural-language templates, with/without feature names). Two variants is enough for a real finding; eight variants is a separate, more thorough survey paper. See §8.6.
### Experiment 5 — Practicality and deployability (the "would a company actually use this" angle)
 
- **What:** For every model/mode run in Experiments 2-3, record wall-clock inference time per row/batch, hardware footprint (VRAM at the quantization level used, or dollar cost for a hosted API), and the rate of unparseable or malformed model outputs (a cost specific to prompted scoring, mode (b) in Experiment 2).
- **Why:** This paper's whole hook is whether free, locally-deployable models are practically viable, not just accurate. A model that's 2 AUROC points better but produces 15% unparseable outputs, or needs a GPU most companies don't have, is a different practical answer than one that's 2 points worse but runs cleanly on a laptop.
- **How:**
  1. Log timestamps and token counts during every run in Experiments 2 and 3 — instrument this from day one, it's expensive to reconstruct after the fact.
  2. Track parse-failure rate per model per scoring mode.
  3. Record the quantization level (Q4/Q8/full precision) for any locally-run model, since it affects both speed and accuracy.
- **Output:** a small "practicality" table that sits next to your accuracy tables — this is what makes the deployment framing land as a real finding instead of just a tagline.
### 8.5 Expected result patterns — the paper is useful under any of these outcomes
 
Worth pre-writing the discussion section's shape now, regardless of which result actually lands:
 
- **Classical methods still win outright:** still publishable — "modern open-source LLMs have improved, but classical detectors remain stronger and cheaper for high-volume numeric security data."
- **LLMs close the gap specifically on mixed-type/semantically-rich data:** the most interesting middle outcome — "LLMs remain weak on purely numeric fraud features but improve where feature names and categorical semantics provide useful context."
- **LLMs are weak as standalone detectors but useful for triage/explanation:** arguably the best practical outcome — "LLMs aren't ideal first-stage detectors, but may be useful as second-stage components that rerank or explain alerts produced by classical detectors." Worth one paragraph in the discussion even if you don't build the actual two-stage pipeline (see §8.6) — flag it as the natural next step.
### 8.6 What we're explicitly not building in this version
 
Cut these now, mention them as future work in the discussion section — each is a real, separate chunk of engineering time that would blow the 3-4 week budget:
 
- **Few-shot prompted scoring** (a third scoring mode, on top of likelihood + zero-shot prompted) — real prompt-design and evaluation time, not v1 scope.
- **The full serialization matrix** (random permutations, JSON vs. natural-language templates, with/without feature names) — Experiment 4 tests two variants; a fuller 6-8-variant matrix is its own thorough study.
- **An actual two-stage classical-detector + LLM-reranker/explainer pipeline** — a genuinely separate, interesting follow-up project (see the third bullet in §8.5), not something to build inside this paper's timeline.
### Rough timeline mapped to experiments
- Days 1-3: Experiment 1 (reproduce baseline)
- Days 4-6: Experiment 2 (model swap + two scoring modes on ODDS)
- Days 7-10: Build new dataset loaders, start Experiment 3
- Days 11-15: Finish Experiment 3, run Experiment 4, finalize Experiment 5's instrumentation/logs
- Week 3-4: Analysis + write-up, abstract rewritten last
**Total: ~3-4 weeks of part-time work**, not months. The additions in this section (operational metrics, second scoring mode) are deliberately the cheap, high-value ones — they reuse outputs you're already generating rather than requiring new experiments.
 
---
 
## 9. Framing the novelty honestly (for the intro/related-work section)
 
> "AD-LLM (Yang et al., 2025) and AnoLLM (Tsai et al., 2025) established that off-the-shelf open-source LLMs underperform classical anomaly detectors on generic tabular benchmarks. We revisit this finding along two axes that prior work did not test: (1) current-generation open-weight models released after these benchmarks were built, and (2) security-specific tabular domains — fraud and network intrusion — rather than generic outlier datasets. We ask: has the gap closed?"
 
**On the "isn't this just AnoLLM with newer models?" objection:** yes, in part — and that's fine. Replication-and-extension studies are an established, accepted genre, especially at data-centric and applied-ML venues (the DMLR journal in §10 exists specifically for this kind of work). Re-evaluating a claim as the underlying models change is exactly what a good benchmark/survey paper does — it isn't a flaw to manage around, it's the genre. State the replication framing plainly in the related-work section rather than dancing around it. What separates a thin version of this paper from a strong one isn't avoiding the comparison — it's depth: operational security metrics instead of AUROC alone, more than one LLM scoring strategy, and serialization treated as a real variable rather than a footnote. Those are exactly the additions in §8.0 and Experiment 2 above.
 
---
 
## 10. Possible venues to target
- **DMLR (Data-centric Machine Learning Research)** journal — good fit, data-centric ML evaluation focus, and explicitly receptive to replication/extension studies like this one.
- A trust/safety-flavored workshop at a major ML conference (NeurIPS/ICLR workshop track).
- An applied/industry track at a security or data-mining conference.
- arXiv preprint first, regardless of venue — gets it citable and dated immediately.
---
 
## References
- Yang, T. et al. "AD-LLM: Benchmarking Large Language Models for Anomaly Detection." ACL Findings 2025. [arxiv.org/abs/2412.11142](https://arxiv.org/abs/2412.11142)
- Tsai, C-P. et al. "AnoLLM: Large Language Models for Tabular Anomaly Detection." ICLR 2025. [OpenReview](https://openreview.net/forum?id=7VkHffT5X2)
- "CausalTAD." arXiv:2602.07798, Feb 2026.
- Rayana, S. (2016). ODDS Library. [odds.cs.stonybrook.edu](https://odds.cs.stonybrook.edu/)