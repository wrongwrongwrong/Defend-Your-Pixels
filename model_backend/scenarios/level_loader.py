"""
Load a scenario from a .txt map (ASCII art).

First line, if it is only digits -> random seed. Otherwise the whole file is the grid.

Symbols
-------
  #  wall / border (blocked)
  . or space  walkable floor
  H  Player 1 command tower (headquarters)
  h  Player 2 command tower
  A  Player 1 attacker      a  Player 2 attacker
  D  Player 1 defender      d  Player 2 defender
"""

from __future__ import annotations

from pathlib import Path

from model_backend.game import Attacker, CommandTower, Defender, GameState, PlayerId
from model_backend.game.types import Pos, TerrainType

_GRID_CHARS = set("#. HhAaDd ")


def load_level_from_path(path: str | Path) -> GameState:
    raw = Path(path).read_text(encoding="utf-8")
    lines = [ln.rstrip("\n") for ln in raw.splitlines() if ln.strip() != ""]

    seed = 1
    grid_lines = lines
    if lines and lines[0].strip().isdigit():
        seed = int(lines[0].strip())
        grid_lines = lines[1:]

    if not grid_lines:
        raise ValueError(f"Empty grid in {path}")

    width = len(grid_lines[0])
    for i, row in enumerate(grid_lines):
        if len(row) != width:
            raise ValueError(f"Row {i} length {len(row)} != {width} in {path}")
        for char in row:
            if char not in _GRID_CHARS:
                raise ValueError(f"Unknown character {char!r} in {path}")

    height = len(grid_lines)
    game = GameState(seed=seed, board_width=width, board_height=height)

    unit_index = 0
    for y, row in enumerate(grid_lines):
        for x, char in enumerate(row):
            pos = Pos(x, y)
            if char == "#":
                game.board.get(pos).terrain = TerrainType.BLOCKED
            elif char in " .":
                game.board.get(pos).terrain = TerrainType.PLAIN
            elif char == "H":
                game.board.get(pos).terrain = TerrainType.PLAIN
                game.towers[PlayerId.P1] = CommandTower(PlayerId.P1, pos=pos)
            elif char == "h":
                game.board.get(pos).terrain = TerrainType.PLAIN
                game.towers[PlayerId.P2] = CommandTower(PlayerId.P2, pos=pos)
            elif char == "A":
                game.board.get(pos).terrain = TerrainType.PLAIN
                unit_id = f"u{unit_index}"
                unit_index += 1
                game.add_unit(Attacker(unit_id, PlayerId.P1, pos))
            elif char == "a":
                game.board.get(pos).terrain = TerrainType.PLAIN
                unit_id = f"u{unit_index}"
                unit_index += 1
                game.add_unit(Attacker(unit_id, PlayerId.P2, pos))
            elif char == "D":
                game.board.get(pos).terrain = TerrainType.PLAIN
                unit_id = f"u{unit_index}"
                unit_index += 1
                game.add_unit(Defender(unit_id, PlayerId.P1, pos))
            elif char == "d":
                game.board.get(pos).terrain = TerrainType.PLAIN
                unit_id = f"u{unit_index}"
                unit_index += 1
                game.add_unit(Defender(unit_id, PlayerId.P2, pos))

    if PlayerId.P1 not in game.towers or PlayerId.P2 not in game.towers:
        raise ValueError(f"Map must contain both H (P1 HQ) and h (P2 HQ): {path}")

    game.spawn_default_pixels()
    game.start_turn()
    return game
