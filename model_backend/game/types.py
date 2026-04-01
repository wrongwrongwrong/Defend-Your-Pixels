from __future__ import annotations

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
    HIGHWAY = "highway"  # 0.5 move cost, but disables attack/defend abilities this turn
    FORTRESS = "fortress"  # 2 move cost, +range for attacker / cheaper shield for defender
    MOUNTAIN = "mountain"  # same as fortress for prototype
    ETHER_DRILL = "ether_drill"  # capturable resource tile
    BLOCKED = "blocked"  # impassable (obstacles)


