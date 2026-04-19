#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────
# Defend Your Pixels — macOS / Linux launcher
#
# Starts BOTH the React dev server and the Python live
# tracker in a single terminal using "concurrently".
#
# Prerequisites:
#   1.  cd <project-root>/react_frontend && npm install
#   2.  pip install -e .   (from project root)
#
# Usage:
#   cd <project-root>
#   bash scripts/run-mac.sh
# ──────────────────────────────────────────────────────────

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "============================================="
echo "  Defend Your Pixels — macOS / Linux"
echo "  Project root: $PROJECT_ROOT"
echo "============================================="
echo ""

# Check that npm dependencies are installed
if [ ! -d "$PROJECT_ROOT/react_frontend/node_modules" ]; then
    echo "[setup] Installing React frontend dependencies..."
    (cd "$PROJECT_ROOT/react_frontend" && npm install)
fi

# Check that concurrently is available
if ! npx --yes concurrently --version > /dev/null 2>&1; then
    echo "[setup] Installing concurrently..."
    (cd "$PROJECT_ROOT/react_frontend" && npm install concurrently --save-dev)
fi

echo "[start] Launching React dev server + Python live tracker..."
echo "        React UI  → http://localhost:5173"
echo "        Tracker   → ws://localhost:8765"
echo ""

cd "$PROJECT_ROOT/react_frontend"
npx concurrently -k \
    -n react,tracker \
    -c cyan,magenta \
    "npx vite" \
    "cd '$PROJECT_ROOT' && python3 -m runner.run_live_tracker"
