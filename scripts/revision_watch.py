#!/usr/bin/env python3
"""Fail-safe local watcher for Revision Phase RunPod runs.

Polls the pod, pulls + verifies + backs up when new JSONs land, starts fewshot
after unsw completes, and exits cleanly when fewshot completes. Designed to never
crash on transient SSH/rsync errors — logs and retries on the next interval.

Usage:
  uv run python scripts/revision_watch.py
  uv run python scripts/revision_watch.py --host 69.30.85.67 --port 22132 --interval 300

Logs/state:
  results/logs/fleet/revision/watch.log
  results/logs/fleet/revision/watch_state.json
  results/logs/fleet/revision/watch.lock  (single-instance flock)
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "results" / "logs" / "fleet" / "revision"
STATE_PATH = LOG_DIR / "watch_state.json"
LOCK_PATH = LOG_DIR / "watch.lock"
LOG_PATH = LOG_DIR / "watch.log"
KEY = Path.home() / ".ssh" / "id_ed25519_runpod_anomaly"
PULL = ROOT / "scripts" / "revision_pull.sh"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    line = f"[revision-watch] {_ts()} {msg}"
    print(line, flush=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            log("WARN corrupt state file; resetting")
    local_unsw = len(list((ROOT / "results/raw/exp3_security").glob("*likelihood*unsw*.json")))
    local_few = len(list((ROOT / "results/raw/exp2_fewshot").glob("*.json")))
    return {
        "last_unsw_pod": local_unsw,
        "last_fewshot_pod": local_few,
        "fewshot_launch_attempted": False,
    }


def save_state(state: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    state = {**state, "heartbeat_utc": _ts(), "watcher_pid": os.getpid()}
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    tmp.replace(STATE_PATH)


def pod_status(host: str, port: int) -> dict | None:
    """One SSH round-trip for counts + log markers (fewer connections, less kill risk)."""
    remote = r"""python3 - <<'PY'
import json
from pathlib import Path
log = Path("/workspace/results/logs/revision/revision_run.log")
text = log.read_text(errors="replace") if log.exists() else ""
tail = text[-80000:]
def has(needle):
    return needle in tail
print(json.dumps({
    "unsw_jsons": len(list(Path("/workspace/results/raw/exp3_security").glob("*likelihood*unsw*.json"))),
    "fewshot_jsons": len(list(Path("/workspace/results/raw/exp2_fewshot").glob("*.json"))),
    "unsw_done": has("done PHASE=unsw"),
    "fewshot_started": has("start PHASE=fewshot"),
    "fewshot_done": has("done PHASE=fewshot"),
}))
PY"""
    ok, out = ssh(host, port, remote, timeout=45)
    if not ok or not out.strip():
        return None
    try:
        return json.loads(out.strip().splitlines()[-1])
    except json.JSONDecodeError:
        log(f"WARN bad pod_status json: {out[:200]!r}")
        return None


def ssh(host: str, port: int, remote_cmd: str, *, timeout: int = 30) -> tuple[bool, str]:
    cmd = [
        "ssh",
        "-i", str(KEY),
        "-p", str(port),
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=15",
        "-o", "BatchMode=yes",
        f"root@{host}",
        remote_cmd,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (r.stdout or "").strip()
        if r.returncode != 0:
            err = (r.stderr or "").strip()
            log(f"WARN ssh rc={r.returncode} cmd={remote_cmd!r} err={err[:200]}")
            return False, out
        return True, out
    except subprocess.TimeoutExpired:
        log(f"WARN ssh timeout cmd={remote_cmd!r}")
        return False, ""
    except OSError as e:
        log(f"WARN ssh error cmd={remote_cmd!r}: {e}")
        return False, ""


def ssh_int(host: str, port: int, remote_cmd: str) -> int | None:
    ok, out = ssh(host, port, remote_cmd)
    if not ok:
        return None
    digits = "".join(ch for ch in out if ch.isdigit())
    if not digits:
        return 0
    try:
        return int(digits)
    except ValueError:
        log(f"WARN could not parse int from {out!r}")
        return None


def log_contains(host: str, port: int, needle: str) -> bool:
    """Legacy helper; prefer pod_status()."""
    ok, out = ssh(
        host,
        port,
        f"tail -c 80000 /workspace/results/logs/revision/revision_run.log 2>/dev/null | grep -F '{needle}' | tail -1",
        timeout=45,
    )
    return ok and bool(out.strip())


def pull(host: str, port: int) -> bool:
    if not PULL.exists():
        log(f"ERROR missing {PULL}")
        return False
    try:
        r = subprocess.run(
            ["bash", str(PULL), host, str(port), "revision"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=600,
        )
        for line in (r.stdout or "").splitlines():
            if line.strip():
                log(line.strip())
        if r.returncode != 0:
            err = (r.stderr or "").strip()
            log(f"WARN pull exit {r.returncode}: {err[:300]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        log("WARN pull timed out after 600s")
        return False
    except OSError as e:
        log(f"WARN pull error: {e}")
        return False


def launch_fewshot(host: str, port: int) -> None:
    cmd = (
        "cd /workspace/anomaly-llm-study && "
        "nohup env PHASE=fewshot bash scripts/revision_run.sh "
        ">> /workspace/results/logs/revision/nohup_fewshot.log 2>&1 &"
    )
    ok, _ = ssh(host, port, cmd)
    if ok:
        log("fewshot launch sent to pod")
    else:
        log("WARN fewshot launch failed; will retry next cycle if unsw still done")


def acquire_lock() -> int | None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_PATH.exists():
        try:
            old = int(LOCK_PATH.read_text(encoding="utf-8").strip())
            os.kill(old, 0)
            log(f"lock held by live pid {old}; exiting")
            return None
        except (ProcessLookupError, ValueError):
            log("removing stale watch.lock (dead pid)")
            LOCK_PATH.unlink(missing_ok=True)
        except OSError:
            pass
    fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        log("another watcher holds flock; exiting")
        return None
    os.ftruncate(fd, 0)
    os.write(fd, str(os.getpid()).encode())
    return fd


def cycle(host: str, port: int, state: dict) -> str:
    """One poll cycle. Returns 'continue' or 'done'."""
    ps = pod_status(host, port)
    if ps is None:
        log("skip cycle: pod unreachable")
        save_state(state)
        return "continue"

    unsw_pod = int(ps.get("unsw_jsons") or 0)
    few_pod = int(ps.get("fewshot_jsons") or 0)
    log(
        f"pod counts unsw={unsw_pod} fewshot={few_pod} "
        f"(local tracked unsw={state['last_unsw_pod']} fewshot={state['last_fewshot_pod']})"
    )

    if unsw_pod > state["last_unsw_pod"]:
        log(f"new unsw JSON(s): {state['last_unsw_pod']} -> {unsw_pod}; pulling")
        pull(host, port)
        state["last_unsw_pod"] = unsw_pod

    unsw_done = bool(ps.get("unsw_done"))
    fewshot_started = bool(ps.get("fewshot_started"))
    fewshot_done = bool(ps.get("fewshot_done"))

    if unsw_done and not fewshot_started and not state.get("fewshot_launch_attempted"):
        log("unsw complete on pod; final pull then launch fewshot")
        pull(host, port)
        state["last_unsw_pod"] = max(state["last_unsw_pod"], unsw_pod)
        launch_fewshot(host, port)
        state["fewshot_launch_attempted"] = True

    if fewshot_started and few_pod > state["last_fewshot_pod"]:
        log(f"new fewshot JSON(s): {state['last_fewshot_pod']} -> {few_pod}; pulling")
        pull(host, port)
        state["last_fewshot_pod"] = few_pod

    save_state(state)

    if fewshot_done:
        log("fewshot complete on pod; final pull")
        pull(host, port)
        state["last_fewshot_pod"] = max(state["last_fewshot_pod"], few_pod)
        save_state(state)
        return "done"

    return "continue"


def main() -> int:
    p = argparse.ArgumentParser(description="Fail-safe revision RunPod watcher")
    p.add_argument("--host", default=os.environ.get("REVISION_POD_IP", "69.30.85.67"))
    p.add_argument("--port", type=int, default=int(os.environ.get("REVISION_POD_PORT", "22132")))
    p.add_argument("--interval", type=int, default=300, help="seconds between polls")
    p.add_argument("--once", action="store_true", help="run one poll cycle then exit (for cron)")
    args = p.parse_args()

    if not KEY.exists():
        log(f"ERROR missing SSH key {KEY}")
        return 1

    lock_fd = acquire_lock()
    if lock_fd is None:
        log("another watcher already running (lock held); exiting")
        return 0

    state = load_state()
    log(f"start host={args.host} port={args.port} interval={args.interval}s state={state}")

    try:
        while True:
            try:
                outcome = cycle(args.host, args.port, state)
                state = load_state()
                if outcome == "done":
                    log("all phases complete; watcher exiting OK")
                    return 0
            except Exception as e:  # noqa: BLE001 — outer guard; never crash the daemon
                log(f"ERROR unexpected cycle exception: {e!r}")
            if args.once:
                return 0
            time.sleep(max(30, args.interval))
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


if __name__ == "__main__":
    sys.exit(main())
