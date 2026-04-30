"""Build a tracker snapshot from detected ArUco markers.

This module converts OpenCV marker detections (`corners`, `ids`) into a plain dict
snapshot used by:
- preview UIs (camera overlays)
- the bridge layer (telemetry message + move-intent inference)

The snapshot includes:
- calibration readiness (homography built from corner markers)
- per-marker grid positions when calibrated (else raw pixel positions)
- marker rotation in degrees
"""

import cv2
import numpy as np

from python_tracker.tracked_markers import HQ_MARKER_IDS, TOKEN_IDS, TURN_MARKER_IDS, marker_label
from python_tracker.calibration.homography import (
    GRID_COLS,
    GRID_ROWS,
    build_homography,
    build_playable_corners,
    pixel_to_grid_with_bounds,
)
from python_tracker.token_detection.token_rotation import compute_rotation_deg


BOARD_CORNER_IDS = {0, 1, 2, 3}

ALL_TRACKED_IDS = TOKEN_IDS | TURN_MARKER_IDS | HQ_MARKER_IDS


def build_tracker_snapshot(corners, ids):
    # This payload is intentionally plain JSON-friendly data. Bridge and preview code
    # should not need OpenCV arrays or detector-specific objects.
    markers_out = []
    board_corners_out = []
    board_corners_px = {}

    if ids is None:
        return {
            "calibration_ready": False,
            "markers": markers_out,
            "hq_markers": [],
            "turn_markers": [],
            "board_corners": board_corners_out,
        }

    for i, mid in enumerate(ids.flatten()):
        if mid in BOARD_CORNER_IDS:
            marker_corners = corners[i][0]
            center = marker_corners.mean(axis=0)
            board_corners_px[int(mid)] = {
                "center": center,
                "size_px": _marker_size_px(marker_corners),
            }
            board_corners_out.append({
                "id": int(mid),
                "position": {"x": round(float(center[0]), 1), "y": round(float(center[1]), 1)},
            })

    # Corner markers define the board calibration. Token positions only become grid
    # coordinates once this homography exists.
    H = build_homography(board_corners_px)
    playable_corners = build_playable_corners(board_corners_px)

    turn_markers_out = []
    hq_markers_out = []

    for i, mid in enumerate(ids.flatten()):
        if mid in TURN_MARKER_IDS:
            center = corners[i][0].mean(axis=0)
            rotation_deg = compute_rotation_deg(corners[i][0])
            turn_markers_out.append({
                "id": int(mid),
                "raw_position": {"x": round(float(center[0]), 1), "y": round(float(center[1]), 1)},
                "rotation": round(rotation_deg, 1),
            })
            continue

        if mid in HQ_MARKER_IDS:
            center = corners[i][0].mean(axis=0)
            px, py = float(center[0]), float(center[1])
            rotation_deg = compute_rotation_deg(corners[i][0])
            gx, gy, in_bounds = pixel_to_grid_with_bounds(px, py, H)
            hq_markers_out.append({
                "id": int(mid),
                "position": {"x": gx, "y": gy} if gx is not None and in_bounds else None,
                "raw_position": {"x": round(px, 1), "y": round(py, 1)},
                "in_bounds": in_bounds,
                "rotation": round(rotation_deg, 1),
            })
            continue

        if mid not in TOKEN_IDS:
            continue

        center = corners[i][0].mean(axis=0)
        px, py = float(center[0]), float(center[1])
        rotation_deg = compute_rotation_deg(corners[i][0])
        gx, gy, in_bounds = pixel_to_grid_with_bounds(px, py, H)

        if gx is not None:
            markers_out.append({
                "id": int(mid),
                "position": {"x": gx, "y": gy} if in_bounds else None,
                "raw_position": {"x": round(px, 1), "y": round(py, 1)},
                "in_bounds": in_bounds,
                "rotation": round(rotation_deg, 1),
            })
        else:
            markers_out.append({
                "id": int(mid),
                "position": {"x": round(px, 1), "y": round(py, 1)},
                "raw_position": {"x": round(px, 1), "y": round(py, 1)},
                "in_bounds": False,
                "rotation": round(rotation_deg, 1),
            })

    return {
        "calibration_ready": H is not None,
        "markers": markers_out,
        "hq_markers": hq_markers_out,
        "turn_markers": turn_markers_out,
        "board_corners": board_corners_out,
        "playable_corners": _serialize_playable_corners(playable_corners),
        "homography": H,
    }


def apply_calibration_fallback(snapshot: dict, fallback_snapshot: dict | None) -> dict:
    # If corners drop out for a frame or two, keep using the last good homography so
    # token positions remain stable enough for UI feedback and move-intent inference.
    if snapshot.get("calibration_ready"):
        return snapshot
    if not fallback_snapshot or not fallback_snapshot.get("calibration_ready"):
        return snapshot

    fallback_h = fallback_snapshot.get("homography")
    if fallback_h is None:
        return snapshot

    remapped_markers = _remap_marker_positions(snapshot.get("markers", []), fallback_h)
    remapped_hq_markers = _remap_marker_positions(snapshot.get("hq_markers", []), fallback_h)

    return {
        **snapshot,
        "calibration_ready": True,
        "markers": remapped_markers,
        "hq_markers": remapped_hq_markers,
        "board_corners": snapshot.get("board_corners") or fallback_snapshot.get("board_corners", []),
        "playable_corners": fallback_snapshot.get("playable_corners", []),
        "homography": fallback_h,
    }


def _remap_marker_positions(markers: list[dict], homography) -> list[dict]:
    remapped_markers = []
    for marker in markers:
        raw_position = marker.get("raw_position")
        if not isinstance(raw_position, dict):
            remapped_markers.append(marker)
            continue

        raw_x = raw_position.get("x")
        raw_y = raw_position.get("y")
        if not isinstance(raw_x, (int, float)) or not isinstance(raw_y, (int, float)):
            remapped_markers.append(marker)
            continue

        gx, gy, in_bounds = pixel_to_grid_with_bounds(float(raw_x), float(raw_y), homography)
        if gx is None or gy is None:
            remapped_markers.append(marker)
            continue

        remapped_markers.append({
            **marker,
            "position": {"x": gx, "y": gy} if in_bounds else None,
            "in_bounds": in_bounds,
        })

    return remapped_markers


def build_tracker_preview(frame, detector) -> tuple[dict, object]:
    # Preview mode shares the same snapshot builder as the live bridge path so the
    # on-screen diagnostics match the actual data sent to the frontend.
    corners, ids, _ = detector.detectMarkers(frame)
    snapshot = build_tracker_snapshot(corners, ids)

    if ids is None:
        cv2.putText(frame, "No markers detected", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 100, 255), 2)
        return snapshot, frame

    cv2.aruco.drawDetectedMarkers(frame, corners, ids)
    n_corners = len(snapshot["board_corners"])
    corner_color = (0, 255, 0) if n_corners == 4 else (0, 140, 255)
    cv2.putText(frame, f"Board corners: {n_corners}/4", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, corner_color, 2)

    H = snapshot["homography"]
    if H is not None:
        draw_playable_area(frame, snapshot.get("playable_corners", []))
        draw_grid_overlay(frame, H)

    for i, mid in enumerate(ids.flatten()):
        if mid not in ALL_TRACKED_IDS:
            continue

        center = corners[i][0].mean(axis=0)
        px, py = float(center[0]), float(center[1])

        if mid in TURN_MARKER_IDS:
            label = token_label(int(mid))
            cv2.putText(frame, label, (int(px) + 5, int(py) - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 200, 255), 2, cv2.LINE_AA)
            continue

        rotation_deg = compute_rotation_deg(corners[i][0])
        gx, gy, in_bounds = pixel_to_grid_with_bounds(px, py, H)

        if gx is None or not in_bounds:
            continue

        label = token_label(int(mid))
        cv2.putText(
            frame,
            label,
            (int(px) + 5, int(py) - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (100, 255, 100),
            2,
            cv2.LINE_AA,
        )

    return snapshot, frame


def annotate_tracker_preview(frame, snapshot: dict) -> object:
    if not snapshot.get("markers") and not snapshot.get("hq_markers") and not snapshot.get("turn_markers") and not snapshot.get("board_corners"):
        cv2.putText(frame, "No markers detected", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 100, 255), 2)
        return frame

    n_corners = len(snapshot.get("board_corners", []))
    corner_color = (0, 255, 0) if n_corners == 4 else (0, 140, 255)
    cv2.putText(frame, f"Board corners: {n_corners}/4", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, corner_color, 2)

    H = snapshot.get("homography")
    if H is not None:
        draw_playable_area(frame, snapshot.get("playable_corners", []))
        draw_grid_overlay(frame, H)

    for marker in snapshot.get("markers", []):
        raw_position = marker.get("raw_position")
        if not isinstance(raw_position, dict):
            continue

        px = raw_position.get("x")
        py = raw_position.get("y")
        if not isinstance(px, (int, float)) or not isinstance(py, (int, float)):
            continue

        label = token_label(int(marker.get("id", -1)))
        cv2.putText(
            frame,
            label,
            (int(px) + 5, int(py) - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (100, 255, 100),
            2,
            cv2.LINE_AA,
        )

    for marker in snapshot.get("hq_markers", []):
        raw_position = marker.get("raw_position")
        if not isinstance(raw_position, dict):
            continue

        px = raw_position.get("x")
        py = raw_position.get("y")
        if not isinstance(px, (int, float)) or not isinstance(py, (int, float)):
            continue

        cv2.putText(
            frame,
            token_label(int(marker.get("id", -1))),
            (int(px) + 5, int(py) - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 220, 120),
            2,
            cv2.LINE_AA,
        )

    for turn_marker in snapshot.get("turn_markers", []):
        if not isinstance(turn_marker, dict) or not isinstance(turn_marker.get("raw_position"), dict):
            continue
        px = turn_marker["raw_position"].get("x")
        py = turn_marker["raw_position"].get("y")
        if isinstance(px, (int, float)) and isinstance(py, (int, float)):
            cv2.putText(
                frame,
                token_label(int(turn_marker.get("id", -1))),
                (int(px) + 5, int(py) - 12),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (80, 200, 255),
                2,
                cv2.LINE_AA,
            )

    return frame


def token_label(marker_id: int) -> str:
    return marker_label(marker_id)


def draw_grid_overlay(frame, H):
    try:
        # Draw grid lines back in camera space by inverting the board homography.
        H_inv = np.linalg.inv(H)
        for col in range(GRID_COLS + 1):
            grid_x = col - 0.5
            pts = np.float32([[[grid_x, -0.5]], [[grid_x, GRID_ROWS - 0.5]]])
            src = cv2.perspectiveTransform(pts, H_inv)
            p1 = tuple(src[0][0].astype(int))
            p2 = tuple(src[1][0].astype(int))
            cv2.line(frame, p1, p2, (60, 60, 120), 1)
        for row in range(GRID_ROWS + 1):
            grid_y = row - 0.5
            pts = np.float32([[[-0.5, grid_y]], [[GRID_COLS - 0.5, grid_y]]])
            src = cv2.perspectiveTransform(pts, H_inv)
            p1 = tuple(src[0][0].astype(int))
            p2 = tuple(src[1][0].astype(int))
            cv2.line(frame, p1, p2, (60, 60, 120), 1)
    except Exception:
        pass


def draw_playable_area(frame, playable_corners: list[dict]) -> None:
    if len(playable_corners) != 4:
        return
    pts = np.array(
        [[corner["position"]["x"], corner["position"]["y"]] for corner in playable_corners],
        dtype=np.int32,
    )
    cv2.polylines(frame, [pts], isClosed=True, color=(0, 0, 255), thickness=2)


def _serialize_playable_corners(playable_corners) -> list[dict]:
    if playable_corners is None:
        return []
    return [
        {
            "position": {
                "x": round(float(point[0]), 1),
                "y": round(float(point[1]), 1),
            }
        }
        for point in playable_corners
    ]


def _marker_size_px(marker_corners) -> float:
    edge_lengths = []
    for index in range(4):
        p1 = marker_corners[index]
        p2 = marker_corners[(index + 1) % 4]
        edge_lengths.append(float(np.linalg.norm(p2 - p1)))
    return sum(edge_lengths) / len(edge_lengths)
