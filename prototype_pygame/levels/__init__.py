"""Prototype level builders.

Prototype-specific entry functions stay here, but shared scenario construction now
lives in `model_backend.scenarios` so the live runtime and pygame prototype load maps
through the same authoritative code path.
"""

from model_backend.scenarios import build_react_integration_level, load_level_from_path

from .pvp_level1 import build_pvp_level1
from .solo_range_test import build_solo_range_test
from .turn_cycle_test import build_turn_cycle_test

__all__ = [
    "build_pvp_level1",
    "build_react_integration_level",
    "build_solo_range_test",
    "build_turn_cycle_test",
    "load_level_from_path",
]
