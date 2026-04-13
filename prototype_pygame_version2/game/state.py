# ---------------------------------------------------------------------------
# game/state.py — data classes and state initialisation
# ---------------------------------------------------------------------------
from dataclasses import dataclass, field
from typing import Optional
import random

from .constants import (
    ROWS, COLS, CELLS_PER_PLAYER,
    HARD_TERRAIN_COUNT, SOFT_TERRAIN_COUNT, SOFT_TERRAIN_HP,
    UPGRADES,
)


# ---------------------------------------------------------------------------
# Core data classes
# ---------------------------------------------------------------------------

@dataclass
class Cell:
    own:     Optional[str] = None   # 'b' | 'r' | None
    alive:   bool          = False
    hp:      int           = 1
    shld:    bool          = False
    terrain: Optional[str] = None   # 'hard' | 'soft'


@dataclass
class Token:
    pos: Optional[tuple] = None    # (row, col) or None
    mv:  bool            = False   # True = moved this turn (legacy, kept for future use)
    dir: Optional[str]   = None    # 'h' | 'v' | 'd'  — ATK tokens only


@dataclass
class GameState:
    g:           list          = field(default_factory=list)   # Cell[ROWS][COLS]
    hq:          dict          = field(default_factory=dict)   # {'b': (r,c), 'r': (r,c)}
    tok:         dict          = field(default_factory=dict)   # {'b': {'a1','a2','df'}, 'r': ...}
    kills:       dict          = field(default_factory=dict)   # {'b': int, 'r': int}
    upg:         dict          = field(default_factory=dict)   # {'b': set, 'r': set}
    nuke_used:   dict          = field(default_factory=dict)   # {'b': bool, 'r': bool}
    turn:        str           = 'b'
    round:       int           = 1
    phase:       str           = 'intro'
    sel:         Optional[str] = None    # selected token key: 'a1' | 'a2' | 'df'
    nuke_mode:   bool          = False
    pending_dir: Optional[str] = None   # token key awaiting direction choice
    new_upg:     dict          = field(default_factory=dict)   # unlocked this turn
    winner:      Optional[str] = None
    log:         list          = field(default_factory=list)   # [{msg, cls}, ...]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def opp(p: str) -> str:
    """Return the opposing player key."""
    return 'r' if p == 'b' else 'b'


def log_event(state: GameState, msg: str, cls: str = 'info') -> None:
    state.log.insert(0, {'msg': msg, 'cls': cls})
    if len(state.log) > 40:
        state.log.pop()


def in_territory(p: str, r: int, c: int) -> bool:
    """True if (r, c) is within player p's half of the board."""
    return (r + c < 11) if p == 'b' else (r + c > 11)


# ---------------------------------------------------------------------------
# Grid generation
# ---------------------------------------------------------------------------

def _w_sample(items: list, weights: list, n: int) -> list:
    """Weighted random sample without replacement."""
    pool = list(zip(items, weights))
    result = []
    for _ in range(n):
        total = sum(w for _, w in pool)
        r = random.uniform(0, total)
        cum = 0.0
        for i, (item, w) in enumerate(pool):
            cum += w
            if r <= cum:
                result.append(item)
                pool.pop(i)
                break
    return result


def gen_grid() -> list:
    """
    Build the starting board.

    Layout:
        r+c < 11  — Blue territory (upper-left triangle)
        r+c > 11  — Red  territory (lower-right triangle)
        r+c == 11 — Neutral diagonal strip

    24 cells per player, strongly biased toward their home corner.
    Terrain scattered near the mid-board diagonal.
    """
    grid = [[Cell() for _ in range(COLS)] for _ in range(ROWS)]

    # Blue cells — bias toward (0, 0)
    b_cands = [(r, c) for r in range(ROWS) for c in range(COLS) if r + c < 11]
    b_weights = [(12 - r) ** 2 * (12 - c) ** 2 for r, c in b_cands]
    for r, c in _w_sample(b_cands, b_weights, CELLS_PER_PLAYER):
        grid[r][c] = Cell(own='b', alive=True, hp=1)

    # Red cells — bias toward (11, 11)
    r_cands = [(r, c) for r in range(ROWS) for c in range(COLS) if r + c > 11]
    r_weights = [(r + 1) ** 2 * (c + 1) ** 2 for r, c in r_cands]
    for r, c in _w_sample(r_cands, r_weights, CELLS_PER_PLAYER):
        grid[r][c] = Cell(own='r', alive=True, hp=1)

    # Terrain — empty non-diagonal cells, weighted toward mid-board
    empty = [
        (r, c) for r in range(ROWS) for c in range(COLS)
        if r + c != 11 and not grid[r][c].alive and grid[r][c].own is None
    ]
    t_weights = [max(1, 9 - abs(r + c - 11)) for r, c in empty]

    hard_cells = _w_sample(empty, t_weights, HARD_TERRAIN_COUNT)
    hard_set   = set(map(tuple, hard_cells))
    for r, c in hard_cells:
        grid[r][c] = Cell(terrain='hard', alive=True, hp=999)

    remain   = [(r, c) for r, c in empty if (r, c) not in hard_set]
    r_tw     = [max(1, 9 - abs(r + c - 11)) for r, c in remain]
    for r, c in _w_sample(remain, r_tw, SOFT_TERRAIN_COUNT):
        grid[r][c] = Cell(terrain='soft', alive=True, hp=SOFT_TERRAIN_HP)

    return grid


def init_state() -> GameState:
    """Return a fresh GameState ready for the intro screen."""
    return GameState(
        g=gen_grid(),
        hq={'b': None, 'r': None},
        tok={
            'b': {'a1': Token(), 'a2': Token(), 'df': Token()},
            'r': {'a1': Token(), 'a2': Token(), 'df': Token()},
        },
        kills={'b': 0, 'r': 0},
        upg={'b': set(), 'r': set()},
        nuke_used={'b': False, 'r': False},
        new_upg={'b': set(), 'r': set()},
        turn='b', round=1, phase='intro',
    )
