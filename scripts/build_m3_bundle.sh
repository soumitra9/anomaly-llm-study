#!/usr/bin/env bash
# Build the M3 golden data bundle for RunPod staging (deterministic, no fetch race).
# Packs creditcard.csv + unsw.parquet + pima ODDS cache. Output: /tmp/m3_data_golden.tgz
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-/tmp/m3_data_golden.tgz}"
cd "$ROOT"
for f in data/creditcard.csv data/unsw.parquet; do
  [ -f "$f" ] || { echo "missing $f — download creditcard (Kaggle) + UNSW first"; exit 1; }
done
[ -d data/pima ] || { echo "missing data/pima — run ODDS staging first"; exit 1; }
echo "[m3-bundle] packing creditcard + unsw + pima -> $OUT"
tar czf "$OUT" -C "$ROOT/data" creditcard.csv unsw.parquet pima
ls -lh "$OUT"
echo "[m3-bundle] verify loads..."
uv run python - <<'PY'
from anodet.data.creditcard import load_creditcard
from anodet.data.unsw import load_unsw
from anodet.data.odds import load_odds
cc = load_creditcard("data/creditcard.csv", split="temporal", seed=0)
assert abs(cc["true_base_rate"] - 0.00173) < 0.0001 and int(cc["y_test"].sum()) == 492
u = load_unsw("data/unsw.parquet", seed=0)
assert u["X_train"].shape[1] > 0 and u["n_neg_scored"] <= 40000
p = load_odds("pima", split_idx=0)
assert p["X_test"].shape[1] == 8
print("[m3-bundle] creditcard + unsw + pima load OK")
PY
