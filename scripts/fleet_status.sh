#!/usr/bin/env bash
# Poll all 5 RunPod gate pods at once. Usage: bash scripts/fleet_status.sh
KEY=~/.ssh/id_ed25519_runpod_anomaly
SSHOPT="-i $KEY -o BatchMode=yes -o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new"
# pod  ip  port  ncells_expected
PODS=(
  "E 194.68.245.198 22046 18"
  "A 69.30.85.213  22174 18"
  "B 69.30.85.138  22063 18"
  "C 69.30.85.4    22076 18"
  "D 69.30.85.29   22003 18"
)
poll() {
  local name=$1 ip=$2 port=$3 exp=$4
  ssh $SSHOPT -p "$port" root@"$ip" '
    cd /workspace/anomaly-llm-study 2>/dev/null || exit 9
    done=$(ls -1 results/raw/exp1_repro/*.json 2>/dev/null | wc -l | tr -d " ")
    fails=$(grep -c "\[FAIL\]" results/logs/gate_*.log 2>/dev/null | awk -F: "{s+=\$2} END{print s+0}")
    proc=$(pgrep -f kaggle_gate >/dev/null && echo RUN || echo STOP)
    last=$(grep -hE "\[ok\]" results/logs/gate_*.log 2>/dev/null | tail -1 | sed "s/.*\] //; s/ (.*//")
    gpu=$(nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader 2>/dev/null | head -1)
    echo "done=$done fails=$fails proc=$proc gpu=[$gpu] last=[$last]"
  ' 2>/dev/null || echo "UNREACHABLE"
}
echo "=== FLEET STATUS $(date -u +%H:%M:%SZ) ==="
total=0
for row in "${PODS[@]}"; do
  read -r name ip port exp <<< "$row"
  out=$(poll "$name" "$ip" "$port" "$exp")
  n=$(echo "$out" | sed -n 's/.*done=\([0-9]*\).*/\1/p'); n=${n:-0}
  total=$((total + n))
  printf "Pod %s (%s/%s):  %s\n" "$name" "${n:-?}" "$exp" "$out"
done
echo "--- TOTAL cells complete: $total / 90 ---"
