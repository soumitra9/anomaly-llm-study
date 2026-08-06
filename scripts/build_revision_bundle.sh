#!/usr/bin/env bash
# Build RunPod staging bundles for Revision Phase (RV1 + RV2).
#   /tmp/revision_data.tgz  — creditcard + unsw + 8 ODDS cache dirs (GATE_SPEC §RV2)
#   /tmp/revision_code.tgz  — uncommitted execution-path files (overlay on pod)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RV2_DS=(arrhythmia breastw cardio ionosphere shuttle speech vertebral yeast)
DATA_OUT="${1:-/tmp/revision_data.tgz}"
CODE_OUT="${2:-/tmp/revision_code.tgz}"

for f in data/creditcard.csv data/unsw.parquet; do
  [ -f "$f" ] || { echo "missing $f"; exit 1; }
done

echo "[revision-bundle] warming ${#RV2_DS[@]} ODDS caches (first load builds npz)..."
for d in "${RV2_DS[@]}"; do
  uv run python -c "from anodet.data.odds import load_odds; o=load_odds('$d', split_idx=0); print('  ok $d', o['X_train'].shape, o['X_test'].shape)"
done

TAR_ARGS=(creditcard.csv unsw.parquet)
for d in "${RV2_DS[@]}"; do
  [ -d "data/$d" ] || { echo "missing data/$d after warm"; exit 1; }
  TAR_ARGS+=("$d")
done

echo "[revision-bundle] packing data -> $DATA_OUT"
tar czf "$DATA_OUT" -C data "${TAR_ARGS[@]}"
ls -lh "$DATA_OUT"

echo "[revision-bundle] packing code overlay -> $CODE_OUT"
tar czf "$CODE_OUT" \
  scripts/exp3_fleet.py \
  scripts/revision_fewshot.py \
  scripts/revision_bootstrap.sh \
  scripts/revision_run.sh \
  anodet/eval/exp3_security.py \
  anodet/scoring/prompted.py \
  GATE_SPEC.md
ls -lh "$CODE_OUT"

echo "[revision-bundle] verify security + one ODDS load..."
uv run python - <<'PY'
from anodet.data.creditcard import load_creditcard
from anodet.data.unsw import prepare_unsw
import pandas as pd
from anodet.data.odds import load_odds
cc = load_creditcard("data/creditcard.csv", split="temporal", seed=0)
assert int(cc["y_test"].sum()) == 492
u = prepare_unsw(pd.read_parquet("data/unsw.parquet"), seed=0)
assert len(u["y_test"]) > 0
load_odds("breastw", split_idx=0)
print("[revision-bundle] verify OK")
PY
