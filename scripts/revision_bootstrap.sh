#!/usr/bin/env bash
# Revision Phase pod bootstrap — idempotent, self-verifying.
#
# PREREQUISITES scp'd to /workspace BEFORE running:
#   /workspace/revision_data.tgz
#   /workspace/revision_code.tgz
#
# USAGE: bash scripts/revision_bootstrap.sh
set -uo pipefail
REPO=/workspace/anomaly-llm-study
REPO_URL=https://github.com/soumitra9/anomaly-llm-study.git

echo "[revision-bootstrap] $(date -u) start"

if [ ! -d "$REPO/.git" ]; then
  git clone --recurse-submodules "$REPO_URL" "$REPO" || { echo "BOOTSTRAP FAIL: clone"; exit 11; }
fi
cd "$REPO" || exit 12
git submodule update --init --recursive >/dev/null 2>&1

echo "[revision-bootstrap] uv sync..."
uv sync >/dev/null 2>&1 || { echo "BOOTSTRAP FAIL: uv sync"; exit 13; }

if [ -f /workspace/revision_code.tgz ]; then
  tar xzf /workspace/revision_code.tgz -C "$REPO" --no-same-owner || { echo "BOOTSTRAP FAIL: code overlay"; exit 14; }
  echo "[revision-bootstrap] code overlay applied"
fi

mkdir -p "$REPO/data"
if [ -f /workspace/revision_data.tgz ]; then
  tar xzf /workspace/revision_data.tgz -C "$REPO/data" --no-same-owner || { echo "BOOTSTRAP FAIL: data extract"; exit 15; }
  echo "[revision-bootstrap] data bundle staged"
else
  echo "BOOTSTRAP FAIL: /workspace/revision_data.tgz missing"; exit 16
fi

mkdir -p /workspace/results/logs/revision /workspace/results/raw/exp3_security /workspace/results/raw/exp2_fewshot

echo "[revision-bootstrap] verify loads..."
uv run python - <<'PY'
import pandas as pd
from anodet.data.creditcard import load_creditcard
from anodet.data.unsw import prepare_unsw
from anodet.data.odds import load_odds
cc = load_creditcard("data/creditcard.csv", split="temporal", seed=0)
assert int(cc["y_test"].sum()) == 492
u = prepare_unsw(pd.read_parquet("data/unsw.parquet"), seed=0)
assert len(u["y_test"]) > 0
for d in ["arrhythmia", "breastw", "cardio", "ionosphere", "shuttle", "speech", "vertebral", "yeast"]:
    o = load_odds(d, split_idx=0)
    print(f"  ok {d}: train{o['X_train'].shape} test{o['X_test'].shape}")
print("[revision-bootstrap] all loads OK")
PY
[ $? -eq 0 ] || { echo "BOOTSTRAP FAIL: verify"; exit 17; }

echo "[revision-bootstrap] $(date -u) OK"
