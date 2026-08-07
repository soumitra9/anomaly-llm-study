#!/usr/bin/env bash
# Install a macOS LaunchAgent so revision_watch survives IDE terminal teardown.
#
# Run once from Terminal.app (not from Cursor agent):
#   bash scripts/revision_watch_install_launchagent.sh
#   bash scripts/revision_watch_install_launchagent.sh uninstall
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.anodet.revision-watch"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
LOG_DIR="$ROOT/results/logs/fleet/revision"
HOST="${REVISION_POD_IP:-69.30.85.67}"
PORT="${REVISION_POD_PORT:-22132}"
INTERVAL="${REVISION_WATCH_INTERVAL:-300}"
UV="$(command -v uv || true)"

if [[ "${1:-}" == "uninstall" ]]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  echo "uninstalled $LABEL"
  exit 0
fi

if [[ -z "$UV" ]]; then
  echo "ERROR: uv not on PATH"; exit 1
fi

mkdir -p "$LOG_DIR"
LA_DIR="$HOME/Library/LaunchAgents"
if [[ ! -d "$LA_DIR" ]]; then
  mkdir -p "$LA_DIR" || {
    echo "ERROR: cannot create $LA_DIR"; exit 1
  }
fi
if [[ ! -w "$LA_DIR" ]]; then
  owner="$(stat -f '%Su' "$LA_DIR" 2>/dev/null || echo unknown)"
  echo "ERROR: $LA_DIR is not writable (owner: $owner, you: $(whoami))."
  echo "Fix once in Terminal.app, then re-run this script:"
  echo "  sudo chown \"$(whoami):staff\" \"$LA_DIR\""
  echo "  chmod u+rwx \"$LA_DIR\""
  echo ""
  echo "Fallback (no LaunchAgent): bash scripts/revision_watch_daemon.sh"
  exit 1
fi
bash "$ROOT/scripts/revision_watch_daemon.sh" stop 2>/dev/null || true

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>WorkingDirectory</key>
  <string>${ROOT}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>REVISION_POD_IP</key>
    <string>${HOST}</string>
    <key>REVISION_POD_PORT</key>
    <string>${PORT}</string>
    <key>REVISION_WATCH_INTERVAL</key>
    <string>${INTERVAL}</string>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>ProgramArguments</key>
  <array>
    <string>${UV}</string>
    <string>run</string>
    <string>python</string>
    <string>${ROOT}/scripts/revision_watch.py</string>
    <string>--host</string>
    <string>${HOST}</string>
    <string>--port</string>
    <string>${PORT}</string>
    <string>--interval</string>
    <string>${INTERVAL}</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/watch.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/watch.log</string>
  <key>ThrottleInterval</key>
  <integer>30</integer>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl enable "gui/$(id -u)/$LABEL"
launchctl kickstart -k "gui/$(id -u)/$LABEL"

echo "installed $LABEL"
echo "  plist: $PLIST"
echo "  log:   $LOG_DIR/watch.log"
echo "  stop:  bash scripts/revision_watch_install_launchagent.sh uninstall"
