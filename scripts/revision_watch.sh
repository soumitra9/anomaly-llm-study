#!/usr/bin/env bash
# Thin launcher for the fail-safe Python watcher (prefer this over hand-rolled bash loops).
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
exec uv run python scripts/revision_watch.py "$@"
