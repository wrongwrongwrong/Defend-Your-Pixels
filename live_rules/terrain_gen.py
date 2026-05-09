"""Symmetric random terrain and resource generator.

Each side gets a mirrored set of 24 attackable resource cells:

- 22 cells are worth 1 point
- 2 hidden cells are worth 2 points
- all resource cells share the same presentation
"""

import random

GRID_COLS = 12
GRID_ROWS = 12

N_HARD_PER_SIDE = 3
N_SOFT_PER_SIDE = 3
FENCE_BUFFER = 2
DEF_CENTRE_EXCL = True
RESOURCE_COUNT = 24
RESOURCE_TWO_POINT_COUNT = 2
RESERVED_CELLS = frozenset({(0, 0), (0, 1), (1, 0), (11, 11), (11, 10), (10, 11)})


def _pack(cells: list[tuple[int, int]], prefix: str) -> list[dict]:
    return [{"id": f"{prefix}_{i}", "name": f"{prefix}_{i}", "col": c, "row": r} for i, (c, r) in enumerate(cells)]


def _pack_resources(cells: list[tuple[int, int]], *, two_point_cells: set[tuple[int, int]]) -> list[dict]:
    packed: list[dict] = []
    for index, (c, r) in enumerate(cells):
        value = 1
        max_hp = 1
        visible = False
        resource_type = "standard"
        if (c, r) in two_point_cells:
            value = 2
            resource_type = "bonus"

        packed.append({
            "id": f"resource_{index}",
            "col": c,
            "row": r,
            "value": value,
            "max_hp": max_hp,
            "visible": visible,
            "resource_type": resource_type,
        })
    return packed


def generate(seed: int | None = None) -> dict:
    """Return dict {p1_hard, p1_soft, p2_hard, p2_soft, p1_resources, p2_resources, seed}."""
    rng = random.Random(seed)

    candidates = []
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            if c + r >= 11 - FENCE_BUFFER + 1:
                continue
            if (c, r) in RESERVED_CELLS:
                continue
            if DEF_CENTRE_EXCL and 3 <= c <= 5 and 8 <= r <= 10:
                continue
            candidates.append((c, r))

    rng.shuffle(candidates)
    need = N_HARD_PER_SIDE + N_SOFT_PER_SIDE
    if len(candidates) < need:
        raise RuntimeError("Not enough valid cells for terrain generation")

    p1_hard_cells = candidates[:N_HARD_PER_SIDE]
    p1_soft_cells = candidates[N_HARD_PER_SIDE:need]
    mirror = lambda cells: [(11 - c, 11 - r) for c, r in cells]

    terrain_set = set(p1_hard_cells) | set(p1_soft_cells)
    p1_eligible = [
        (c, r)
        for r in range(GRID_ROWS)
        for c in range(GRID_COLS)
        if c + r < 11 and (c, r) not in terrain_set and (c, r) not in RESERVED_CELLS
    ]
    if len(p1_eligible) < RESOURCE_COUNT:
        raise RuntimeError("Not enough valid cells for resource generation")

    p1_resource_cells = rng.sample(p1_eligible, RESOURCE_COUNT)
    rng.shuffle(p1_resource_cells)

    bonus_cells = list(p1_resource_cells)
    rng.shuffle(bonus_cells)
    p1_two_point_cells = set(bonus_cells[:RESOURCE_TWO_POINT_COUNT])

    p2_resource_cells = mirror(p1_resource_cells)
    p2_two_point_cells = set(mirror(list(p1_two_point_cells)))

    p1_resources = _pack_resources(
        p1_resource_cells,
        two_point_cells=p1_two_point_cells,
    )
    p2_resources = _pack_resources(
        p2_resource_cells,
        two_point_cells=p2_two_point_cells,
    )

    return {
        "p1_hard": _pack(p1_hard_cells, "fence"),
        "p1_soft": _pack(p1_soft_cells, "scarecrow"),
        "p2_hard": _pack(mirror(p1_hard_cells), "mound"),
        "p2_soft": _pack(mirror(p1_soft_cells), "spinifex"),
        "p1_resources": p1_resources,
        "p2_resources": p2_resources,
        # Legacy alias kept while callers transition off the old target-cell naming.
        "p1_targets": [{"col": cell["col"], "row": cell["row"]} for cell in p1_resources],
        "p2_targets": [{"col": cell["col"], "row": cell["row"]} for cell in p2_resources],
        "seed": seed,
    }
