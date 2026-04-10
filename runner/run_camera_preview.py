"""Runner entrypoint for a simple camera preview.

This script exists so docs/scripts can consistently run previews via `runner/`,
while the actual implementation lives in `python_tracker.debug.camera_preview`.
"""

import sys

from python_tracker.debug.camera_preview import main

if __name__ == "__main__":
    sys.exit(main())
