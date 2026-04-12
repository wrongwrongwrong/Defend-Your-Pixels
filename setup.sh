#!/bin/bash
# Run from Terminal (repo root), not by double-click in Finder:
#   cd path/to/Defend-Your-Pixels
#   chmod +x setup.sh   # once
#   ./setup.sh
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Creating .venv …"
  python3 -m venv .venv
fi

VENV_PY="./.venv/bin/python"

"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install -r requirements.txt
"$VENV_PY" -m pip install -e .

cat <<'EOF'
Environment is ready.
Use:
  source .venv/bin/activate
  python3 runner/run_live_tracker.py
EOF
