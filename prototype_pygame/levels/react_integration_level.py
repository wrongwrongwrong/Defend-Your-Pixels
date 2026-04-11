"""React/live integration level with P1 at bottom and P2 at top."""

# Live tracker now uses model_backend.scenarios.react_integration_level.

from __future__ import annotations

from pathlib import Path

from model_backend.game import GameState

from .level_loader import load_level_from_path


def build_react_integration_level() -> GameState:
    return load_level_from_path(Path(__file__).with_name("react_integration_level.txt"))
