# Running the Exp-1 reproduction gate on Kaggle (GPU)

The runner (`anodet.eval.exp1` via `scripts/kaggle_gate.py`) is the SAME code validated locally on
Mac/CPU. On Kaggle it runs on a CUDA T4/P100. Validate the CUDA path with the **trial** before the
full 30-set gate (free quota is 30 GPU-h/week — scarce).

## Step 0 — get the code onto Kaggle (pick one; see "Decision" below)

**Option A — clone from GitHub (recommended once the `soumitra9` remote exists):**
```bash
git clone --recurse-submodules https://github.com/soumitra9/<repo>.git
cd <repo>
```
(Public repo → no auth needed for the Kaggle clone. The AnoLLM submodule is public.)

**Option B — no GitHub: clone the fork + attach our code as a Kaggle Dataset:**
- Upload `anodet/`, `scripts/`, `pyproject.toml`, `uv.lock` as a Kaggle Dataset (via the Kaggle MCP
  `upload_dataset_file`), attach it to the notebook, and `git clone` the AnoLLM fork from upstream into
  `third_party/AnoLLM`. More moving parts; use only if we skip GitHub.

## Step 1 — environment (Kaggle notebook, Internet ON)
```bash
pip install uv
uv sync --frozen        # reproduces our pinned stack (torch 2.3.1, transformers 4.48.2, ...)
```
(uv installs into a project venv; run subsequent commands with `uv run`. If uv's CUDA torch wheel
fights Kaggle's preinstalled CUDA, fall back to `pip install -e . --no-deps` + the pinned reqs — but
try `uv sync` first; the lockfile is the reproducibility artifact.)

## Step 2 — TRIAL (validate CUDA path, ~tiny quota)
```bash
uv run python -m scripts.kaggle_gate --datasets lymphography,wine,breastw --models smol-360 --splits 1
```
Expect sane AUROC (breastw ≈ 0.98–0.99, in AnoLLM's ballpark). Confirms CUDA fine-tune + NLL scoring
works remotely. Per-cell JSON lands in `results/raw/exp1_repro/`.

## Step 3 — FULL gate (only after the trial passes)
```bash
uv run python -m scripts.kaggle_gate --full     # 30 ODDS x 5 splits x {smol, smol-360}
```
Then compare per-dataset AUROC/AUPRC to AnoLLM's published tables (PLAN §7 gate: aggregate mean within
~1 pt + per-dataset rank correlation + per-dataset band vs published ±std). Download
`results/raw/exp1_repro/` as the notebook output and sync into the repo.

## Notes
- Single-process is fine on 1 GPU — `anodet/_fork.py` inits a 1-rank gloo group (the shipped
  `train_anollm.py` torchrun/nccl multi-GPU path is NOT needed).
- `USE_TF=0` is set automatically by `_fork.setup_env()`.
- Resumable: re-running skips cells whose JSON is already `complete` (survives the 12 h session limit).

## Decision needed: code delivery (A vs B)
Option A needs the project pushed to a **public `soumitra9` GitHub repo** once (`gh` not installed
locally — install it or create the repo + push with a token). Option B avoids GitHub but is clunkier.
Recommended: do the one-time GitHub push (it's also the project's real home + needed for publishing).
