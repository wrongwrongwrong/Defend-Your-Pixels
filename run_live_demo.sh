#!/bin/bash
# Run from anywhere — same as launch_live_demo.command (no Finder required).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
export DYP_NO_CAMERA="${DYP_NO_CAMERA:-1}"
exec "$REPO_ROOT/launch_live_demo.command"
