"""
Terrain generator for Defend Your Pixels.

Generates per-game:
  - 24 active resource cells per player  (p1_resources / p2_resources)
  - 2 hard terrain cells per player      (p1_hard / p2_hard)
  - 3 soft terrain cells per player      (p1_soft / p2_soft)
  - 1 default HQ position per player     (hq_p1 / hq_p2)

Territory split: anti-diagonal.
  P1 (Old Mick / upper-left):  col + row < 11
  P2 (The Mob  / lower-right): col + row >= 11
"""

import random

GRID_SIZE        = 12
ACTIVE_CELLS     = 24
HARD_PER_PLAYER  = 2
SOFT_PER_PLAYER  = 3
FENCE_BUFFER     = 1          # cells within this distance of fence are excluded
CORNER_CELLS     = frozenset({(0, 0), (GRID_SIZE - 1, GRID_SIZE - 1)})


def _is_p1(col: int, row: int) -> bool:
    return col + row < GRID_SIZE - 1


def _is_p2(col: int, row: int) -> bool:
    return col + row >= GRID_SIZE - 1


def _pool(side_fn) -> list:
    """All valid cells for a side, excluding fence buffer and corners."""
    return [
        (c, r)
        for c in range(GRID_SIZE)
        for r in range(GRID_SIZE)
        if side_fn(c, r)
        and abs((c + r) - (GRID_SIZE - 1)) > FENCE_BUFFER
        and (c, r) not in CORNER_CELLS
    ]


def generate(seed=None) -> dict:
    """Return a terrain dict the server and game_model can use directly."""
    rng = random.Random(seed)

    p1_pool = _pool(_is_p1)
    p2_pool = _pool(_is_p2)

    # ── Active resource cells ─────────────────────────────────────────────────
    p1_active = rng.sample(p1_pool, min(ACTIVE_CELLS, len(p1_pool)))
    p2_active = rng.sample(p2_pool, min(ACTIVE_CELLS, len(p2_pool)))
    active_set = set(p1_active) | set(p2_active)

    # ── Terrain ───────────────────────────────────────────────────────────────
    p1_terrain_pool = [c for c in p1_pool if c not in active_set]
    p2_terrain_pool = [c for c in p2_pool if c not in active_set]
    rng.shuffle(p1_terrain_pool)
    rng.shuffle(p2_terrain_pool)

    p1_terrain = p1_terrain_pool[:HARD_PER_PLAYER + SOFT_PER_PLAYER]
    p2_terrain = p2_terrain_pool[:HARD_PER_PLAYER + SOFT_PER_PLAYER]
    terrain_set = set(p1_terrain) | set(p2_terrain)

    p1_hard = [{"col": c, "row": r} for c, r in p1_terrain[:HARD_PER_PLAYER]]
    p1_soft = [{"col": c, "row": r} for c, r in p1_terrain[HARD_PER_PLAYER:]]
    p2_hard = [{"col": c, "row": r} for c, r in p2_terrain[:HARD_PER_PLAYER]]
    p2_soft = [{"col": c, "row": r} for c, r in p2_terrain[HARD_PER_PLAYER:]]

    # ── Default HQ positions ──────────────────────────────────────────────────
    occupied = active_set | terrain_set
    p1_hq_pool = [c for c in p1_pool if c not in occupied]
    p2_hq_pool = [c for c in p2_pool if c not in occupied]
    hq_p1 = list(rng.choice(p1_hq_pool)) if p1_hq_pool else None
    hq_p2 = list(rng.choice(p2_hq_pool)) if p2_hq_pool else None

    return {
        "p1_resources": [
            {"col": c, "row": r, "hp": 1, "resource_type": "normal"}
            for c, r in p1_active
        ],
        "p2_resources": [
            {"col": c, "row": r, "hp": 1, "resource_type": "normal"}
            for c, r in p2_active
        ],
        "p1_hard": p1_hard,
        "p2_hard": p2_hard,
        "p1_soft": p1_soft,
        "p2_soft": p2_soft,
        "hq_p1":   hq_p1,
        "hq_p2":   hq_p2,
    }
