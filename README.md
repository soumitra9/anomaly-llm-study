# Tabular LLM Anomaly Detection — Scoring Mode, Scale, and Operating Regime

A replication + extension study of open-weight LLMs for tabular anomaly detection (security domains),
building on **AnoLLM** (ICLR 2025). See [`PLAN.md`](PLAN.md) for the research design and the approved
implementation plan under `~/.claude/plans/` for the build order.

## Status

**M1–M6 all complete. No active pods. Spend ≈ $141.41.**

M1 (90/90, partial repro). M2 (360/360: likelihood ≫ prompted; no Qwen scale gain; Friedman p=6×10⁻¹²).
M3 (66/66: security transfer + semantic ablation). M3.5 (T3+BA1+DA1 confound checks all PASS).
M4 (33/33: ordering ablation + triage; both negative results). M6 (stats, figures, §4 results, §5 discussion).
85 unit tests pass. See `ROADMAP.md` for full milestone table.

## Resuming in a new session (read these, in order)

If context is lost, this fully re-orients an assistant:

1. **Memory `docs/claude/memory/project-state.md`** (or `~/.claude/projects/.../memory/project-state.md`) — what's done / what's
   next, the env recipe, key findings, exact reproduction commands. *(Best single file.)*
2. **Approved build plan** — `docs/claude/plans/i-need-to-plan-ancient-dawn.md` (milestones M0–M6; ★★ POST-M2 = M3 onward).
3. **`PLAN.md`** (this repo) — the research design v1.0 (RQs, datasets, scoring modes, metrics, budget).
4. **This repo** — `git log --oneline`, the two `scripts/smoke_*.py` drivers, `pyproject.toml` + `uv.lock`.

**Orientation line to paste:** *"Resuming the anomaly-detection project. Read memory `project-state.md`,
then `ROADMAP.md`, then `PLAN.md`. M1–M6 complete; no active pods; spend ≈$141.41. Next step: LaTeX paper draft.
Use **uv**; package is `anodet`; honor the RunPod double-confirm cost gate."*

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
  code/analysis; RunPod spend is double-confirm gated. See `results/SUMMARY.md` for actual spend.

## Reproducibility

The file system is the system of record (see the implementation plan's *Traceability* section): every run
emits a JSON with full `RunMetadata` (git SHA, `uv.lock` hash, model revision, LoRA config, data/split
content hashes, prompt/serialization hashes, cost), reconciled against `results/MANIFEST.jsonl`.
