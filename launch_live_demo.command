#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
UI_URL="http://localhost:8080"
VENV_PY="$REPO_ROOT/.venv/bin/python3"

if [ ! -x "$VENV_PY" ]; then
  echo ""
  echo "[launch_live_demo] Missing .venv. Run from repo root:"
  echo "  chmod +x setup.sh && ./setup.sh"
  echo ""
  read -r -p "Press Enter to close..."
  exit 1
fi

TRACKER_CMD="cd \"${REPO_ROOT}\"; \"${VENV_PY}\" -m runner.run_live_tracker"

# Start tracker in a new Terminal window (keeps it open).
osascript >/dev/null <<EOF
tell application "Terminal"
  activate
  do script "${TRACKER_CMD}"
end tell
EOF

# Open the UI in the default browser.
open "$UI_URL"

echo ""
echo "[launch_live_demo] Started tracker in Terminal and opened UI:"
echo "  $UI_URL"
echo ""
