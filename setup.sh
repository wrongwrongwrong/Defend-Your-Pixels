#!/bin/bash
set -euo pipefail


VENV_PY="./.venv/bin/python"

if ! "$VENV_PY" -c "import cv2, numpy, django" >/dev/null 2>&1; then
  "$VENV_PY" -m pip install --upgrade pip
  "$VENV_PY" -m pip install -r requirements.txt
else
  echo "Dependencies already installed in .venv."
fi

cat <<'EOF'
Environment is ready.
Use:
  source .venv/bin/activate
  python pixel_defense_tracker/main.py
EOF