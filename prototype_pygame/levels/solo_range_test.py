"""Single-player range/attack verification map."""

from __future__ import annotations

from pathlib import Path

from model_backend.game import GameState

from .level_loader import load_level_from_path


def build_solo_range_test() -> GameState:
    return load_level_from_path(Path(__file__).with_name("solo_range_test.txt"))
