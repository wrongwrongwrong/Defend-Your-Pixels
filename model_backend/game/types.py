from __future__ import annotations

"""Shared primitive types for the rules engine.

This module keeps small, dependency-light definitions (enums, grid coordinates, helpers)
that are imported widely across the model and bridge.
"""

from dataclasses import dataclass
from enum import Enum, IntEnum


class PlayerId(IntEnum):
    P1 = 1
    P2 = 2


@dataclass(frozen=True, slots=True)
class Pos:
    x: int
    y: int

    def __add__(self, other: "Pos") -> "Pos":
        return Pos(self.x + other.x, self.y + other.y)


def manhattan_distance(a: Pos, b: Pos) -> int:
    return abs(a.x - b.x) + abs(a.y - b.y)


def chebyshev_distance(a: Pos, b: Pos) -> int:
    return max(abs(a.x - b.x), abs(a.y - b.y))


class Direction(Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"

    def delta(self) -> Pos:
        return {
            Direction.UP: Pos(0, -1),
            Direction.DOWN: Pos(0, 1),
            Direction.LEFT: Pos(-1, 0),
            Direction.RIGHT: Pos(1, 0),
        }[self]


class TerrainType(Enum):
    PLAIN = "plain"
    HIGHWAY = "highway"
    FORTRESS = "fortress"
    MOUNTAIN = "mountain"
    ETHER_DRILL = "ether_drill"
    BLOCKED = "blocked"  # walls (indestructible) and barricade sites (destructible via Obstacle)


CELLS_PER_PLAYER = 24
TOKEN_MOVE_RANGE = 2
BARRICADE_HP = 2

ATK_DIRS: dict[PlayerId, dict[str, Pos]] = {
    PlayerId.P1: {"h": Pos(1, 0), "v": Pos(0, 1), "d": Pos(1, 1)},
    PlayerId.P2: {"h": Pos(-1, 0), "v": Pos(0, -1), "d": Pos(-1, -1)},
}

UPGRADES: list[tuple[int, str, str, str]] = [
    (3,  "t2",  "Splash",    "ATK hits 1 adjacent enemy after primary"),
    (6,  "dt2", "DEF+",      "DEF shield radius 1→2 (3×3→5×5)"),
    (10, "t3",  "Bonus ATK", "Extra attack fires from first ATK each resolve"),
]


