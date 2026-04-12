"""Build the default pygame PVP level from the colocated ASCII map."""

from __future__ import annotations

from pathlib import Path

from model_backend.game import GameState
from model_backend.scenarios import load_level_from_path


def build_pvp_level1() -> GameState:
    return load_level_from_path(Path(__file__).with_name("level1.txt"))
