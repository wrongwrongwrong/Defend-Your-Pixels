"""
Legacy compatibility entrypoint.

Historically the repository exposed a `bridge/websocket_server.py` entrypoint.
The current canonical runtime is `runner/run_live_tracker.py`.

This file intentionally contains no game/tracker logic; it simply forwards to the
runner so older commands keep working.
"""

import sys

from runner.run_live_tracker import main


if __name__ == "__main__":
    # Keep behavior identical to calling the runner directly.
    sys.exit(main())
