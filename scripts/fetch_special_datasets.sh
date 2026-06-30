#!/usr/bin/env bash
# Stage the 3 ODDS datasets the AnoLLM fork does NOT get from adbench (it requires manual files).
# Sources are exactly those documented in third_party/AnoLLM/src/data_utils.py. Run from repo root on
# any pod/host that will load these datasets. Idempotent. Verifies each file parses.
#
#   bash scripts/fetch_special_datasets.sh
#
# Verified 2026-06-30: seismic 2584 rows/19 fields; mulcross 262144 rows/5 fields; arrhythmia X=452x274,
# 66 outliers (the ODDS version; NOT the DAMI 450x259/45.8% one).
#
# NOTE on arrhythmia source: the AnoLLM fork comment points to odds.cs.stonybrook.edu, but that host's
# TLS is broken (HANDSHAKE_FAILURE, 2026-06-30). The ODDS maintainer (Shebuti Rayana) mirrors the files at
# shebuti.com; arrhythmia.mat is a Dropbox link off that page. We pin that working URL below.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/seismic data/mulcross data/arrhythmia

echo "[1/3] seismic-bumps.arff (UCI)"
wget -q "https://archive.ics.uci.edu/ml/machine-learning-databases/00266/seismic-bumps.arff" \
  -O data/seismic/seismic-bumps.arff

echo "[2/3] mulcross.arff (OpenML data_id=40897)"
uv run python - <<'PY'
import urllib.request, json
meta = json.load(urllib.request.urlopen("https://www.openml.org/api/v1/json/data/40897", timeout=60))
urllib.request.urlretrieve(meta["data_set_description"]["url"], "data/mulcross/mulcross.arff")
PY

echo "[3/3] arrhythmia.mat (ODDS via shebuti.com mirror; adbench does NOT ship it)"
# Fork loads data/arrhythmia/arrhythmia.mat via scipy.io.loadmat, keys 'X','y'.
# Dropbox mirror from http://shebuti.com/arrhythmia-dataset/ (dl=1 forces raw download).
wget -q "https://www.dropbox.com/s/lmlwuspn1sey48r/arrhythmia.mat?dl=1" -O data/arrhythmia/arrhythmia.mat

echo "verify:"
uv run python - <<'PY'
from scipy.io import arff
for f in ["data/seismic/seismic-bumps.arff", "data/mulcross/mulcross.arff"]:
    d, m = arff.loadarff(f); print(f"  {f}: {len(d)} rows, {len(d.dtype.names)} fields")
import scipy.io, numpy as np, sys
d = scipy.io.loadmat("data/arrhythmia/arrhythmia.mat")
X, y = d["X"], np.asarray(d["y"]).ravel()
print(f"  arrhythmia.mat: X{X.shape} outliers={int(y.sum())} rate={y.mean():.4f}")
# guard against the wrong (DAMI 450x259/45.8%) arrhythmia
assert X.shape == (452, 274) and int(y.sum()) == 66, "NOT the ODDS arrhythmia (452x274/66) — refusing"
print("  ODDS arrhythmia verified.")
PY
