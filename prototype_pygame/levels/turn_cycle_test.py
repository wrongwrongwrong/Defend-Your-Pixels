"""Minimal test level for alternating-turn verification."""

from __future__ import annotations

from pathlib import Path

from model_backend.game import GameState

from .level_loader import load_level_from_path


def build_turn_cycle_test() -> GameState:
    game = load_level_from_path(Path(__file__).with_name("turn_cycle_test.txt"))
    game.pixels.clear()
    game.pixels_destroyed_by = {pid: 0 for pid in game.players}
    game.last_action = f"Player {int(game.active_player)} turn started"
    return game
