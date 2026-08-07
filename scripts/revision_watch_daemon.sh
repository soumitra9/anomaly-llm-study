#!/usr/bin/env bash
# Supervisor for revision_watch.py — survives IDE terminal teardown.
#
# USAGE:
#   bash scripts/revision_watch_daemon.sh
#   bash scripts/revision_watch_daemon.sh stop
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/results/logs/fleet/revision"
DAEMON_LOG="$LOG_DIR/watch_daemon.log"
DAEMON_LOCK="$LOG_DIR/watch_daemon.lock"
LOOP="$ROOT/scripts/revision_watch_supervisor_loop.sh"

mkdir -p "$LOG_DIR"

daemon_log() {
  echo "[revision-watch-daemon] $(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> "$DAEMON_LOG"
}

pid_alive() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

stop_daemon() {
  if [[ -f "$DAEMON_LOCK" ]]; then
    local pid
    pid="$(tr -dc '0-9' < "$DAEMON_LOCK" 2>/dev/null || true)"
    if pid_alive "$pid"; then
      daemon_log "stopping supervisor pid=$pid"
      kill "$pid" 2>/dev/null || true
      sleep 2
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$DAEMON_LOCK"
  fi
  pkill -f "revision_watch_supervisor_loop.sh" 2>/dev/null || true
  pkill -f "scripts/revision_watch.py" 2>/dev/null || true
  rm -f "$LOG_DIR/watch.lock"
  daemon_log "stopped"
}

if [[ "${1:-}" == "stop" ]]; then
  stop_daemon
  exit 0
fi

if [[ -f "$DAEMON_LOCK" ]]; then
  old="$(tr -dc '0-9' < "$DAEMON_LOCK" 2>/dev/null || true)"
  if pid_alive "$old"; then
    daemon_log "already running supervisor pid=$old"
    exit 0
  fi
  daemon_log "removing stale daemon lock pid=$old"
  rm -f "$DAEMON_LOCK"
fi

chmod +x "$LOOP"
if command -v setsid >/dev/null 2>&1; then
  setsid "$LOOP" >> "$DAEMON_LOG" 2>&1 &
else
  nohup "$LOOP" >> "$DAEMON_LOG" 2>&1 &
fi
sup_pid=$!
echo "$sup_pid" > "$DAEMON_LOCK"
disown "$sup_pid" 2>/dev/null || true
daemon_log "launched detached supervisor pid=$sup_pid"
