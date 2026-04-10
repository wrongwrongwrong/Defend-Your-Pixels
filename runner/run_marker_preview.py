"""Runner entrypoint for ArUco marker detection preview.

Delegates to `python_tracker.marker_detection.marker_preview` so the preview can be
invoked via a stable `runner/` command path.
"""

import sys

from python_tracker.marker_detection.marker_preview import main


if __name__ == "__main__":
    sys.exit(main() or 0)
