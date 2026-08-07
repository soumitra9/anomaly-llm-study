#!/usr/bin/env bash
# Launch the detached supervisor (do not run revision_watch.py directly from IDE shells).
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec bash "$ROOT/scripts/revision_watch_daemon.sh" "$@"
