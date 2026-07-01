# Tabular LLM Anomaly Detection — Scoring Mode, Scale, and Operating Regime

A replication + extension study of open-weight LLMs for tabular anomaly detection (security domains),
building on **AnoLLM** (ICLR 2025). See [`PLAN.md`](PLAN.md) for the research design and the approved
implementation plan under `~/.claude/plans/` for the build order.

## Status

**M1 reproduction gate COMPLETE** (90/90 cells, SmolLM-360M, 30 ODDS × 3 splits, on a RunPod A40 fleet):
C1 mean PASS + C2 rank PASS; C3 band 19/30 (a code-vs-paper difference in the released fork, not our error)
→ a credible **partial** reproduction (see `GATE_SPEC.md` + `RUNLOG.md`). **M2 Exp-2 is EXECUTING** on a
6-pod A40 fleet: the same-model **likelihood vs prompted** A/B, SmolLM-360M + Qwen2.5-3B × 30 ODDS × 3 seeds
(360 cells; SmolLM @2000 steps, Qwen @1000). 70 unit tests pass. Fleet ops + recovery: `FLEET.md`.

## Resuming in a new session (read these, in order)

If context is lost, this fully re-orients an assistant:

1. **Memory `project-state.md`** (`~/.claude/projects/.../memory/project-state.md`) — what's done / what's
   next, the env recipe, key findings, exact reproduction commands. *(Best single file.)*
2. **Approved build plan** — the latest file under `~/.claude/plans/` (milestones M0–M6, reuse map,
   traceability, verification; top section = current go-forward).
3. **`PLAN.md`** (this repo) — the research design v1.0 (RQs, datasets, scoring modes, metrics, budget).
4. **This repo** — `git log --oneline`, the two `scripts/smoke_*.py` drivers, `pyproject.toml` + `uv.lock`.

**Orientation line to paste:** *"Resuming the anomaly-detection project. Read memory `project-state.md`,
then the plan in `~/.claude/plans/`, then `PLAN.md`. M1 gate done (partial repro); M2 Exp-2 A/B fleet
running on RunPod. Use **uv** for everything; our package is `anodet`; honor the RunPod double-confirm
cost gate."*

**Do NOT re-derive (hard-won):**
- **Env**: uv + Python 3.10; overrides are non-negotiable — `setuptools`, `override-dependencies =
  ["torch==2.3.1","pyod==2.0.1"]`, `USE_TF=0`, single-process **gloo** group (AnoLLM's trainer is
  CUDA/DDP-hardwired). All captured in `uv.lock` + the smoke scripts.
- **Mode A is fine-tuning** (base backbone + LoRA), not frozen inference. Mode B uses the instruct sibling.
- Our package is **`anodet`** (renamed from `src/` to avoid clashing with the fork's own `src/`).
- **RunPod**: never spin up / incur cost without asking the user **twice** (`runpod-cost-guardrail`).

## Quickstart (uv)

```bash
uv sync              # create the env (Python 3.10) from pyproject.toml + uv.lock
uv run pytest        # run the metric / determinism property tests
```

All commands run through **uv** (`uv run …`). No pip/conda/venv.

## Layout

- `anodet/` — our package (renamed from `src/` to avoid clashing with the fork's `src/`): `data`
  (loaders + serialization), `scoring` (`likelihood` = mode A, `prompted` = mode B), `baselines`,
  `metrics`, `eval` (Exp 1–6 runners), `triage` (Exp 6), `utils` (RunMetadata, manifest).
- `third_party/AnoLLM/` — forked AnoLLM submodule (reused for data loading, serialization, fine-tune +
  NLL scoring, and the classical baseline panel).
- `configs/` — YAML axis-lists (model / dataset / scoring / seed); a runner takes the Cartesian product.
- `results/` — `raw/` (one JSON per run, the auditable system of record), `MANIFEST.jsonl`, `INDEX.md`,
  `tables/`, `figures/`.
- `tests/` — metric property tests + determinism test.

## Key engineering decisions

- **Engine:** HF Transformers + PEFT everywhere (no vLLM in v1).
- **Mode A (likelihood):** fine-tune the *base* backbone with LoRA per dataset, then NLL-score over
  r column permutations. **Mode B (prompted):** the *instruct* sibling, frozen; expected-value score
  over verbalizer-token logprobs.
- **Compute:** RunPod A40 fleets (SECURE, ~$0.44/hr each) for GPU work + local Mac (Apple Silicon) for
  code/analysis; RunPod spend is double-confirm gated. Budget ≈ $30–70 total.

## Reproducibility

The file system is the system of record (see the implementation plan's *Traceability* section): every run
emits a JSON with full `RunMetadata` (git SHA, `uv.lock` hash, model revision, LoRA config, data/split
content hashes, prompt/serialization hashes, cost), reconciled against `results/MANIFEST.jsonl`.
