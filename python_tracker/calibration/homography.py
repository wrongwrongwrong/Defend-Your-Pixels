"""Board calibration via homography (pixel -> grid mapping).

Given 4 detected board-corner markers in pixel coordinates, this module builds a
homography matrix that maps camera pixels into board grid coordinates.
"""

import cv2
import numpy as np


GRID_COLS = 12
GRID_ROWS = 12


def build_homography(board_corners_px: dict):
    if not all(k in board_corners_px for k in [0, 1, 2, 3]):
        return None

    src = np.float32([
        board_corners_px[0],
        board_corners_px[1],
        board_corners_px[2],
        board_corners_px[3],
    ])

    dst = np.float32([
        [0, 0],
        [GRID_COLS, 0],
        [0, GRID_ROWS],
        [GRID_COLS, GRID_ROWS],
    ])

    H, _ = cv2.findHomography(src, dst)
    return H


def pixel_to_grid(px: float, py: float, H) -> tuple[float, float] | tuple[None, None]:
    if H is None:
        return None, None

    warped = _warp_point(px, py, H)
    if warped is None:
        return None, None

    gx = float(np.clip(warped[0], 0, GRID_COLS - 1))
    gy = float(np.clip(warped[1], 0, GRID_ROWS - 1))
    return round(gx, 2), round(gy, 2)


def pixel_to_grid_with_bounds(px: float, py: float, H) -> tuple[float, float, bool] | tuple[None, None, bool]:
    if H is None:
        return None, None, False

    warped = _warp_point(px, py, H)
    if warped is None:
        return None, None, False

    raw_x = float(warped[0])
    raw_y = float(warped[1])
    in_bounds = 0.0 <= raw_x < GRID_COLS and 0.0 <= raw_y < GRID_ROWS
    gx = float(np.clip(raw_x, 0, GRID_COLS - 1))
    gy = float(np.clip(raw_y, 0, GRID_ROWS - 1))
    return round(gx, 2), round(gy, 2), in_bounds


def _warp_point(px: float, py: float, H):
    if H is None:
        return None
    pt = np.float32([[[px, py]]])
    return cv2.perspectiveTransform(pt, H)[0][0]
