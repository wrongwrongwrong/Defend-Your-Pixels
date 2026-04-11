"""
Bridge-level entrypoint (CLI) for the live tracker runtime.

Why this file exists:
- Keep backwards-compatible command paths for scripts/docs that expect `bridge/...`
- Delegate the real runtime to `runner/run_live_tracker.py`

In other words, this file is an alias entrypoint, not the main application logic.
"""

import sys

from runner.run_live_tracker import main


if __name__ == "__main__":
    # Exit code is forwarded from the runner's main.
    sys.exit(main())
