# Tabular LLM Anomaly Detection — Scoring Mode, Scale, and Operating Regime

A replication + extension study of open-weight LLMs for tabular anomaly detection (security domains),
building on **AnoLLM** (ICLR 2025). See [`PLAN.md`](PLAN.md) for the research design and the approved
implementation plan under `~/.claude/plans/` for the build order.

## Status

Implementation **M0** (skeleton + traceability core + metric tests). Nothing trained yet.

## Quickstart (uv)

```bash
uv sync              # create the env (Python 3.10) from pyproject.toml + uv.lock
uv run pytest        # run the metric / determinism property tests
```

All commands run through **uv** (`uv run …`). No pip/conda/venv.

## Layout

- `src/` — `data` (loaders + serialization), `scoring` (`likelihood` = mode A, `prompted` = mode B),
  `baselines`, `metrics`, `eval` (Exp 1–6 runners), `triage` (Exp 6), `utils` (RunMetadata, manifest).
- `third_party/AnoLLM/` — forked AnoLLM submodule (reused for data loading, serialization, fine-tune +
  NLL scoring, and the classical baseline panel).
- `configs/` — YAML axis-lists (model / dataset / scoring / seed); a runner takes the Cartesian product.
- `results/` — `raw/` (one JSON per run, the auditable system of record), `MANIFEST.jsonl`, `INDEX.md`,
  `tables/`, `figures/`.
- `tests/` — metric property tests + determinism test.

## Key engineering decisions

- **Engine:** HF Transformers + PEFT everywhere (no vLLM in v1).
- **Mode A (likelihood):** fine-tune the *instruct* checkpoint with LoRA per dataset, then NLL-score over
  r column permutations. **Mode B (prompted):** the same instruct weights, frozen; expected-value score
  over verbalizer-token logprobs.
- **Compute:** free Kaggle + local Mac (Apple Silicon) for the bulk; one short cost-gated A100 burst for
  the 14B model. Budget ≈ $30–70.

## Reproducibility

The file system is the system of record (see the implementation plan's *Traceability* section): every run
emits a JSON with full `RunMetadata` (git SHA, `uv.lock` hash, model revision, LoRA config, data/split
content hashes, prompt/serialization hashes, cost), reconciled against `results/MANIFEST.jsonl`.
