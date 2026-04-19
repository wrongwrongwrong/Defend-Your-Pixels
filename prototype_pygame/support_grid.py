"""
Layout constants for pygame (cell size, colours). Grid width/height come from GameState.
"""

from __future__ import annotations

CELL = 48

COLOUR_BG = (12, 18, 32)
COLOUR_GRID = (40, 55, 80)
COLOUR_PLAIN = (25, 35, 55)
COLOUR_HIGHWAY = (45, 45, 70)
COLOUR_BLOCKED = (55, 55, 62)
COLOUR_P1 = (70, 130, 220)
COLOUR_P2 = (220, 90, 70)
COLOUR_TOWER_P1 = (200, 170, 60)
COLOUR_TOWER_P2 = (200, 120, 60)
COLOUR_TEXT = (235, 240, 250)
COLOUR_HUD_BG = (18, 24, 40)


def cell_rect_px(x: int, y: int) -> tuple[int, int, int, int]:
    return (x * CELL, y * CELL, CELL, CELL)


def compute_screen_size(grid_w: int, grid_h: int) -> tuple[int, int]:
    hud_w = 280
    pad = 40
    return (grid_w * CELL + hud_w + 16, grid_h * CELL + pad)
