"""
Symmetric random terrain generator.

P2 terrain positions are always a 180° rotation of P1's, so the map is
perfectly fair. Terrain is placed only in each side's own triangle, with
a buffer around the fence-line diagonal and the DEF spawn area.
"""

import random

GRID_COLS = 12
GRID_ROWS = 12

N_HARD_PER_SIDE    = 2
N_SOFT_PER_SIDE    = 2
FENCE_BUFFER       = 2    # minimum cells away from the diagonal fence (terrain only)
DEF_CENTRE_EXCL    = True # keep the DEF spawn zone clear (terrain only)


def generate(seed: int | None = None) -> dict:
    """Return dict {p1_hard, p1_soft, p2_hard, p2_soft, seed}."""
    rng = random.Random(seed)

    candidates = []
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            # Keep away from the fence diagonal
            if c + r >= 11 - FENCE_BUFFER + 1:
                continue
            # Keep DEF default spawn area clear
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

    # Resource cells are every non-fence, non-terrain cell on a side.
    terrain_set = set(p1_hard_cells) | set(p1_soft_cells)
    p1_resource_cells = [(c, r) for r in range(GRID_ROWS) for c in range(GRID_COLS)
                         if c + r < 11 and (c, r) not in terrain_set]

    def pack(cells, prefix):
        return [{"id": f"{prefix}_{i}", "name": f"{prefix}_{i}",
                 "col": c, "row": r} for i, (c, r) in enumerate(cells)]

    def pack_cells(cells):
        return [{"col": c, "row": r} for c, r in cells]

    return {
        "p1_hard":    pack(p1_hard_cells,         "fence"),
        "p1_soft":    pack(p1_soft_cells,         "scarecrow"),
        "p2_hard":    pack(mirror(p1_hard_cells), "mound"),
        "p2_soft":    pack(mirror(p1_soft_cells), "spinifex"),
        "p1_resources": pack_cells(p1_resource_cells),
        "p2_resources": pack_cells(mirror(p1_resource_cells)),
        # Legacy alias kept while callers transition off the old target-cell naming.
        "p1_targets": pack_cells(p1_resource_cells),
        "p2_targets": pack_cells(mirror(p1_resource_cells)),
        "seed":       seed,
    }
