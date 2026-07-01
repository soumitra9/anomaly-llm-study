#!/usr/bin/env bash
# M2 fleet pod bootstrap — deterministic, idempotent, self-verifying.
#
# Prepares a fresh (or recovered) RunPod A40 to run its shard of the M2 Exp-2 fleet. Safe to re-run:
# a re-run after a pod death/balance-loss re-stages anything missing and re-verifies, then exits 0.
#
# PREREQUISITES scp'd to the pod BEFORE running (by the launcher):
#   /workspace/adbench_classical.tgz   — the 27 adbench ODDS npz (deterministic staging, NOT the flaky downloader)
#   /workspace/m2_code.tgz             — the 3 uncommitted M2 files (exp2_fleet.py, qwen_hparams.yaml, prompted.py)
#
# USAGE:  bash pod_bootstrap.sh "<datasets csv>" "<specials csv | none>"
#   e.g.  bash pod_bootstrap.sh "speech,wine,breastw,cardio,ecoli" "none"
#         bash pod_bootstrap.sh "arrhythmia,lymphography,vertebral,wbc,yeast" "arrhythmia"
# Exits 0 only if EVERY dataset in the shard loads. Any failure -> non-zero + a clear BOOTSTRAP FAIL line.
set -uo pipefail

DATASETS="${1:?need datasets csv}"
SPECIALS="${2:-none}"
REPO=/workspace/anomaly-llm-study
REPO_URL=https://github.com/soumitra9/anomaly-llm-study.git

echo "[bootstrap] $(date -u) datasets=$DATASETS specials=$SPECIALS"

# 1) repo (clone once; recovery re-runs skip this)
if [ ! -d "$REPO/.git" ]; then
  echo "[bootstrap] cloning + submodule..."
  git clone --recurse-submodules "$REPO_URL" "$REPO" || { echo "BOOTSTRAP FAIL: git clone"; exit 11; }
fi
cd "$REPO" || { echo "BOOTSTRAP FAIL: cd repo"; exit 12; }
git submodule update --init --recursive >/dev/null 2>&1

# 2) env (uv sync is fast when already synced)
echo "[bootstrap] uv sync..."
uv sync >/dev/null 2>&1 || { echo "BOOTSTRAP FAIL: uv sync"; exit 13; }

# 3) code overlay — the 3 uncommitted M2 files (push to main was gated, so we scp+overlay)
if [ -f /workspace/m2_code.tgz ]; then
  tar xzf /workspace/m2_code.tgz -C "$REPO" || { echo "BOOTSTRAP FAIL: m2_code extract"; exit 14; }
  echo "[bootstrap] code overlay applied"
fi
# sanity: the fleet runner + Qwen table must exist post-overlay
[ -f "$REPO/scripts/exp2_fleet.py" ] || { echo "BOOTSTRAP FAIL: exp2_fleet.py missing"; exit 15; }
[ -f "$REPO/configs/qwen_hparams.yaml" ] || { echo "BOOTSTRAP FAIL: qwen_hparams.yaml missing"; exit 16; }

# 4+5) DATA — prefer the GOLDEN bundle (all 30 datasets pre-built + specials, proven to load): fully
# deterministic, no npz-build, no network fetch. Fall back to Classical-tarball + fetch only if absent.
mkdir -p "$REPO/data"
if [ -f /workspace/data_golden.tgz ]; then
  tar xzf /workspace/data_golden.tgz -C "$REPO/data" 2>/dev/null || { echo "BOOTSTRAP FAIL: golden extract"; exit 17; }
  echo "[bootstrap] golden data bundle staged ($(ls "$REPO/data" | wc -l) dataset dirs)"
else
  CLASS="$REPO/.venv/lib/python3.10/site-packages/adbench/datasets/Classical"
  mkdir -p "$CLASS"
  [ -f /workspace/adbench_classical.tgz ] && tar xzf /workspace/adbench_classical.tgz -C "$CLASS" 2>/dev/null
  [ -f /workspace/data_caches.tgz ] && tar xzf /workspace/data_caches.tgz -C "$REPO/data" 2>/dev/null
  if [ "$SPECIALS" != "none" ]; then
    echo "[bootstrap] fetching specials ($SPECIALS)..."
    bash scripts/fetch_special_datasets.sh || { echo "BOOTSTRAP FAIL: fetch_special_datasets"; exit 18; }
  fi
  echo "[bootstrap] fallback staging done (Classical + caches + specials)"
fi

# 6) VERIFY every dataset in the shard actually LOADS (the no-surprise gate before any GPU spend)
echo "[bootstrap] verifying dataset loads..."
DATASETS="$DATASETS" uv run python - <<'PY'
import os, sys
from anodet.data.odds import load_odds
ds = os.environ["DATASETS"].split(",")
bad = []
for d in ds:
    d = d.strip()
    try:
        o = load_odds(d, split_idx=0, n_splits=5)
        print(f"  ok {d}: X_train{o['X_train'].shape} X_test{o['X_test'].shape} anom={int(o['y_test'].sum())}")
    except Exception as e:
        bad.append((d, type(e).__name__, str(e)[:120]))
        print(f"  FAIL {d}: {type(e).__name__}: {str(e)[:120]}")
if bad:
    print("BOOTSTRAP FAIL: datasets did not load:", [b[0] for b in bad]); sys.exit(19)
print("[bootstrap] all datasets load OK")
PY
rc=$?
[ $rc -eq 0 ] || { echo "BOOTSTRAP FAIL: verify rc=$rc"; exit $rc; }
echo "BOOTSTRAP OK $(date -u)"
