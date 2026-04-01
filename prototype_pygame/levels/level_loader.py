"""
Load a level from a .txt map (ASCII art).

First line, if it is only digits → random seed. Otherwise the whole file is the grid.

Symbols
-------
  #  wall / border (blocked)
  . or space  walkable floor
  E  ether drill (capturable)
  H  Player 1 command tower (headquarters)
  h  Player 2 command tower
  A  Player 1 attacker      a  Player 2 attacker
  D  Player 1 defender      d  Player 2 defender
"""

from __future__ import annotations

from pathlib import Path

from model_backend.game import Attacker, CommandTower, Defender, GameState, PlayerId
from model_backend.game.types import Pos, TerrainType

# `e` is not used — ether drills are always `E`
_GRID_CHARS = set("#. EHhAaDd ")


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
        for c in row:
            if c not in _GRID_CHARS:
                raise ValueError(f"Unknown character {c!r} in {path}")

    height = len(grid_lines)
    g = GameState(seed=seed, board_width=width, board_height=height)

    unit_index = 0
    for y, row in enumerate(grid_lines):
        for x, ch in enumerate(row):
            p = Pos(x, y)
            if ch == "#":
                g.board.get(p).terrain = TerrainType.BLOCKED
            elif ch in " .":
                g.board.get(p).terrain = TerrainType.PLAIN
            elif ch == "E":
                g.add_drill(p, yield_per_turn=1)
            elif ch == "H":
                g.board.get(p).terrain = TerrainType.PLAIN
                g.towers[PlayerId.P1] = CommandTower(PlayerId.P1, pos=p)
            elif ch == "h":
                g.board.get(p).terrain = TerrainType.PLAIN
                g.towers[PlayerId.P2] = CommandTower(PlayerId.P2, pos=p)
            elif ch == "A":
                g.board.get(p).terrain = TerrainType.PLAIN
                uid = f"u{unit_index}"
                unit_index += 1
                g.add_unit(Attacker(uid, PlayerId.P1, p))
            elif ch == "a":
                g.board.get(p).terrain = TerrainType.PLAIN
                uid = f"u{unit_index}"
                unit_index += 1
                g.add_unit(Attacker(uid, PlayerId.P2, p))
            elif ch == "D":
                g.board.get(p).terrain = TerrainType.PLAIN
                uid = f"u{unit_index}"
                unit_index += 1
                g.add_unit(Defender(uid, PlayerId.P1, p))
            elif ch == "d":
                g.board.get(p).terrain = TerrainType.PLAIN
                uid = f"u{unit_index}"
                unit_index += 1
                g.add_unit(Defender(uid, PlayerId.P2, p))

    if PlayerId.P1 not in g.towers or PlayerId.P2 not in g.towers:
        raise ValueError(f"Map must contain both H (P1 HQ) and h (P2 HQ): {path}")

    g.start_turn()
    return g
