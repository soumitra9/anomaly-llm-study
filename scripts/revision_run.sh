#!/usr/bin/env bash
# Revision Phase GPU run — phased, logged, resume-safe (GATE_SPEC §RV1 + §RV2).
#
# Run ON THE POD from /workspace/anomaly-llm-study after revision_bootstrap.sh.
# All stdout/stderr -> /workspace/results/logs/revision/revision_run.log
#
# Phases (env PHASE controls which to run):
#   measure  — RV1 UNSW likelihood seed 0 only (--max-cells 1)
#   unsw     — RV1 UNSW likelihood seeds 1,2 (skips complete)
#   fewshot  — RV2 all 8 datasets × 3 seeds
#   all      — measure then unsw then fewshot (default)
set -uo pipefail
REPO=/workspace/anomaly-llm-study
cd "$REPO"
mkdir -p /workspace/results/logs/revision
LOG=/workspace/results/logs/revision/revision_run.log
PHASE="${PHASE:-all}"

log() { echo "[revision-run] $(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a "$LOG"; }

run_measure() {
  log "PHASE measure: RV1 UNSW likelihood seed=0 r=5 max_steps=1000"
  uv run python -m scripts.exp3_fleet \
    --task-datasets unsw --modes likelihood --models qwen2.5-3b \
    --likelihood-tasks unsw --seeds 0 --r 5 --max-steps 1000 \
    --results-root /workspace/results --device cuda --max-cells 1 \
    2>&1 | tee -a "$LOG"
}

run_unsw_rest() {
  log "PHASE unsw: RV1 UNSW likelihood seeds 1,2"
  uv run python -m scripts.exp3_fleet \
    --task-datasets unsw --modes likelihood --models qwen2.5-3b \
    --likelihood-tasks unsw --seeds 1,2 --r 5 --max-steps 1000 \
    --results-root /workspace/results --device cuda \
    2>&1 | tee -a "$LOG"
}

run_fewshot() {
  log "PHASE fewshot: RV2 qwen prompted-fewshot k=3"
  uv run python -m scripts.revision_fewshot \
    --datasets all --seeds 0,1,2 --n-shots 3 \
    --results-root /workspace/results --device cuda \
    2>&1 | tee -a "$LOG"
}

log "start PHASE=$PHASE git=$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
case "$PHASE" in
  measure) run_measure ;;
  unsw)    run_unsw_rest ;;
  fewshot) run_fewshot ;;
  all)     run_measure; run_unsw_rest; run_fewshot ;;
  *)       echo "unknown PHASE=$PHASE"; exit 2 ;;
esac
log "done PHASE=$PHASE"
# cell counts for teardown gate
uv run python - <<'PY' | tee -a "$LOG"
from pathlib import Path
for exp, pat in [("exp3_security", "*likelihood*unsw*"), ("exp2_fewshot", "*.json")]:
    p = Path("/workspace/results/raw") / exp
    n = len(list(p.glob(pat))) if p.exists() else 0
    print(f"[revision-run] {exp} matching cells: {n}")
PY
