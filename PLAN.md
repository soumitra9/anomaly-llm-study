# Project Plan v1.0 — Tabular LLM Anomaly Detection: Scoring Mode, Scale, and Operating Regime

> **Working title (revised):** *"When Does Tabular LLM Anomaly Detection Hold Up? A Controlled Study of
> Scoring Mode, Model Scale, and Operating Regime on Generic and Security Data."*
>
> This is v1.0 — it integrates four independent adversarial reviews (methodology/statistics,
> feasibility/cost, novelty/reviewer-defense, reproducibility) of the v0.1 draft. Sections marked
> **[REV]** changed materially because of those reviews. Verified against primary sources: AnoLLM
> (ICLR 2025), AD-LLM (ACL Findings 2025), Li et al. (IJCAI 2024, arXiv 2406.16308), CausalTAD
> (arXiv:2602.07798), TabLLM, GReaT, ADBench.

---

> **⚠️ DELTAS SINCE v1.0 (2026-07-01) — the research design below stands; these execution assumptions changed.**
> For current status/config always defer to `ROADMAP.md`, `RUNLOG.md`, `FLEET.md`, and memory `project-state.md`.
> - **Compute platform:** free Kaggle GPU → **RunPod A40 fleets** (Kaggle P100 retired: emulated bf16 too slow +
>   OOMs). All "free Kaggle / Kaggle-vLLM / 12h-session / weekly-quota" text below is superseded by RunPod A40
>   ($0.44/hr, double-confirm gated). Kaggle MCP is still used, but only for **dataset download** (e.g. creditcard).
> - **Engine:** the "Kaggle-vLLM single engine" plan → **HF Transformers everywhere** (no vLLM in v1); cross-engine
>   parity is therefore moot.
> - **Scale-up model:** **Qwen3-4B → Qwen2.5-3B** (Qwen3 arch needs transformers≥4.51, incompatible with pinned
>   4.48.2). Any "Qwen3-4B" below = Qwen2.5-3B.
> - **Status:** M1 gate DONE (partial repro); **M2 Exp-2 A/B fleet running** (SmolLM-360M @2000 steps + Qwen2.5-3B
>   @1000 steps × 30 ODDS × 3 seeds). max_steps for Qwen reduced to 1000 (2000 over-trains — see RUNLOG D0).

---

## 0. Corrections & reframing incorporated

**From primary-source verification (v0.1):**
1. AnoLLM's backbone is **SmolLM-135M/360M**, not "7B-class"; its own ablation shows *bigger is
   worse* for likelihood scoring (ODDS 0.884→0.865→0.861 for 135M→360M→1.7B).
2. **"Open LLMs lost to classical" is false for tabular.** AnoLLM *won* mixed-type, *tied* numeric
   ODDS. Li et al. 2024 found GPT-4 *on par* with SOTA. The pessimistic framing was AD-LLM (**text**).
3. AnoLLM already covers fraud (fraud-ecommerce 9.36%, vehicle-insurance 5.99%).
4. No NVIDIA GPU → **budget-hybrid compute** (§9): free Kaggle + **local Mac (Apple Silicon) for ≤4B
   models** carry the bulk; one short paid A100 burst only for fp16 14B. Mind cross-engine logprob parity.
5. CausalTAD = causal column *ordering* **+** *reweighting* (two modules), not ordering alone.

**From the reviews — framing changes [REV]:**
6. **Retire "has the gap closed?"** — it is a strawman by our own correction #2. Reframe around the
   *operating regime*: AnoLLM was competitive via likelihood with tiny models; **does that hold,
   improve, or invert under (a) prompted scoring, (b) modern scale, and (c) the conditions security
   actually cares about — extreme imbalance and fixed-FPR alert budgets?**
7. **Prompted scoring is NOT a novel contribution** (Li et al. 2024, AD-LLM, the GPT-4 blog). The
   contribution is the **first controlled, same-model A/B between likelihood and prompted scoring on
   open-weight models, under operational + security metrics**, plus the constructive two-stage result
   (Exp 6). Frame honestly; cite and differentiate all prior prompted-tabular work.
8. **Operational metrics are not a contribution** — they are the correct protocol. The contribution is
   the *finding they enable* (e.g., AUROC-competitive LLMs collapsing under Recall@1%FPR / cost).
9. **Add a constructive contribution (Exp 6):** a two-stage classical→LLM triage/rerank pipeline. This
   is the single highest-leverage addition — it turns a likely "LLMs weak standalone" verdict into a
   method result, reuses outputs we already generate, and directly serves the operating-regime framing.

---

## 1. Research questions, hypotheses, and pre-registered confirmatory tests [REV]

Each RQ has **one pre-registered confirmatory test**; everything else is exploratory. Family-wise
error controlled with **Holm–Bonferroni** across the confirmatory set.

| RQ | Question | Hypothesis | Pre-registered confirmatory test |
|---|---|---|---|
| RQ1 | Does AnoLLM reproduce? | within tolerance | Exp 1 acceptance gate (§8) |
| RQ2 | Do *modern* small models beat SmolLM at NLL scoring (size ~fixed)? | H2: little/no gain (two-sided, **not** assumed null) | Wilcoxon (Holm-corrected) modern-small vs SmolLM across 30 ODDS, AUROC |
| RQ3 | Does **prompted** scoring scale with capability where **likelihood** does not? | H3: prompted AUROC rises with model tier; likelihood flat | Slope of AUROC vs model-tier, prompted vs likelihood; sign test across ODDS |
| RQ3b | Does prompted benefit specifically from **semantic** column names? | H3b: yes | **Semantic-vs-anonymized column-name ablation on `pima`** (diabetes; `breastw` backup — both genuinely semantic; NOT credit-card, whose PCA cols are anonymized), bootstrap CI on delta |
| RQ4 | Does the LLM-vs-classical gap differ on **security** data? | H4: LLMs relatively stronger on semantic/mixed; classical strong on numeric high-volume | Per-dataset bootstrap CIs on best-LLM − best-classical, by metric |
| RQ5 | Does a domain-informed serialization **order** change AUROC on security data? | H5: small effect | Multi-ordering × ≥2 datasets × 3 seeds, Wilcoxon vs random-permutation control |
| RQ6 | Practicality: accuracy vs cost/latency/parse-failure? | descriptive | Accuracy–cost Pareto frontier (Exp 5) |
| RQ7 | Can an LLM **second stage** improve a classical detector's operating point? | H7: yes, at fixed alert budget | Recall@1%FPR / Precision@K of two-stage vs classical-alone, bootstrap CI (Exp 6) |

**Primary contribution claim (honest):** not a new detector. (i) The first controlled same-model
likelihood-vs-prompted comparison on open-weight models; (ii) re-evaluation under extreme-imbalance
and fixed-FPR operating conditions on security data; (iii) a constructive two-stage triage result; (iv)
serialization-order tested as a variable. Replication+extension genre, stated plainly.

---

## 2. Datasets

### 2a. Comparability
- **ODDS** (30 sets) via AnoLLM repo. For RQ1–RQ3.
- AnoLLM's 6 mixed-type sets re-run in Exp 1 for full reproduction (not our novelty).
- **~10/30 ODDS sets have human-readable column names** (per AnoLLM). The Exp 3b semantic ablation runs
  on **`pima`** (diabetes: glucose, BMI, blood pressure, insulin, age — unambiguously semantic; backup
  **`breastw`**: clump thickness, cell-size uniformity, …) — free on Kaggle/local, decoupled from the
  UNSW stretch. **Day-0 check (per review):** ODDS `.mat` files ship only `X`+`y` — column *names are
  usually not in the file*. Before coding Exp 3b, verify the names are recoverable from the original UCI
  source **and** line up with the `.mat` column order; if `pima`/`breastw` don't, find another named set.

### 2b. Security extension
| Dataset | Type | Full size | True anomaly % | Role | Source |
|---|---|---|---|---|---|
| **Credit Card Fraud** (ULB, ODbL) | numeric (PCA V1–28 + Amount/Time) | 284,807 | 0.17% | extreme imbalance; AUPRC/Recall@1%FPR story | Kaggle (MCP) |
| **UNSW-NB15** (academic) | mixed, rich named flow features | ~2.5M flows | varies | semantic columns; modern IDS — **preferred network set** | `nids-datasets` / UNSW |
| *NSL-KDD* | mixed | ~148k | n/a | OPTIONAL; canonical-split conflict (§2c) — likely demote | UNB |
| *IEEE-CIS / CICIDS2017* | mixed | large | varies | OPTIONAL, only if time | Kaggle (MCP) / UNB |

**First-pass minimum:** ODDS subset + Credit Card Fraud + UNSW-NB15.

### 2c. Sampling, splitting, leakage — the methodological core [REV]
- **Match AnoLLM protocol** for comparability: uncontaminated unsupervised; train = 50% of *normals*;
  test = remaining normals + all anomalies; **3 seeds** (reduced from 5 for cost — §9b; report transparently); mean ± std.
- **One frozen (train-normals, test-set) pair per seed, used identically by every method** (LLM and
  classical). Subsampling is for scoring *cost*, never a per-method difference. **[fixes meth-M5/feas]**
- **Cost-driven test subsampling with importance reweighting [fixes meth-C1 — critical]:** for large
  sets (credit-card, UNSW, big ODDS), score **all anomalies + a stratified random sample of *m*
  normals**, then **importance-reweight each sampled negative by `w = N_neg_total / m`** when computing
  AUPRC, FPR, Precision@K, Recall@1%FPR. This recovers *unbiased true-base-rate* metrics at a fraction
  of cost. AUROC is rank-based and prevalence-invariant. **Never report subsampled-prevalence AUPRC.**
  - Resample the normal subset **inside the 3-seed loop** so subsampling variance enters the ±std.
  - Report AUPRC **relative to the no-skill baseline** (= true prevalence) and with **bootstrap CIs**.
  - Prefer **absolute** operating points (Recall at a fixed *count* of false alarms; Precision in top-N
    alerts) over percent-of-rows, which shift with test size.
- **Cap every large test set** (credit-card, UNSW, big ODDS like `cover`/`http`/`shuttle`/`mnist`) to a
  documented size (target ≈ 20–40k scored rows) via the same reweighted scheme. **[fixes feas-C1/C3]**
- **Split policy, pre-registered per dataset [fixes meth-M4]:**
  - *Credit-card:* report **both** a temporal split (train earlier, test later — operationally honest)
    and the AnoLLM random split (labeled "comparability-only, optimistic"). Decide `Time` handling and
    document.
  - *UNSW-NB15:* subsample to a stratified ~200–400k working set from the start. Publish the **exact
    dropped-column list** (drop `label`, `attack_cat`, `id`, IP/port identifiers). **Leakage screen:**
    single-feature AUROC; any feature >~0.95 alone is flagged/dropped (audit `ct_*` look-ahead features).
  - *NSL-KDD:* its canonical KDDTrain+/KDDTest+ split is *not* a random-normal split. Either use the
    canonical split (then label it a separate transfer experiment, not AnoLLM-protocol) or drop it.
    **Default: demote NSL-KDD; lead with UNSW.**
- **Serialization:** replicate AnoLLM "standard" rescaling + rounding for numeric columns. Keep raw
  category strings for LLM (semantics are the point); PyOD/DeepOD conventions for classical.
- **Every split/subsample is hashed and versioned** (§10 RunMetadata) — the index sets, not just the prose.

### 2d. Data acquisition via Kaggle MCP [REV — schema-inspected, official Kaggle MCP confirmed]
The official Kaggle MCP is connected and authenticated. It is the **canonical data-acquisition path**
(replaces a hand-rolled Kaggle CLI/API in `src/data/`). Verified capabilities and how we use them:

- **Datasets — version-pinned, hashable download.** `get_dataset_info` + `get_dataset_files_summary`
  for inspection; `download_dataset(ownerSlug, datasetSlug, datasetVersionNumber, hashLink)` for the
  fetch. *Credit Card Fraud* = `mlg-ulb/creditcardfraud`, **pin `datasetVersionNumber=3`** (2018-03-23),
  single `creditcard.csv` ≈150 MB, 31 cols (29 decimal + 2 int), license **ODbL** (record in
  `DATA_LICENSES.md`). The MCP exposes `hashLink` per version → store it + our own post-download content
  hash in RunMetadata (§10) so the Exp-3 reproduction gate is falsifiable (mismatch ⇒ code, not data drift).
- **Competitions** (different API from datasets): `get_competition`, `get_competition_data_files_summary`,
  `download_competition_data_files` for the optional *IEEE-CIS* set (`ieee-fraud-detection`).
- **Column metadata without downloading:** `get_dataset_files_summary` / `list_dataset_files` returns
  column types up front — use it to draft serialization templates (§4) before pulling 150 MB.
- **GPU-quota–aware smoke testing:** `get_accelerator_quota` confirms **30 GPU-h/week** (108,000 s;
  TPU 20 h; refreshes weekly) — call it before each Kaggle run to budget. `create_notebook_session`
  (`machineShape` for GPU, `dockerImage`, `enableInternet`) runs the Exp-1 SmolLM reproduction smoke-test
  scriptably; `get_notebook_session_status` / `download_notebook_output` retrieve results;
  `cancel_notebook_session` to stop. This makes Kaggle scriptable compute, not just a manual UI.
- **Model weights (optional):** `download_model_variation_version` supports vLLM/Transformers/GGUF
  frameworks — a fallback to Hugging Face for pulling SmolLM/Qwen/Gemma/Phi weights if HF is gated/slow.
- **Caveats unchanged:** ODDS is **not** on Kaggle (comes from the AnoLLM repo / Stony Brook — optionally
  mirror `.mat` files to our own Kaggle Dataset via `upload_dataset_file` to dodge the flaky host);
  UNSW-NB15 stays on `nids-datasets`/UNSW. Do not commit any downloaded data (`data/` gitignored, §10).

> **Status:** the MCP's exact tools were not inspectable when this plan was written (server not loaded
> in-session). The three loaders (`creditcard.py`, optional `ieee_cis.py`, ODDS mirror) must expose the
> same `download() → (path, version_id, content_hash)` interface regardless of whether the backend is
> the MCP or the Kaggle CLI, so the rest of the pipeline is backend-agnostic. Finalize the concrete MCP
> calls after inspecting the schemas.

---

## 3. Models — v1 lineup CUT to control the grid [REV: feas-M5]

The grid multiplies per model; v0.1's 6–7 models were infeasible. **v1 confirmatory lineup = 3:**

| Role | Model (verify HF revision at run time) | Likelihood (NLL) | Prompted | Why |
|---|---|---|---|---|
| Repro + size anchor | SmolLM-360M (Apache-2.0) | ✅ | ✅ | replicates AnoLLM; smallest tier |
| Modern small | Qwen3-4B (Apache-2.0) | ✅ | ✅ | modern arch/instruction-tuning, size ≈ AnoLLM's regime |
| Medium | Qwen3-14B (Apache-2.0) | ✅ (A100 fp16) | ✅ | tests whether scale helps each mode |

**Optional / spot-check tier (only if budget+time remain, single-dataset, not in confirmatory tests):**
Phi-4-mini-3.8B, Gemma-3-4B (cross-family robustness); Mistral-Small-24B. Same-family ladder
(SmolLM/Qwen3) keeps tokenizer effects comparable within the scale test.

**Large-model ceiling = a footnote spot-check, NOT a comparand [per review].** If useful, spot-check one
big hosted model (GLM-5 / Qwen3.5-large) via API and report it as a one-line footnote ("observed X"),
scored however is easiest — it is *not* folded into the fair expected-value A/B, so its scoring method
doesn't need to match. (Only if you ever promote it to a real comparand would `top_logprobs` availability
matter — not in scope.)

**Controls:** every confirmatory model runs **both** modes on the **same** weights → no scoring-mode
confound. **Hold precision fixed (fp16) within the confirmatory comparison**; quantization is a separate
one-model spot-check, never mixed into the scale ladder. **[fixes meth-MN3]** **Engine discipline
(Gap B):** run the whole RQ3 scale ladder (4B→8B→14B) on a **single engine** — free Kaggle-vLLM for
≤8B, paid A100-vLLM for 14B — so no cross-engine logprob confound falls *inside* a comparison; use
**local Mac (MLX/llama.cpp/HF-MPS)** only for non-comparative work (repro anchor, prototyping) unless
the day-1 logprob-parity check (§9/Exp 1) passes. Record HF revision hash + quant + **inference engine**
+ stack versions per run (§10).

---

## 4. Scoring methods — exact specifications [REV]

### 4a. Likelihood mode (mode A) — replicate AnoLLM
- Score = mean NLL over **r random column permutations** (AnoLLM Eqn 5); textual columns
  length-normalized (Eqn 6); column-name tokens excluded.
- **r is a budgeted parameter [fixes feas-C1/M1; §9b]:** **cache the per-permutation NLLs, not just
  their mean** — then the r-sensitivity curve (r=5/8/10/21) is computed **post-hoc by averaging prefixes
  of a single run**, so it costs nothing extra (a line in the aggregation script, reported as a
  robustness result). Run the confirmatory grid at **r=10**, **r=5 on expensive sets**, and **r=21 on
  the ~3 small cheap datasets** that anchor the sensitivity curve; report r per run. r forward
  passes/row is the dominant cost driver of the whole project.
- Implemented via vLLM `prompt_logprobs` (single prefill, no generation — much cheaper per pass than
  mode B). **Tokenizer-fairness check [fixes meth-M3]:** re-derive length-normalization and
  column-name masking per model's tokenizer; verify number-rounding yields comparable token counts
  across SmolLM/Qwen tokenizers, so a "no-gain" H2 result isn't a tokenizer artifact.
- **Smoke-test prompt_logprobs throughput + host-RAM at scale on the smallest and largest model before
  committing the full grid** (vLLM logprob objects have caused memory cliffs). Set `prompt_logprobs` to
  the minimum needed. **[fixes feas-M1]**

### 4b. Prompted mode (mode B) — continuous score by default [REV: meth-C2 — critical]
The v0.1 "parse a 0–100 integer" design compares a continuous NLL against a coarse, heavily-tied
ordinal — mechanically depressing prompted AUROC/AUPRC and confounding *capability* with *output
granularity*. **Default prompted score = expected value over a verbalizer token distribution:** prompt
the model for an anomaly level, then compute `score = Σ_k p(k)·k` over the level tokens' logprobs (we
have logits locally via vLLM). This yields a **continuous, tie-free** score from a single forward pass,
**eliminates parse failures**, and makes the A/B fair.
- **Fallback / comparison:** also record the naive parsed-integer score for one model to quantify how
  much the elicitation method itself matters; run a **ceiling analysis** (discretize NLL to the same #
  of levels) to bound how much granularity alone costs.
- **Prompt template:** native chat template per model; system = security-analyst framing; user =
  serialized row + 1-line column schema; ask for an anomaly level. **Versioned, and the *rendered*
  prompt is content-hashed into each run's metadata** (§10). **[fixes repro-C3]**
- **Prompt-sensitivity sweep [fixes meth-M1]:** 2–3 semantically-equivalent paraphrases; report
  mean ± range so a flat capability curve isn't actually prompt-format noise, and capability is
  separated from prompt-fit.
- **Zero-shot only** in v1 (few-shot = future work). Temperature 0 / greedy; seed logged.
- **Cost:** 1 pass/row (no permutation averaging). **Mandate vLLM offline batched inference**
  (`llm.generate(all_prompts)`), `max_tokens` small with a stop token — never a per-row request loop.
  **[fixes feas-M2]**
- **Tie-aware AUROC** (Mann-Whitney with averaged ranks); **never random/deterministic tie-breaking
  before metric computation**; report # distinct score levels per config as a diagnostic. **[fixes meth-C2]**
- **Local-only requirement:** the expected-value scorer needs token logprobs, which all *local* engines
  (vLLM / HF / llama.cpp / MLX) provide. (Hosted APIs would need `top_logprobs`, but the only API model
  is a footnote spot-check (§3), not a comparand, so this never gates a confirmatory result.)

### 4c. Methodological decision logged (brief §8.2)
For the scale ladder, both modes run on the **same weights and same engine** with exact log-probs — no
silent substitution. Cross-engine (Mac vs vLLM) scores are trusted only after the day-1 logprob-parity
check (§9/Exp 1, Gap B); where it fails, that config is labelled a **separate method**, never folded into
the fair A/B. (The large hosted model is a footnote spot-check (§3), outside the A/B entirely.)

---

## 5. Classical baselines
AnoLLM's panel via PyOD/DeepOD: IForest, PCA, KNN, ECOD (classical); DeepSVDD, RCA, SLAD, GOAD,
NeuTraL, ICL, DTE, REPEN (deep). Exact AnoLLM configs on ODDS; document any LR/epoch change forced by
the security data. **Score classical baselines on the same frozen, subsampled+reweighted eval set as the
LLMs** (cheap) for apples-to-apples; report full-set classical numbers separately. **[fixes meth-M5/M4-cost]**
Note KNN/deep methods on 200–400k UNSW rows may be slow/OOM — budget accordingly.

---

## 6. Metrics [REV]
- **AUROC** (comparability, prevalence-invariant); **AUPRC** reported **relative to no-skill baseline
  (=prevalence)** with **bootstrap CIs**; **average-precision-gain** when aggregating across ODDS's
  varying base rates (simple AUPRC mean across heterogeneous prevalences is misleading). **[meth-MN5]**
- **Precision@top-N** and **Recall@fixed-false-alarm-count** (absolute budgets, sampling-robust under
  reweighting) — primary operating metrics; also % budgets for comparability.
- **Recall@1%FPR** with **Clopper–Pearson CIs** (only 492 positives in credit-card → wide binomial CI). **[meth-MN6]**
- **Runtime** per 1K/10K/100K rows; **$ cost** ($/1K rows = GPU-sec×rate or API price); **VRAM**@quant;
  **parse-failure rate** (near-zero with the expected-value scorer — report anyway).
- All metrics: mean ± std over **3 seeds** (§9b). **Distinguish split-variance from run-variance** and say which
  the ±std reflects (here: data-split, since scoring is deterministic). **[fixes meth-C3]**
- Report a "# datasets where config beats best classical" tally per metric.

---

## 7. Statistical rigor [REV]
- **ODDS (30 datasets):** Friedman omnibus → Nemenyi **critical-difference diagram** (Demšar 2006),
  replicating AnoLLM Fig 7. Pre-registered pairwise claims → **Holm-corrected** Wilcoxon signed-rank.
- **Security (2–3 datasets):** **NO Friedman/Nemenyi/CD** (no power, invalid at n=2–3). Use **per-dataset
  bootstrap CIs over test instances** and report effect sizes. State this scope split explicitly. **[fixes meth-C3]**
- **Multiple comparisons:** one pre-registered confirmatory test per RQ (§1); Holm–Bonferroni across the
  family; everything else labeled exploratory. **[fixes meth-C4]**
- **Reproduction gate** defined on the **aggregate** (mean AUROC within ~1 pt + per-dataset rank
  correlation) **plus** a per-dataset band relative to AnoLLM's published ±std (not a flat ±2–3). **[fixes meth-MN2]**
- **Parse-failure handling:** report metrics **both** excluding failed rows and with conservative
  imputation (least-anomalous score, not median); parse-failure-rate is a primary reported quantity. **[fixes meth-MN1]**
- **Variance asymmetry:** mode A (r perms) is lower-variance than mode B (1 pass) — note when
  interpreting close AUROC gaps. **[meth-MN4]**

---

## 8. Experiments (dependency-ordered) [REV]

**Exp 1 — Reproduce AnoLLM** *(Days 1–5; **free Kaggle GPU + local Mac — no paid GPU yet**).* Run shipped
scripts **unmodified** on ODDS + 6 mixed-type with SmolLM-135M/360M. Gate per §7. **Also in this window:
the engine-parity check (Gap B)** — score one model (e.g. Qwen3-4B) on both the chosen ladder engine
(Kaggle-vLLM) and local Mac (MLX/llama.cpp/HF-MPS); proceed with cross-engine use only if logprobs agree
within tolerance, else keep the whole ladder on one engine. Fallback: if vLLM won't pin with the repo's
torch, reproduce mode A via plain `transformers` logprob extraction (the reproduction only).
**Risk gate — do not proceed until reproduction passes.** **[feas-M3/M4]**

**Exp 2 — Model generation × scoring mode on ODDS** *(Days 6–12; mostly free Kaggle).* {mode A, mode B}
× 3 seeds. **SmolLM-360M + Qwen3-4B run on all 30 ODDS (free Kaggle → preserves CD diagram + AnoLLM
comparability); Qwen3-14B runs on a ~12-dataset representative subset (paid A100 burst, §9/§9b)** — state
the subset selection criterion (span size/dimensionality). Tests RQ2, RQ3. Output: ODDS table with
generation × mode axes + beats-best-classical tally + CD diagram (on the 30-set small-model results).

**Exp 3 — Security transfer** *(Days 11–18; mostly free Kaggle + small paid burst).* Datasets:
credit-card (both splits) + UNSW (subsampled, reweighted). **Cost-shaped scoring [§9b]: mode B (prompted)
+ classical on both security sets; mode A (likelihood) only on credit-card for ONE model** (retains a
partial likelihood-vs-prompted A/B; full A/B already lives on ODDS) — skip mode A on UNSW (r-permutation
cost worst there). Aligns with the operating-regime framing: the security question is "can prompted LLM
scoring compete with classical under operational metrics." Don't select on ODDS winners (winner's-curse);
if compute forces it, pre-register the rule and treat configs as held-out. Lead with AUPRC /
Precision@top-N / Recall@1%FPR. Tests RQ4. **[fixes meth-M7]**

**Exp 3b — Semantic vs anonymized column names** *(on **`pima`** — diabetes; **`breastw`** backup —
free Kaggle/local; NOT credit-card, whose PCA cols are already anonymized; decoupled from the UNSW
stretch).* Same model/mode, real column names vs `col_1…col_n`. Isolates the semantic-knowledge
contribution. **Day-0 pre-step (§2a):** confirm the chosen set's column names are recoverable from UCI
and aligned to the `.mat` column order *before* writing code — else swap to another named set. Tests
RQ3b. **[fixes meth-M2; relocated + named per review]**

**Exp 4 — Serialization order** *(Days 16–19).* Multiple orderings {arbitrary, domain-informed, ≥2
random-permutation controls} × ≥2 security datasets × ≥2 models × 3 seeds, bootstrap CIs. Honest scope:
this tests whether *a domain-informed order* helps — **not** that CausalTAD transfers (we don't run their
causal-discovery or reweighting). *Stretch:* run a lightweight causal-ordering (PC/NOTEARS on train
normals) to make a real CausalTAD-mechanism-transfer claim; else keep as labeled ablation. Tests RQ5. **[fixes nov-M1/meth-M6]**

**Exp 5 — Practicality → Pareto** *(instrumented throughout; finalized Days 18–20).* Runtime, $, VRAM,
parse-failure from Exp 2/3 logs → **accuracy-vs-cost Pareto frontier as a first-class figure** (not just
a table). Tests RQ6. **[fixes nov-M4]**

**Exp 6 — Two-stage classical→LLM triage/rerank** *(Days 19–22; the constructive contribution) [REV: nov-M2].*
Take a cheap classical detector's (IForest/ECOD) top-K candidates, re-score with the best LLM/mode, and
measure Recall@1%FPR / Precision@top-N of the two-stage system vs classical-alone and LLM-alone at
matched cost. Reuses prompted scores already computed → cheap. Tests RQ7. Turns a likely "LLMs weak
standalone" verdict into a positive operating-point result.

---

## 9. Compute & cost — BUDGET-HYBRID strategy (target ~$30–70 after §9b cuts) [REV: cost-sensitive]
**Decision (2026-06-29): free Kaggle does the bulk; a short, gated paid A100 burst covers only what
free hardware can't (the fp16 14B likelihood runs).** The cost driver is mode A's `r` forward passes/row
on large test sets — controlled by capping rows, tiering `r`, and keeping the paid GPU window tiny.

**Where each piece runs:**
- **Free Kaggle (30 GPU-h/week ≈ 120–150 free hr over the project; T4/P100 16 GB), via Kaggle MCP
  `create_notebook_session` + `get_accelerator_quota`:**
  - Exp 1 reproduction (SmolLM-135M/360M) — fits easily.
  - Exp 2/3 for the **free-tier models: SmolLM-360M, Qwen3-4B** (fp16 on 16 GB), and **Qwen3-8B in
    4-bit** as the larger-but-free point (flagged as quantized — not in the fp16 scale comparison).
  - Caveats: internet off by default, 12 h/session (checkpoint + resume per §10), no persistence
    between sessions, env friction vs the pinned 2024 AnoLLM stack. Call `get_accelerator_quota` before
    each run to stay inside the weekly 30 h.
  - **Colab free (T4)** as overflow when the weekly Kaggle quota is exhausted.
  - **Engine discipline (Gap B):** Kaggle-vLLM is the *single engine* for the whole RQ3 scale ladder
    (≤8B here, 14B on the paid burst) so no cross-engine logprob confound falls inside a comparison.
- **Local Mac (Apple Silicon) — free, no session limits — for ≤4B *non-comparative* work:** SmolLM-360M
  repro anchor, prototyping, and the named-ODDS Exp 3b, via MLX/llama.cpp/HF-MPS. This is the real fix
  for the Kaggle session-management overhead (re-download weights / re-install deps / sync results each
  12 h session), not Colab. **Caveat (Gap B):** different engine than vLLM → NLL can differ; only use Mac
  *inside* a comparison (e.g. as a ladder rung) if the day-1 logprob-parity check (Exp 1) passes.
- **Paid RunPod A100 80GB — ONE short burst, ~12–22 hr total (≈ $25–45 after §9b cuts), gated by §9a:** only the
  **Qwen3-14B fp16** likelihood + prompted runs (the data point free 16 GB can't hold at fp16). Spin up,
  run just the 14B grid (capped rows, tiered `r`), `stop-pod`/`delete-pod` immediately after. Network
  volume optional for such a short burst (can re-pull 14B weights, ~28 GB).
- **Hosted API (OpenRouter/Together/Fireworks), ~$5–30 — optional footnote spot-check only:** one large
  model (GLM-5 / Qwen3.5-large), prompted, scored however is easiest, reported as a one-line "observed X."
  Not a comparand, not in any confirmatory test (§3) — so scoring-method match is irrelevant. Skip
  entirely if it's not quick and clean.

**Cost controls (unchanged, now load-bearing):** cap every large test set to ≈20–40k scored rows
(reweighted, §2c); `r=21` only on cheap sets, `r≈8–10` on expensive ones; vLLM offline batched
inference; pinned Docker image; **`stop-pod` the instant the 14B burst ends.**

**Realistic estimate:** **~$30–70 all-in after the §9b cuts** (short A100 burst ~$25–45 for the
capped-ODDS 14B runs + API $5–30 + buffer); pre-cut ceiling was ~$120. Free Kaggle + local Mac carry
Exp 1 + the small models at $0. Smoke-test throughput on Kaggle/Mac first; only open the paid burst once
the 14B row-budget is known.

**Scientific cost of going cheap:** the fp16 scale axis rests on the single short 14B burst; if even
that is cut, the scale ladder becomes SmolLM-360M → Qwen3-4B → Qwen3-8B(4-bit) — still a trend, but the
top point is quantized. The two load-bearing comparisons (likelihood-vs-prompted, semantic transfer) do
not need 14B and run entirely free.

### 9a. Provisioning via RunPod MCP — short paid burst only, with a hard cost gate [REV — tools verified]
Under the budget-hybrid strategy (§9) RunPod is used for **ONE short burst (~15–25 hr) for the Qwen3-14B
fp16 runs only** — not as the project workhorse. Config: **1× A100 80GB** (or A6000 48GB to halve the
rate), our pinned vLLM **Docker image** (`create-template`/`imageName`). Network volume is **optional**
for so short a burst — re-pulling the 14B weights (~28 GB) is cheaper than weeks of idle volume billing;
skip `create-network-volume` unless the burst spans multiple sessions. **`stop-pod`/`delete-pod` the
moment the 14B grid finishes.** Everything else runs free on Kaggle/Colab.

**Standard provisioning sequence (each cost step gated — see guardrail):**
1. `list-gpu-types` (searchTerm "A100", `minMemoryGb: 80`, `secureCloudOnly`) + `list-data-centers` →
   pick a GPU type + DC that has stock. *(read-only)*
2. **(OPTIONAL — skip for a single-session burst; create only if the 14B work spans sessions)**
   `create-network-volume` (size ≈100, the chosen `dataCenterId`). *(COST — storage; double-confirm)*
3. `create-pod` (`imageName` = our vLLM image, `gpuTypeIds`, `cloudType: SECURE`, `volumeInGb`/
   `volumeMountPath` for the network volume, `dataCenterIds` = same DC, `ports` for SSH/HTTP).
   *(COST — hourly; double-confirm)*
4. Run experiments over SSH; `stop-pod` between sessions (keeps volume, frees GPU billing); `start-pod`
   to resume. `delete-pod` only when fully done. *(there is NO "terminate" — `delete-pod` is terminate.)*

> ## 🛑 COST GUARDRAIL — non-negotiable
> **No cost-incurring RunPod action is ever taken without TWO explicit user confirmations.**
> - **COST / DOUBLE-CONFIRM REQUIRED:** `create-pod`, `start-pod`, `update-pod` (disk/volume changes),
>   `create-network-volume`, `update-network-volume` (size up), `create-endpoint`, `update-endpoint`
>   (raises `workersMin`), `run-endpoint` / `runsync-endpoint` (consume serverless credits per call).
>   Protocol: (1) state exactly what will be created + the $/hr or per-call cost, ask "confirm?";
>   (2) on yes, ask once more "final confirm — provisioning now?"; only then invoke.
> - **DESTRUCTIVE / DOUBLE-CONFIRM (data loss):** `delete-pod`, `delete-network-volume`,
>   `delete-endpoint`, `delete-template`.
> - **Encouraged, single ack:** `stop-pod` (this SAVES money — only confirm it won't interrupt a live run).
> - **Read-only (no confirm):** `list-pods`, `get-pod`, `list-endpoints`, `get-endpoint`,
>   `endpoint-health`, `get-job-status`, `list-gpu-types`, `list-data-centers`, `list-templates`,
>   `list-network-volumes`, `get-network-volume`.
> - **Always** remind to `stop-pod` when a session ends — idle pods keep billing. Network volume keeps
>   billing (small $/GB-mo) even when the pod is stopped; `delete-network-volume` only when fully done.
> - Enforce in `settings.json` (deny/ask permission rule on the RunPod write tools) so the gate is
>   mechanical, not just procedural — offered as an optional hardening step.

**The experiment runner never auto-spins a pod** — provisioning is always a manual, human-gated step.
See `runpod-cost-guardrail` in project memory.

### 9b. Adopted cost cuts (target <$100) [REV — external suggestion, refined]
External cost-reduction suggestions, taken with researcher edits so savings don't cost credibility:

| Cut | Decision | Rationale / guardrail |
|---|---|---|
| Fewer seeds | **3 seeds, not 5** (global) | report transparently; CIs widen but fine for a v1. Updates §2c/§6/§7. |
| Lower `r` | **Cache per-permutation NLLs** → r-sensitivity curve (5/10/21) is **free post-hoc** (average prefixes); run confirmatory at **r=10**, **r=5 expensive**, r=21 on the ~3 small curve datasets | citable robustness result at ~zero extra cost. Updates §4a/§10. |
| Skip mode A on security | **Yes on UNSW; keep mode A on credit-card for ONE model** | r-permutation cost concentrates on big security sets; the likelihood-vs-prompted A/B still lives on all of ODDS. Aligns with the operating-regime framing (security Q = "can prompted compete with classical"). Partial credit-card A/B retained. Updates Exp 3. |
| Cap ODDS | **Keep all 30 for the free small models** (SmolLM-360M, Qwen3-4B — preserves CD diagram + AnoLLM comparability); **cap to ~12 representative sets ONLY for the paid 14B burst** | small models are free on Kaggle, so don't sacrifice the headline replication; cap only where compute is actually expensive. State the 12-set selection criterion (span size/dimensionality). Updates Exp 1/2. |
| Fewer models | **Keep SmolLM-360M (repro anchor) + Qwen3-4B + Qwen3-14B (paid burst)** | do NOT collapse to SmolLM+4B — that's a cross-family pair, so a "scale" trend is confounded. RQ3 scale needs a same-family Qwen ladder (4B→14B, or free 8B-4bit if 14B is cut). |

**Revised estimate with these cuts: ~$30–70 all-in** (short A100 burst for the capped-ODDS 14B runs +
small hosted-API ceiling; free Kaggle carries everything else). Comfortably under $100.

---

## 10. Repository, reproducibility & hygiene [REV: repro C1–C4, M1–M6]
```
Project_AnomalyDetectionSurvey/
├── README.md  PLAN.md  project_idea.md  DATA_LICENSES.md
├── Dockerfile               # prebuilt image (tag, not digest) for the paid A100 burst; documents CUDA/torch/vLLM
├── requirements.txt + env/anollm_repro.lock   # pinned deps; Exp-1 lock incl. PyOD/DeepOD pins
├── configs/                 # simple YAML of axis-LISTS (model/dataset/scoring/seed); a runner loops the
│   │                        #   Cartesian product — NO Hydra, NO per-combo files
│   ├── model/  dataset/  scoring/  experiment/
├── third_party/AnoLLM/      # git submodule -> OUR FORK; tag `upstream-repro` (exact SHA) + ext branch
├── src/
│   ├── data/                # loaders (download+hash; Kaggle via MCP §2d), serialize.py (orderings)
│   ├── scoring/             # likelihood.py (vLLM prompt_logprobs), prompted.py (expected-value scorer)
│   ├── baselines/  metrics/  eval/ (exp1..6 runners)  triage/ (Exp 6)
│   └── utils/               # RunMetadata, seeding, timing, cost accounting, secret redaction
├── data/                    # GITIGNORED; documented expected layout only
├── results/
│   ├── raw/                 # one JSON per (model,mode,dataset,seed); atomic write; status field;
│   │                        #   mode A stores PER-PERMUTATION NLLs (→ free r-sensitivity, §4a)
│   │   └── .../scores.jsonl # per-row checkpoint (prompted), input-hashed, resumable
│   ├── MANIFEST.jsonl       # expected grid; aggregation diffs actual vs expected, refuses if incomplete
│   ├── tables/  figures/    # derived; `make tables`/`make figures` regenerate deterministically
├── notebooks/               # exploratory only; nbstripout; src never imports from here
├── paper/ (main.tex sections refs.bib)
└── tests/                   # property-based metric tests + determinism test
```
**Scope note [REV — lean for a solo, <$100 first paper]:** keep the practices that protect *correctness*
of the headline numbers; drop pure infrastructure. **Dropped:** W&B (raw JSON is the system of record →
a small aggregation script suffices), Hydra (simple YAML + Cartesian-loop runner), Hypothesis framework
(replaced by targeted pytest cases), Docker digest-pinning (prebuilt image tag + documented CUDA is
enough). **Kept / elevated** below.

**Mandatory practices:**
- **Resumption/persistence [repro-C1 — ELEVATED on free Kaggle]:** atomic unit = one
  (model,mode,dataset,seed) JSON, written on completion, named deterministically with config hash;
  runner skips existing valid cells. Per-row JSONL checkpoint for prompted scoring. **This matters MORE
  on the cheap path:** free Kaggle sessions are 12 h with no persistence, so a long run must resume, not
  restart. Sync `results/raw/` + weight cache to a persistent store (Kaggle Dataset output / Drive /
  cheap object store) between sessions; never trust ephemeral box disk. Writes are `tmp→fsync→rename`.
- **Completion manifest [repro-C2]:** each JSON carries `status` + `n_rows_scored/expected`; aggregation
  refuses to run on missing/partial cells and prints the gap matrix.
- **RunMetadata schema [repro-C3]:** auto-populated, asserted non-null, embedded in every JSON: HF
  **revision commit hash**, quantization method+config+lib version, **inference engine
  (vLLM/MLX/llama.cpp/API) + logprob-parity status**, vLLM/transformers/torch/CUDA/driver + **GPU model**,
  decode/sampling config + `prompt_logprobs` setting + r, **rendered-prompt hash**,
  **serialization-template hash**, dataset content hash + **Kaggle dataset version id** + **split/subsample
  index hash**, git SHA, AnoLLM ref used. Secrets (`*_API_KEY`, `*_TOKEN`, HF token) explicitly redacted.
- **Dataset hygiene [repro-C4/M4]:** never commit datasets (`.gitignore data/`); ship pinned loaders +
  version IDs + content hashes; `DATA_LICENSES.md` records each dataset's license (credit-card = ODbL),
  source, citation, basis for use. Kaggle pulls go through the MCP/loader interface in §2d.
- **Config [SIMPLIFIED — was repro-M1/Hydra]:** one YAML listing axis *lists* (models, datasets, scoring
  modes, seeds); a runner takes the Cartesian product. No Hydra, no per-combo files; the "expected grid"
  is derived from the YAML for the completion manifest.
- **Tracking [SIMPLIFIED — W&B dropped]:** raw JSON in `results/raw/` is the sole system of record; a
  deterministic `make tables` aggregation script reads it. Per-run `cost.json` lives in `results/raw/`
  (cost is a metric). No external tracker dependency.
- **Forking [repro-M3 — KEPT]:** AnoLLM = submodule of our fork; `upstream-repro` tag (unmodified SHA)
  for Exp 1, extension branch for Exp 2+; pin their PyOD/DeepOD in the lock.
- **Tests [repro-M5 — KEPT as targeted pytest, not Hypothesis]:** ~6 plain unit tests on the bug-prone
  metric edges (these protect the headline number): AUROC label-flip symmetry (positive-class
  orientation) + =0.5 for constant scores; **AUPRC random-ranker baseline ≈ prevalence at
  {0.17%,5%,50%}**; Recall@1%FPR interpolation golden test + `<100`-negatives edge; P@K/R@K
  tie-at-boundary; expected-value scorer + parser edge cases; **determinism test** (same config,seed →
  identical scores). Pin the analysis env (sklearn AUPRC edge behavior drifts across versions).
- **Secrets [repro-M6]:** env vars only, untracked `.env` (+`.env.example`), `gitleaks` pre-commit,
  tracker env-capture disabled/redacted. (Kaggle MCP credentials handled by the MCP server, not in repo.)

---

## 11. Risk register (top)
| Risk | Mit. |
|---|---|
| Budget blow-up via r×rows×UNSW | row-arithmetic spreadsheet; cap all large sets; r tiered; 3 models; smoke-test early |
| Exp 1 env hell (vLLM/torch/DeepOD) | 5-day budget; Docker; transformers logprob fallback |
| Prompted granularity confound | expected-value scorer (default); tie-aware AUROC; ceiling analysis |
| Subsampling biases AUPRC | importance-reweight negatives; frozen eval set for all methods; bootstrap CIs |
| Leakage (UNSW `ct_*`/IDs, credit-card `Time`) | single-feature-AUROC screen; pre-registered split policy; dropped-col list |
| "Just AnoLLM + newer models" | reframe to operating-regime; cite/differentiate Li 2024/AD-LLM/blog; add Exp 6 |
| No positive result if H3 flat | Exp 6 gives a constructive result independent of H3 |
| Lost runs on ephemeral GPU | per-cell atomic JSON + object-store + manifest + resumption |
| Accidental/forgotten RunPod spend | **double-confirm gate on all RunPod write tools (§9a)**; stop/terminate when idle; settings.json deny/ask rule |
| Cross-engine logprob mismatch (Mac vs vLLM) [Gap B] | day-1 parity gate (Exp 1); else keep the RQ3 ladder on one engine; Mac only for non-comparative work |
| Kaggle session-management overhead eats wall-clock | run ≤4B locally on Mac; resumable per-cell JSON; batch many cells per session; sync raw/ to persistent store |

---

## 12. Timeline (~4–5 weeks part-time, buffered) [REV: feas-M5]
- Days 1–5: Exp 1 reproduction (free Kaggle/local) + **engine-parity check (Gap B)** + env/infra
  (RunMetadata, metrics, tests). Gate — Days 1–5 tell you whether the rest of the timeline holds.
- Days 6–12: Exp 2 (ODDS, both modes) + prompted expected-value scorer + prompt-sensitivity.
- Days 11–18: security loaders (UNSW subsample, leakage screen; Kaggle MCP for credit-card) + Exp 3 + Exp 3b.
- Days 16–22: Exp 4 (orderings), Exp 5 (Pareto), Exp 6 (two-stage triage).
- Week 4–5: stats (CD/Wilcoxon/Holm on ODDS; bootstrap on security), figures, write-up.
  **Abstract + title rewritten last.**

---

## 13. Paper outline & result-contingent narratives
1. Intro — operating-regime framing (not "gap closed"); honest prior-gap statement.
2. Related work — AnoLLM, Li et al. 2024, AD-LLM, GReaT, TabLLM, ADBench, CausalTAD, GPT-4 blog, "LLM as
   Algorithmist" — each differentiated (what they did / didn't: no same-model A/B, no open-weight scale
   sweep, no operational/security/fixed-FPR, no two-stage).
3. Method (two scoring modes incl. expected-value scorer; serialization; metrics+reweighting).
4. Datasets. 5. Experiments. 6. Results. 7. Practicality (Pareto). 8. Two-stage triage.
9. Discussion. 10. Limitations + future work (few-shot; full serialization matrix; CausalTAD reweighting;
   richer two-stage pipeline; **cross-engine logprob parity** as a stated threat-to-validity; 3-seed
   CIs; the large-model ceiling reported only as a footnote spot-check, not a comparand). 11. Conclusion.

**Discussion pre-written for all outcomes:** classical still wins → "modern open LLMs improved but
remain costlier/weaker for high-volume numeric, *and collapse under fixed-FPR budgets*"; LLMs close gap
on semantic/mixed → the interesting middle (tie to Exp 3b semantic ablation); LLMs weak standalone but
**Exp 6 shows a better operating point as a second stage** → the constructive headline.

**Target venues:** DMLR (primary) — but note one reviewer's caution that without Exp 6 + the reframing,
the ceiling is arXiv/workshop. arXiv preprint first.
