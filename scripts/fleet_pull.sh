#!/usr/bin/env bash
# M2 fleet checkpoint puller — the durable-record recovery guardrail.
#
# Every INTERVAL seconds, rsync each pod's per-cell result JSONs (and logs) DOWN to local. Local
# results/raw/exp2_odds/ is the system of record: if any/all pods die (crash, balance-loss), every
# completed cell is already here, so recovery = re-provision + rsync local UP + resume (is_complete skips).
#
# Cell keys (filenames) are DISJOINT across pods (dataset sharding), so pooling into one local dir never
# collides. rsync is additive; a re-provisioned pod re-uploading identical JSONs is a harmless no-op.
#
# Reads pods from /tmp/fleet_pods.txt — one "HOST PORT LABEL" per line. Safe to edit live (re-read each cycle).
#
# USAGE:  bash scripts/fleet_pull.sh [interval_secs]   (default 600 = 10 min)
set -uo pipefail

KEY="$HOME/.ssh/id_ed25519_runpod_anomaly"
PODS_FILE=/tmp/fleet_pods.txt
LOCAL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$LOCAL_ROOT/results/raw/exp2_odds"
LOGDEST="$LOCAL_ROOT/results/logs/fleet"
INTERVAL="${1:-600}"
mkdir -p "$DEST" "$LOGDEST"

SSHOPT="-i $KEY -o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ServerAliveInterval=10"

# rsync a path with up to 3 retries (transient SSH under GPU load is common); returns 0 on any success.
pull_retry() {
  local src="$1" dst="$2" port="$3"
  for attempt in 1 2 3; do
    if rsync -az --timeout=60 -e "ssh $SSHOPT -p $port" "$src" "$dst" 2>/dev/null; then return 0; fi
    sleep 5
  done
  return 1
}

while true; do
  if [ ! -f "$PODS_FILE" ]; then echo "[pull] no $PODS_FILE yet"; sleep "$INTERVAL"; continue; fi
  fails=""
  while read -r HOST PORT LABEL; do
    [ -z "${HOST:-}" ] && continue
    mkdir -p "$LOGDEST/$LABEL"
    pull_retry "root@$HOST:/workspace/results/raw/exp2_odds/" "$DEST/" "$PORT" \
      || fails="$fails $LABEL"
    pull_retry "root@$HOST:/workspace/results/logs/" "$LOGDEST/$LABEL/" "$PORT" || true
  done < "$PODS_FILE"
  N=$(ls "$DEST"/*.json 2>/dev/null | wc -l | tr -d ' ')
  if [ -n "$fails" ]; then
    echo "[pull] $(date -u +%H:%M:%S) local cells = $N / 360  (UNREACHABLE after 3 retries:$fails)"
  else
    echo "[pull] $(date -u +%H:%M:%S) local cells = $N / 360  (all pods pulled OK)"
  fi
  sleep "$INTERVAL"
done
