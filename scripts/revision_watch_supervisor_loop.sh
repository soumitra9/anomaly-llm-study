#!/usr/bin/env bash
# Inner loop — launched detached by revision_watch_daemon.sh (do not run directly).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/results/logs/fleet/revision"
DAEMON_LOG="$LOG_DIR/watch_daemon.log"
DAEMON_LOCK="$LOG_DIR/watch_daemon.lock"
WATCH_LOG="$LOG_DIR/watch.log"
HOST="${REVISION_POD_IP:-69.30.85.67}"
PORT="${REVISION_POD_PORT:-22132}"
INTERVAL="${REVISION_WATCH_INTERVAL:-300}"

log() { echo "[revision-watch-daemon] $(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> "$DAEMON_LOG"; }

log "supervisor start host=$HOST port=$PORT interval=${INTERVAL}s"
while true; do
  if grep -q "all phases complete" "$WATCH_LOG" 2>/dev/null; then
    log "watcher complete; supervisor exiting"
    break
  fi
  rm -f "$LOG_DIR/watch.lock"
  cd "$ROOT" || exit 1
  uv run python scripts/revision_watch.py --host "$HOST" --port "$PORT" --interval "$INTERVAL" >> "$WATCH_LOG" 2>&1
  rc=$?
  if grep -q "all phases complete" "$WATCH_LOG" 2>/dev/null; then
    log "watcher exit rc=$rc after complete"
    break
  fi
  log "watcher exited rc=$rc; restart in 15s"
  sleep 15
done
rm -f "$DAEMON_LOCK"
