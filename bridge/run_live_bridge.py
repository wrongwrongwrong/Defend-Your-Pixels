"""Bridge-level entrypoint for the live tracker runtime."""

import sys

from runner.run_live_tracker import main


if __name__ == "__main__":
    sys.exit(main())
