# Implementation Plan — Building & Executing the Tabular-LLM Anomaly-Detection Study

## Context

`PLAN.md` (v1.0) is the *research* design; the repo is currently empty except `PLAN.md` and
`project_idea.md`. This plan converts that design into a concrete build + run order.

Exploration of the AnoLLM source (amazon-science, Apache-2.0) surfaced one fact that reshapes the build:
**mode A (likelihood) is per-dataset *fine-tuning*, not frozen inference.** AnoLLM fine-tunes the
backbone on each dataset's normal rows (HF `Trainer`, ~2000 steps, optional PEFT LoRA) and scores NLL via
`decision_function()` over r=21 column permutations — pure **HF Transformers + PEFT, no vLLM**. This
corrects `PLAN.md §4a` (which wrongly says "vLLM `prompt_logprobs`, single prefill") and reshapes compute
(training-dominated on small sets), the engine story, and the A/B framing.

**Outcome of this plan:** a forked-AnoLLM-based repo that (1) reproduces AnoLLM as a hard gate, then
(2) adds the prompted scoring mode, security datasets, operational metrics, and the two-stage triage —
runnable almost entirely free (Kaggle + local Mac), with one short cost-gated A100 burst for 14B.

## Decisions locked (this session)

1. **Mode A = fine-tune the INSTRUCT checkpoint with LoRA** (Exp 2+). Mode B = the **same instruct
   weights, frozen**, prompted. ⇒ both modes start from identical base weights, so the only variable is
   the scoring method → clean same-model A/B (the paper's headline). Exp 1 still reproduces AnoLLM
   faithfully (base checkpoint + full FT on SmolLM). Disclose instruct+LoRA as a deliberate deviation;
   it is *more* generous to the A/B (if likelihood still loses from the same weights, that's a stronger
   finding). SmolLM-360M base+full-FT (Exp 1) vs instruct+LoRA (Exp 2) gives a near-free
   FT-method/base-vs-instruct sensitivity note.
2. **Engine = HF Transformers + PEFT everywhere. No vLLM in v1.** Mode A must be HF anyway; vLLM would
   only speed the cheap mode B. This dissolves Gap B entirely (Mac-MPS and Kaggle/A100-CUDA both run HF)
   and removes the top risk (vLLM↔torch-2.3.1 env hell). Mode-B inference is slower but fine on the
   capped 20–40k-row eval sets. Revisit vLLM only if M2 smoke test shows mode B is prohibitively slow.

## Tooling & environment (locked)

- **Package/env manager = `uv` for everything.** No pip/conda/venv. Deps live in `pyproject.toml`,
  locked in `uv.lock` (this replaces `requirements.txt` and *is* a core traceability artifact). All
  commands run via `uv run …`; env created with `uv sync`. The `Dockerfile` installs `uv` and runs
  `uv sync --frozen`. Torch is pinned per-platform via uv index config (`[tool.uv.sources]` /
  extra-index): the CUDA wheel on Kaggle/A100, the MPS/CPU wheel on Mac — this is exactly what makes the
  "HF everywhere" engine decision portable across Mac ↔ Kaggle ↔ A100 from one lockfile.
- **GitHub = personal account `soumitra9` (https://github.com/soumitra9), via plain `git` + personal
  `gh`.** NEVER the connected GitHub MCP (it defaults to Autodesk Enterprise `git.autodesk.com` and can't
  reach personal/public repos). Project repo + the AnoLLM fork both live under `soumitra9`.

## Repo layout

Target = `PLAN.md §10` (lean: no Hydra/W&B/Hypothesis). Fork AnoLLM as a submodule and build extensions
around it.

```
third_party/AnoLLM/   # git submodule → soumitra9 fork; tag `upstream-repro` (unmodified SHA) + `ext` branch
src/{data,scoring,baselines,metrics,eval,triage,utils}/   configs/   tests/   results/{raw,tables,figures}/
data/ (gitignored)   Dockerfile (uv-based)   pyproject.toml + uv.lock (uv-managed)   DATA_LICENSES.md
```

## Reuse map (fork = source of truth; do not reimplement)

| Need | Action | Fork file to call |
|---|---|---|
| ODDS load (.mat → X,y) | **wrap** | `src/data_utils.py::load_dataset` |
| Numeric "standard" binning (StandardScaler→round 1dp) | **reuse** | `src/data_utils.py::normalize` |
| Row→text serialization + column permutation | **reuse** | `anollm/anollm_dataset.py` (serialize, `shuffle_column_order`) |
| Mode A fine-tune + NLL score | **wrap** | `anollm/anollm.py::AnoLLM.fit` (LoRA path) + `decision_function`; `train_anollm.py`, `evaluate_anollm.py` |
| Classical baselines (14: 4 PyOD + 8 DeepOD + ICL + DTE) | **wrap** | `evaluate_baselines.py` |
| Exp 1 reproduction | **call shipped, unmodified** | `scripts/exp2-odds/run_anollm.sh`, `run_baselines.sh` (+ exp1-mixed) |

**Build new** (AnoLLM has none of these): `src/scoring/prompted.py` (mode B), `src/metrics/`,
`src/eval/` runners, `src/triage/` (Exp 6), `src/utils/` (RunMetadata/manifest), `configs/`, `tests/`,
new loaders `src/data/{creditcard.py,unsw.py}` + `src/data/odds_names.py` (Exp 3b name injection).

## Build milestones

**M0 — Skeleton + utils + tests (local Mac, $0).** `uv init` the project; create `src/` layout.
Create the project repo + fork AnoLLM **under `soumitra9`** (`gh repo fork` with personal auth), add the
fork as a submodule at `third_party/AnoLLM/` (`upstream-repro` tag on the unmodified SHA + `ext` branch).
Build `src/utils/run_metadata.py` FIRST (RunMetadata schema — see Traceability below; atomic
`tmp→fsync→rename`; completion manifest; `cost.json`; secret redaction). Author `configs/` YAML
axis-lists + Cartesian-loop runner skeleton. Write the **6 metric pytest tests** (`uv run pytest`) before
`src/metrics/` is wired (TDD on the bug-prone numbers).

**M1 — Exp 1 reproduction = THE GATE (free Kaggle + Mac, $0).** Express AnoLLM's pinned stack in
`pyproject.toml` and lock with `uv` → `uv.lock` (py3.10, torch 2.3.1 [platform index], transformers
4.48.2, peft 0.11.1, pyod 2.0.1, deepod 0.4.1, datasets 2.20.0, scikit-learn 1.6.1); `Dockerfile` =
`uv sync --frozen`. Manually stage ODDS `.mat` into `data/{name}/`. Run shipped scripts unmodified via
`uv run` (base SmolLM-135M/360M, full FT, r=21). **Gate (`PLAN §7`):** mean AUROC within ~1 pt of published + high per-dataset rank
correlation + each dataset within its published ±std band. Record `.mat` content hashes so a mismatch
implicates code, not data. **Hard stop — do not proceed until it passes.** Fallback already primary
(HF transformers logprob path; no vLLM).

**M2 — Mode B scorer + Exp 2 on ODDS (free Kaggle/Mac, $0).** Build `src/scoring/prompted.py`
(expected-value `Σ p(k)·k` over verbalizer-token logprobs, frozen instruct, HF logits, single forward
pass) and `src/scoring/likelihood.py` (wraps fork fit+score on the **instruct checkpoint with LoRA**;
caches **per-permutation NLLs** → free r-sensitivity curve). Run {mode A LoRA-FT, mode B} ×
{SmolLM-360M-Instruct, Qwen3-4B-Instruct} × 3 seeds × 30 ODDS. Tests RQ2/RQ3 + CD diagram. Reuse fork
serialization so the row text is identical across modes.

**M3 — Security loaders + Exp 3/3b (free Kaggle/Mac + start small burst).** `src/data/creditcard.py`
(Kaggle MCP, pin v3, hash), `src/data/unsw.py` (`nids-datasets` `Network-Flows` subset, stratified
~200–400k, leakage screen + dropped-col list per `PLAN §2c`). **Exp 3** = mode B + classical on
creditcard+UNSW; mode A on creditcard for ONE model only (`PLAN §9b`). **Exp 3b** = semantic vs
anonymized names on **`pima`** (`breastw` backup) — Day-0 sub-step: recover UCI names + align to ODDS
`.mat` column order before coding (`src/data/odds_names.py`).

**M4 — Exp 4/5/6 (free).** Exp 4 serialization orderings; Exp 5 accuracy-vs-cost Pareto; **Exp 6
two-stage triage** (`src/triage/`, reuses computed prompted scores → cheap; the constructive result).

**M5 — Paid A100 burst, 14B only (cost-gated).** Qwen3-14B-Instruct + LoRA, mode A & B, on the ~12-set
ODDS subset + capped security. **Only after** M2/M3 free work validates and the row-budget is known.
RunPod via MCP under the §9a double-confirm gate; `stop-pod`/`delete-pod` immediately after.

**M6 — Stats, figures, write-up.** CD/Wilcoxon/Holm on ODDS; bootstrap CIs on security; `make tables`/
`make figures`; abstract + title last.

**Critical path:** M0 utils/tests → M1 gate → M2 (the load-bearing A/B) → M5 (only the 14B scale point).
Exp 3b/4/6 hang off M2 outputs and parallelize. The 14B burst is *not* on the critical path for the two
headline comparisons (A/B and semantic transfer both run free).

## Compute mapping & cost

| Work | Where | ~GPU-h |
|---|---|---|
| Exp 1 repro (SmolLM full-FT, ~36 sets) | free Kaggle/Mac | 8–15 |
| Exp 2 mode A LoRA-FT (2 models × 30 ODDS × 3 seeds ≈ 180 short runs) | free Kaggle/Mac | 25–45 |
| Exp 2 mode B + Exp 3/3b/4/5/6 | free Kaggle/Mac | ~20 |
| Qwen3-14B (mode A+B, capped) | **paid A100, ~12–22 h** | **$25–45** |

Free-tier binding constraint is the **30 GPU-h/week Kaggle quota** (mode A = many short LoRA trainings),
so resumable per-cell JSON + `get_accelerator_quota` before each session are load-bearing; free compute
spans ~3–4 Kaggle weeks. All-in ≈ **$30–70**.

## PLAN.md corrections to apply during M0 (consequences of the fine-tuning finding)

- **§4a:** rewrite mode A as *fine-tune (instruct+LoRA) then `decision_function` NLL over r perms*; drop
  "vLLM `prompt_logprobs`." Keep per-permutation caching (still valid on the `(n,n_perm)` output).
- **§3 / §4c:** A/B is "same instruct base weights, two recipes (LoRA-adapted for A, frozen for B)" —
  the only variable is the scoring method. Note Exp 1 = faithful base+full-FT reproduction.
- **§9 / §9a / §9b:** remove vLLM mandates and the "Kaggle-vLLM single engine"; state **HF everywhere**.
  Recompute mode-A cost as LoRA training + r-perm scoring (not single-prefill inference).
- **§3/§5 baselines:** the real panel is **14** (adds RDP, DeepIsolationForest) — sync the list.
- **Gap B:** collapses to a tiny intra-HF Mac-MPS-vs-CUDA float check (no vLLM). Simplify the engine
  discipline + risk-register rows accordingly.

## Traceability & experiment tracking

No external tracker (W&B dropped); the **file system is the auditable system of record**, and the chain
is designed so any number in the paper reconstructs to the exact code + env + data + config that produced
it. Five linked layers:

1. **Per-run record — one JSON per `(model, mode, dataset, seed)`** in `results/raw/<exp>/…json`, written
   atomically (`tmp→fsync→rename`) on completion, with an embedded **RunMetadata** block:
   - **Code:** git SHA of our repo + the AnoLLM submodule ref (`upstream-repro` tag vs `ext` branch).
   - **Env:** the `uv.lock` hash + resolved key versions (torch/transformers/peft/pyod/deepod) +
     inference engine (HF) + device (Mac-MPS / Kaggle-CUDA / A100) + CUDA/driver.
   - **Model:** HF repo **revision commit hash**, checkpoint (instruct), **LoRA config**
     (rank/alpha/target-modules/steps/lr), precision.
   - **Data:** dataset content hash + **split index hash** + **subsample index hash** (+ Kaggle dataset
     version id for creditcard) — so a metric mismatch implicates code, never silent data drift.
   - **Scoring:** mode, r, decode/sampling config, **rendered-prompt hash** + **serialization-template
     hash**, per-permutation NLLs (mode A).
   - **Outcome/ops:** metrics, `status` (`complete|partial`) + `n_rows_scored/expected`, wall-clock,
     token counts, `cost.json` ($ / GPU-seconds). Secrets (`*_API_KEY`, HF token) redacted.
2. **Expected-grid manifest** `results/MANIFEST.jsonl` — derived from the `configs/` axis-lists; the
   aggregator **refuses to build tables** if any expected cell is missing/`partial` and prints the gap
   matrix. This is what makes "resumable on 12h Kaggle sessions" safe — completed cells are skipped, gaps
   are visible.
3. **Human-readable ledger** `results/INDEX.md` (auto-generated from `results/raw/`): one row per run —
   exp, model, mode, dataset, seed, key metric, $, device, git SHA, timestamp — so "what ran, when, on
   what, for how much, with what result" is scannable without a UI.
4. **Deterministic regeneration:** `make tables` / `make figures` rebuild every paper artifact from
   `results/raw/` only (pinned analysis env via uv); committed tables can be diffed against a fresh
   regen to catch drift.
5. **Pre-registration:** the confirmatory tests (`PLAN §1`) and split policies are committed to git
   *before* runs, timestamped by commit — so confirmatory vs exploratory is verifiable after the fact.

(Optional, non-authoritative: a W&B-**offline** or local-MLflow dashboard can be layered as a *read-only
index over* `results/raw/` if a UI is wanted later — but the JSON + manifest remain the source of truth,
so no tracker dependency is on the critical path.)

## Verification

- **Exp 1 gate** as above (aggregate + per-dataset band vs published; data hashes recorded).
- **6 metric property tests** (pytest, written in M0): AUROC label-flip symmetry + =0.5 on constant
  scores; AUPRC random-ranker ≈ prevalence at {0.17%,5%,50%}; Recall@1%FPR interpolation golden test +
  `<100`-negatives edge; P@K/R@K tie-at-boundary; mode-B expected-value scorer + parser edges;
  determinism (same config,seed → identical scores). Pin the analysis env (sklearn AUPRC drift).
- **End-to-end Mac smoke test before any paid spend** (`uv run`): one tiny ODDS set (`wine`/`lympho`)
  through the whole pipeline (mode A LoRA-FT → score → mode B → score → baselines → metrics → JSON →
  manifest → `make tables` → `INDEX.md`); kill mid-run and confirm the runner resumes (skips completed
  cells) and that the manifest flags the gap. Run the Mac-MPS-vs-Kaggle-CUDA logprob parity check here.
  Open the A100 burst only after this + M2 pass.

## Operational notes / residual risks

- **GitHub = personal `soumitra9` only**, via plain `git` + personal `gh` auth. Do NOT use the connected
  GitHub MCP (Autodesk Enterprise default — can't reach personal/public repos). Both the project repo and
  the AnoLLM fork live under `soumitra9`. (A local clone suffices for Exp 1; the remote fork matters for
  our `ext`-branch changes + publishing.)
- **Kaggle MCP** = data path (creditcard v3, hashable). **RunPod MCP** = the 14B burst only, under the
  hard double-confirm cost gate (`runpod-cost-guardrail` in memory; never auto-spin a pod).
- Keep LoRA rank/alpha/target-modules fixed across the scale ladder (so "scale" isn't confounded by
  adapter capacity); log LoRA config in RunMetadata.

## Note — paper writing is a SEPARATE later phase (out of scope for this build)

This plan covers building the repo and running the experiments through results, reasoning, comparative
findings, tables, and figures. **Writing the actual paper is a distinct, later phase** and is NOT part of
this implementation. When all experiments are complete and the findings/comparisons are in hand, the user
will provide (a) a **LaTeX template** and (b) a **paper-writing MCP** (not yet connected). At that point
the task will be to author the paper following real research-writing practice: honest framing per
`PLAN §0/§13`, the operating-regime narrative, the result-contingent discussion, and **proper citation of
prior work where necessary** (AnoLLM, Li et al. 2024, AD-LLM, GReaT, TabLLM, ADBench, CausalTAD, etc.),
mimicking how an actual researcher writes — drawing every claim from the traceable `results/raw/` record.
Do not start writing until the template + MCP are provided.
