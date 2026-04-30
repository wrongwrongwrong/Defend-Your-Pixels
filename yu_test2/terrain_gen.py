"""
Symmetric random terrain and resource generator.

The live map keeps mirrored terrain for fairness, but resources are now a scored
subset of each side's territory:

- roughly 80% of each side is attackable resource territory
- most resource cells are worth 1 point
- 4 cells are worth 2 points
- 2 cells are worth 3 points
- 1 visible "5-point" stronghold is worth 5 points and takes 3 hits
"""

import math
import random

GRID_COLS = 12
GRID_ROWS = 12

N_HARD_PER_SIDE = 2
N_SOFT_PER_SIDE = 2
FENCE_BUFFER = 2
DEF_CENTRE_EXCL = True
RESOURCE_COVERAGE = 0.80
RESOURCE_TWO_POINT_COUNT = 4
RESOURCE_THREE_POINT_COUNT = 2

P1_FIVE_POINT_ZONE = tuple((c, r) for c in range(2, 5) for r in range(1, 4))
P2_FIVE_POINT_ZONE = tuple((c, r) for c in range(7, 10) for r in range(8, 11))


def _weighted_sample(rng: random.Random, items: list[tuple[int, int]], weights: list[int], count: int) -> list[tuple[int, int]]:
    pool = list(zip(items, weights))
    result: list[tuple[int, int]] = []
    for _ in range(min(count, len(pool))):
        total = sum(weight for _, weight in pool)
        pick = rng.uniform(0, total)
        seen = 0.0
        for index, (item, weight) in enumerate(pool):
            seen += weight
            if pick <= seen:
                result.append(item)
                pool.pop(index)
                break
    return result


def _pack(cells: list[tuple[int, int]], prefix: str) -> list[dict]:
    return [{"id": f"{prefix}_{i}", "name": f"{prefix}_{i}", "col": c, "row": r} for i, (c, r) in enumerate(cells)]


def _pack_resources(cells: list[tuple[int, int]], *, five_point_cell: tuple[int, int], two_point_cells: set[tuple[int, int]], three_point_cells: set[tuple[int, int]]) -> list[dict]:
    packed: list[dict] = []
    for index, (c, r) in enumerate(cells):
        value = 1
        max_hp = 1
        visible = False
        resource_type = "standard"
        if (c, r) == five_point_cell:
            value = 5
            max_hp = 3
            visible = True
            resource_type = "stronghold"
        elif (c, r) in three_point_cells:
            value = 3
            resource_type = "bonus"
        elif (c, r) in two_point_cells:
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
        if c + r < 11 and (c, r) not in terrain_set
    ]
    resource_count = math.floor(((GRID_COLS * GRID_ROWS) - GRID_COLS) / 2 * RESOURCE_COVERAGE)
    if len(p1_eligible) < resource_count:
        raise RuntimeError("Not enough valid cells for resource generation")

    p1_five_candidates = [cell for cell in P1_FIVE_POINT_ZONE if cell in p1_eligible]
    if not p1_five_candidates:
        raise RuntimeError("No valid five-point cells on P1 side")
    p1_five_cell = rng.choice(p1_five_candidates)

    remaining = [cell for cell in p1_eligible if cell != p1_five_cell]
    weights = [(12 - c) ** 2 * (12 - r) ** 2 for c, r in remaining]
    p1_resource_cells = [p1_five_cell] + _weighted_sample(rng, remaining, weights, resource_count - 1)
    rng.shuffle(p1_resource_cells)

    non_five_cells = [cell for cell in p1_resource_cells if cell != p1_five_cell]
    rng.shuffle(non_five_cells)
    p1_two_point_cells = set(non_five_cells[:RESOURCE_TWO_POINT_COUNT])
    p1_three_point_cells = set(non_five_cells[RESOURCE_TWO_POINT_COUNT:RESOURCE_TWO_POINT_COUNT + RESOURCE_THREE_POINT_COUNT])

    p2_five_cell = (11 - p1_five_cell[0], 11 - p1_five_cell[1])
    p2_resource_cells = mirror(p1_resource_cells)
    p2_two_point_cells = set(mirror(list(p1_two_point_cells)))
    p2_three_point_cells = set(mirror(list(p1_three_point_cells)))

    p1_resources = _pack_resources(
        p1_resource_cells,
        five_point_cell=p1_five_cell,
        two_point_cells=p1_two_point_cells,
        three_point_cells=p1_three_point_cells,
    )
    p2_resources = _pack_resources(
        p2_resource_cells,
        five_point_cell=p2_five_cell,
        two_point_cells=p2_two_point_cells,
        three_point_cells=p2_three_point_cells,
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
