"""Board calibration via homography (pixel -> grid mapping).

Given 4 detected board-corner markers in pixel coordinates, this module builds a
homography matrix that maps camera pixels into board grid coordinates.
"""

import cv2
import numpy as np


GRID_COLS = 12
GRID_ROWS = 12
GRID_MIN_X = -0.5
GRID_MIN_Y = -0.5
GRID_MAX_X = GRID_COLS - 0.5
GRID_MAX_Y = GRID_ROWS - 0.5


def build_homography(board_corners_px: dict):
    playable_corners = build_playable_corners(board_corners_px)
    if playable_corners is None:
        return None

    src = playable_corners

    dst = np.float32([
        [GRID_MIN_X, GRID_MIN_Y],
        [GRID_MAX_X, GRID_MIN_Y],
        [GRID_MIN_X, GRID_MAX_Y],
        [GRID_MAX_X, GRID_MAX_Y],
    ])

    H, _ = cv2.findHomography(src, dst)
    return H


def build_playable_corners(board_corners_px: dict) -> np.ndarray | None:
    if not all(k in board_corners_px for k in [0, 1, 2, 3]):
        return None

    # The printed ArUco markers sit on the outer border of the board. We infer the
    # actual playable-corner points by moving inward from each marker center by half
    # a marker size along the two board edges that meet at that corner.
    return np.float32([
        _playable_corner_point(board_corners_px, 0),
        _playable_corner_point(board_corners_px, 1),
        _playable_corner_point(board_corners_px, 2),
        _playable_corner_point(board_corners_px, 3),
    ])


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

    # Keep both a clipped UI-friendly coordinate and a strict in-bounds flag so the
    # caller can reject tokens that are only near the board rather than on it.
    raw_x = float(warped[0])
    raw_y = float(warped[1])
    in_bounds = GRID_MIN_X <= raw_x <= GRID_MAX_X and GRID_MIN_Y <= raw_y <= GRID_MAX_Y
    gx = float(np.clip(raw_x, 0, GRID_COLS - 1))
    gy = float(np.clip(raw_y, 0, GRID_ROWS - 1))
    return round(gx, 2), round(gy, 2), in_bounds


def _warp_point(px: float, py: float, H):
    if H is None:
        return None
    pt = np.float32([[[px, py]]])
    return cv2.perspectiveTransform(pt, H)[0][0]


def _playable_corner_point(board_corners_px: dict, marker_id: int) -> np.ndarray:
    center = _marker_center(board_corners_px[marker_id])
    half_size = _marker_half_size(board_corners_px[marker_id])

    if marker_id == 0:
        horizontal = _unit_vector(_marker_center(board_corners_px[1]) - center)
        vertical = _unit_vector(_marker_center(board_corners_px[2]) - center)
        return center + horizontal * half_size + vertical * half_size
    if marker_id == 1:
        horizontal = _unit_vector(_marker_center(board_corners_px[0]) - center)
        vertical = _unit_vector(_marker_center(board_corners_px[3]) - center)
        return center + horizontal * half_size + vertical * half_size
    if marker_id == 2:
        horizontal = _unit_vector(_marker_center(board_corners_px[3]) - center)
        vertical = _unit_vector(_marker_center(board_corners_px[0]) - center)
        return center + horizontal * half_size + vertical * half_size

    horizontal = _unit_vector(_marker_center(board_corners_px[2]) - center)
    vertical = _unit_vector(_marker_center(board_corners_px[1]) - center)
    return center + horizontal * half_size + vertical * half_size


def _marker_center(marker_value) -> np.ndarray:
    if isinstance(marker_value, dict):
        return np.asarray(marker_value["center"], dtype=np.float32)
    return np.asarray(marker_value, dtype=np.float32)


def _marker_half_size(marker_value) -> float:
    if isinstance(marker_value, dict) and isinstance(marker_value.get("size_px"), (int, float)):
        return float(marker_value["size_px"]) / 2.0
    return 0.0


def _unit_vector(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        return np.array([0.0, 0.0], dtype=np.float32)
    return vector / norm
