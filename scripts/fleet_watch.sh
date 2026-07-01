#!/usr/bin/env bash
# M2 fleet event watcher — emits only on meaningful events (zsh/bash-safe, file-based state).
# Events: SHARD_DONE <pod>, FAILS <pod>, UNREACHABLE <pod>, STALL? <pod> (no new cell 45min), ALL_DONE, CHECKIN.
# Reads /tmp/fleet_pods.txt (HOST PORT LABEL). State in /tmp/fw_*. Exits at 360 local cells or after ~2h (re-arm).
#   bash scripts/fleet_watch.sh [interval_secs]   (default 300)
set -u
KEY="$HOME/.ssh/id_ed25519_runpod_anomaly"
PODS=/tmp/fleet_pods.txt
DEST="$(cd "$(dirname "$0")/.." && pwd)/results/raw/exp2_odds"
INT="${1:-300}"
SSHOPT="-i $KEY -o StrictHostKeyChecking=no -o ConnectTimeout=15"

for cyc in $(seq 1 220); do  # ~18h — covers the full fleet run (no re-arm needed)
  while read -r H P L; do
    [ -z "$H" ] && continue
    out=$(ssh $SSHOPT -p "$P" root@"$H" '
      d=$([ -f /workspace/results/shard.done ] && echo DONE || echo -)
      c=$(ls /workspace/results/raw/exp2_odds/*.json 2>/dev/null | wc -l | tr -d " ")
      f=$(cat /workspace/results/logs/*.log 2>/dev/null | grep -cE "\[FAIL\]|Traceback|OutOfMemory")
      echo "$d $c $f"' 2>/dev/null)
    if [ -z "$out" ]; then echo "[watch] $(date -u +%H:%M) UNREACHABLE $L"; continue; fi
    d=$(echo "$out" | awk '{print $1}'); c=$(echo "$out" | awk '{print $2}'); f=$(echo "$out" | awk '{print $3}')
    # shard done (once)
    if [ "$d" = "DONE" ] && [ ! -f /tmp/fw_done_$L ]; then echo "[watch] $(date -u +%H:%M) SHARD_DONE $L (cells=$c)"; touch /tmp/fw_done_$L; fi
    # failures (once)
    if [ "${f:-0}" != "0" ] && [ ! -f /tmp/fw_fail_$L ]; then echo "[watch] $(date -u +%H:%M) FAILS=$f $L"; touch /tmp/fw_fail_$L; fi
    # stall: cell count unchanged across 9 cycles (~45min) and not done
    prev=$(cat /tmp/fw_cells_$L 2>/dev/null || echo -1); pc=$(cat /tmp/fw_stallc_$L 2>/dev/null || echo 0)
    if [ "$c" = "$prev" ] && [ "$d" != "DONE" ]; then
      pc=$((pc+1)); echo "$pc" > /tmp/fw_stallc_$L
      if [ "$pc" -ge 14 ] && [ ! -f /tmp/fw_stall_$L ]; then echo "[watch] $(date -u +%H:%M) STALL? $L cells=$c unchanged ~70min (verify log-growth before acting — wide cells are legitimately slow)"; touch /tmp/fw_stall_$L; fi
    else
      echo 0 > /tmp/fw_stallc_$L; rm -f /tmp/fw_stall_$L
    fi
    echo "$c" > /tmp/fw_cells_$L
  done < "$PODS"
  N=$(ls "$DEST"/*.json 2>/dev/null | wc -l | tr -d ' ')
  if [ "$N" -ge 360 ]; then echo "[watch] $(date -u +%H:%M) ALL_DONE cells=$N/360"; exit 0; fi
  sleep "$INT"
done
N=$(ls "$DEST"/*.json 2>/dev/null | wc -l | tr -d ' ')
echo "[watch] $(date -u +%H:%M) CHECKIN cells=$N/360 (re-arm me)"
