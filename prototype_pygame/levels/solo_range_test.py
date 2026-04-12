"""Build the single-player range/attack verification level."""

from __future__ import annotations

from pathlib import Path

from model_backend.game import GameState
from model_backend.scenarios import load_level_from_path


def build_solo_range_test() -> GameState:
    return load_level_from_path(Path(__file__).with_name("solo_range_test.txt"))
