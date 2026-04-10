from __future__ import annotations

"""Grid board representation for the rules engine.

The board stores per-tile terrain (movement/ability constraints) and provides
lightweight bounds checking and accessors.
"""

from dataclasses import dataclass

from .types import Pos, TerrainType


@dataclass(slots=True)
class Tile:
    terrain: TerrainType = TerrainType.PLAIN


class Board:
    def __init__(self, width: int = 12, height: int = 12):
        self.width = width
        self.height = height
        self._tiles = [[Tile() for _ in range(width)] for _ in range(height)]

    def in_bounds(self, p: Pos) -> bool:
        return 0 <= p.x < self.width and 0 <= p.y < self.height

    def get(self, p: Pos) -> Tile:
        if not self.in_bounds(p):
            raise ValueError(f"Out of bounds: {p}")
        return self._tiles[p.y][p.x]

    def set_terrain(self, p: Pos, terrain: TerrainType) -> None:
        self.get(p).terrain = terrain

