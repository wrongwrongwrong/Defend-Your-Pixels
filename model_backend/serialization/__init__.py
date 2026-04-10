"""Serialization helpers for the authoritative model.

The bridge/frontends should not read model internals directly. Instead, the live
runtime serializes `GameState` into a stable payload shape (snake_case) that is
transported over WebSocket.
"""

from .board_state import serialize_game_state

__all__ = ["serialize_game_state"]
