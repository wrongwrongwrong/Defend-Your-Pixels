"""PVP level = ASCII file next to this module (level1.txt)."""

from __future__ import annotations

from pathlib import Path

from model_backend.game import GameState

from .level_loader import load_level_from_path


def build_pvp_level1() -> GameState:
    return load_level_from_path(Path(__file__).with_name("level1.txt"))
