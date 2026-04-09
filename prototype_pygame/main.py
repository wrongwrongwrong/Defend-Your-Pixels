#!/usr/bin/env python3
"""
Preferred (repo root on sys.path):

  python3 -m prototype_pygame.main

Running this file directly also works (see below).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Running `python prototype_pygame/main.py` puts only `prototype_pygame/` on sys.path,
# so `import prototype_pygame` fails. Put the repo root first.
if __package__ is None:
    _root = Path(__file__).resolve().parents[1]
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from prototype_pygame.control import main

if __name__ == "__main__":
    main()
