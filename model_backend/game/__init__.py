"""Public exports for the authoritative rules engine.

This package hosts:
- core state machine (`GameState`)
- board and entity primitives
- small shared types (grid positions, player IDs, terrain types)

Other layers should import from here rather than reaching into implementation modules
directly, unless they need a private/internal API.
"""

from .state import GameState
from .entities import (
    Attacker,
    Defender,
    CommandTower,
    EtherDrill,
    Obstacle,
    Pixel,
)
from .types import (
    PlayerId,
    Pos,
    TerrainType,
    Direction,
    manhattan_distance,
    chebyshev_distance,
    ATK_DIRS,
    TOKEN_MOVE_RANGE,
    CELLS_PER_PLAYER,
    UPGRADES,
)

__all__ = [
    "GameState",
    "Attacker",
    "Defender",
    "CommandTower",
    "EtherDrill",
    "Obstacle",
    "Pixel",
    "PlayerId",
    "Pos",
    "TerrainType",
    "Direction",
    "manhattan_distance",
    "chebyshev_distance",
    "ATK_DIRS",
    "TOKEN_MOVE_RANGE",
    "CELLS_PER_PLAYER",
    "UPGRADES",
]

