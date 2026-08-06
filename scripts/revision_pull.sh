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

# Verify every pulled JSON is complete (fail-safe; corrupt/partial -> non-zero exit).
cd "$ROOT" || exit 2
VERIFY_FAIL=0
uv run python - <<'PY' || VERIFY_FAIL=1
from pathlib import Path
from anodet.utils.run_metadata import is_complete

root = Path("results/raw")
checks = []
for pat in ["exp3_security/*likelihood*unsw*.json", "exp2_fewshot/*.json"]:
    for p in sorted(root.glob(pat)):
        ok = is_complete(p)
        checks.append((p, ok))
        tag = "OK" if ok else "FAIL"
        print(f"[revision-pull] verify {tag} {p.name}")
if not checks:
    print("[revision-pull] verify: no JSONs yet (ok if mid-run)")
elif not all(ok for _, ok in checks):
    raise SystemExit(1)
PY

# Write-once timestamped backup alongside pull (results/backups/*.tgz never overwritten).
BACKUP_TAG=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="$ROOT/results/backups/revision_${BACKUP_TAG}.tgz"
mkdir -p "$ROOT/results/backups"
TAR_ARGS=()
shopt -s nullglob
for f in "$ROOT/results/raw/exp3_security/"*likelihood*unsw*.json; do TAR_ARGS+=("${f#$ROOT/}"); done
for f in "$ROOT/results/raw/exp2_fewshot/"*.json; do TAR_ARGS+=("${f#$ROOT/}"); done
for f in "$ROOT/results/logs/fleet/$LABEL/"*; do TAR_ARGS+=("${f#$ROOT/}"); done
shopt -u nullglob
if [ "${#TAR_ARGS[@]}" -gt 0 ]; then
  tar czf "$BACKUP" -C "$ROOT" "${TAR_ARGS[@]}"
  echo "[revision-pull] backup -> $BACKUP"
else
  echo "[revision-pull] backup skipped (no files)"
fi

[ "$VERIFY_FAIL" -eq 0 ] || { echo "[revision-pull] VERIFY FAILED"; exit 3; }
echo "[revision-pull] OK"
