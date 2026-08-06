#!/usr/bin/env bash
# Pull revision results + logs from one RunPod pod to local (system of record).
#
# USAGE: bash scripts/revision_pull.sh HOST PORT [label]
#   e.g. bash scripts/revision_pull.sh 69.30.85.142 22071 revision
set -uo pipefail
HOST="${1:?need HOST}"
PORT="${2:?need PORT}"
LABEL="${3:-revision}"
KEY="${HOME}/.ssh/id_ed25519_runpod_anomaly"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SSH="ssh -i $KEY -o StrictHostKeyChecking=no -o ConnectTimeout=30 -p $PORT"
RSYNC="rsync -az --timeout=120 -e \"ssh -i $KEY -o StrictHostKeyChecking=no -o ConnectTimeout=30 -p $PORT\""

mkdir -p "$ROOT/results/raw/exp3_security" "$ROOT/results/raw/exp2_fewshot" \
         "$ROOT/results/logs/fleet/$LABEL"

pull() {
  local src="$1" dst="$2"
  for attempt in 1 2 3; do
    rsync -az --timeout=120 -e "ssh -i $KEY -o StrictHostKeyChecking=no -o ConnectTimeout=30 -p $PORT" \
      "$src" "$dst" && return 0
    sleep 5
  done
  echo "[revision-pull] FAIL $src" >&2
  return 1
}

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[$TS] pulling from root@$HOST:$PORT ($LABEL)"

pull "root@$HOST:/workspace/results/raw/exp3_security/" "$ROOT/results/raw/exp3_security/" || true
pull "root@$HOST:/workspace/results/raw/exp2_fewshot/" "$ROOT/results/raw/exp2_fewshot/" || true
pull "root@$HOST:/workspace/results/logs/revision/" "$ROOT/results/logs/fleet/$LABEL/" || true

N3=$(ls "$ROOT/results/raw/exp3_security/"*likelihood*unsw* 2>/dev/null | wc -l | tr -d ' ')
N2=$(ls "$ROOT/results/raw/exp2_fewshot/"*.json 2>/dev/null | wc -l | tr -d ' ')
echo "[revision-pull] local: exp3_security unsw-likelihood JSONs=$N3  exp2_fewshot JSONs=$N2"
echo "[revision-pull] logs -> $ROOT/results/logs/fleet/$LABEL/"
