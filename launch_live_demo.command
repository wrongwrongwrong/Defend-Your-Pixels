#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
UI_URL="http://localhost:8080"
VENV_PY="$REPO_ROOT/.venv/bin/python3"

pause_on_exit() {
  echo ""
  read -r -p "Press Enter to close..." _
}

# Finder-launched .command windows often close immediately on error; pause so users can read it.
trap 'echo ""; echo "[launch_live_demo] ERROR: launch failed."; pause_on_exit' ERR

if [ ! -x "$VENV_PY" ]; then
  echo ""
  echo "[launch_live_demo] Missing .venv. Bootstrapping environment..."
  echo ""

  if ! command -v python3 >/dev/null 2>&1; then
    echo "[launch_live_demo] ERROR: python3 not found on PATH."
    echo "Install Python 3.10+ and re-run."
    echo ""
    pause_on_exit
    exit 1
  fi

  echo "[launch_live_demo] Creating .venv ..."
  python3 -m venv "$REPO_ROOT/.venv"

  echo "[launch_live_demo] Installing dependencies (this may take a minute) ..."
  "$VENV_PY" -m pip install --upgrade pip
  "$VENV_PY" -m pip install -r "$REPO_ROOT/requirements.txt"
  "$VENV_PY" -m pip install -e "$REPO_ROOT"
fi

echo ""
echo "[launch_live_demo] Opening UI:"
echo "  $UI_URL"
echo ""

# Open the UI in the default browser (non-blocking).
open "$UI_URL" >/dev/null 2>&1 || true

echo "[launch_live_demo] Starting live tracker (close this Terminal window to stop)."
echo ""

cd "$REPO_ROOT"

ARGS=()
if [ "${DYP_NO_CAMERA:-}" = "1" ] || [ "${DYP_NO_CAMERA:-}" = "true" ]; then
  ARGS+=(--no-camera)
fi

echo "[launch_live_demo] Running:"
# Avoid "unbound variable" with `set -u` when ARGS is empty.
echo "  \"$VENV_PY\" -m runner.run_live_tracker ${ARGS[@]:-}"
echo ""

exec "$VENV_PY" -m runner.run_live_tracker "${ARGS[@]}"
