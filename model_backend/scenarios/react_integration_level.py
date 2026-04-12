"""Live tracker scenario with P1 at bottom and P2 at top."""

from __future__ import annotations

from pathlib import Path

from model_backend.game import GameState

from .level_loader import load_level_from_path


def build_react_integration_level() -> GameState:
    game = load_level_from_path(Path(__file__).with_name("react_integration_level.txt"))
    # The live tracker scenario is meant to verify marker-driven movement, so keep
    # the board open instead of filling lanes with default pixels.
    game.pixels.clear()
    game.pixels_destroyed_by = {pid: 0 for pid in game.players}
    game.last_action = f"Player {int(game.active_player)} turn started"
    return game
