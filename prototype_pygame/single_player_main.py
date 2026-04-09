#!/usr/bin/env python3
"""
Run from repo root (after `pip install -e .`):

  python3 -m prototype_pygame.single_player_main
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ is None:
    _root = Path(__file__).resolve().parents[1]
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from prototype_pygame.control import main_solo_range_test


if __name__ == "__main__":
    main_solo_range_test()
