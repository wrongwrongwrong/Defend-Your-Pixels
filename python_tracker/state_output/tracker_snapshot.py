import cv2
import numpy as np

from python_tracker.calibration.homography import GRID_COLS, GRID_ROWS, build_homography, pixel_to_grid
from python_tracker.token_detection.token_rotation import compute_rotation_deg


BOARD_CORNER_IDS = {0, 1, 2, 3}
TOKEN_IDS = set(range(10, 18))


def build_tracker_snapshot(corners, ids):
    markers_out = []
    board_corners_out = []
    board_corners_px = {}

    if ids is None:
        return {
            "calibration_ready": False,
            "markers": markers_out,
            "board_corners": board_corners_out,
        }

    for i, mid in enumerate(ids.flatten()):
        if mid in BOARD_CORNER_IDS:
            center = corners[i][0].mean(axis=0)
            board_corners_px[int(mid)] = center
            board_corners_out.append({
                "id": int(mid),
                "position": {"x": round(float(center[0]), 1), "y": round(float(center[1]), 1)},
            })

    H = build_homography(board_corners_px)

    for i, mid in enumerate(ids.flatten()):
        if mid not in TOKEN_IDS:
            continue

        center = corners[i][0].mean(axis=0)
        px, py = float(center[0]), float(center[1])
        rotation_deg = compute_rotation_deg(corners[i][0])
        gx, gy = pixel_to_grid(px, py, H)

        if gx is not None:
            markers_out.append({
                "id": int(mid),
                "position": {"x": gx, "y": gy},
                "rotation": round(rotation_deg, 1),
            })
        else:
            markers_out.append({
                "id": int(mid),
                "position": {"x": round(px, 1), "y": round(py, 1)},
                "rotation": round(rotation_deg, 1),
            })

    return {
        "calibration_ready": H is not None,
        "markers": markers_out,
        "board_corners": board_corners_out,
        "homography": H,
    }


def build_tracker_preview(frame, detector) -> tuple[dict, object]:
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
        draw_grid_overlay(frame, H)

    for i, mid in enumerate(ids.flatten()):
        if mid not in TOKEN_IDS:
            continue

        center = corners[i][0].mean(axis=0)
        px, py = float(center[0]), float(center[1])
        rotation_deg = compute_rotation_deg(corners[i][0])
        gx, gy = pixel_to_grid(px, py, H)

        if gx is not None:
            label = f"ID:{mid} G({gx:.1f},{gy:.1f}) R:{rotation_deg:.0f}°"
        else:
            label = f"ID:{mid} (no corners)"

        cv2.putText(frame, label, (int(px) + 5, int(py) - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 255, 100), 1, cv2.LINE_AA)

    return snapshot, frame


def draw_grid_overlay(frame, H):
    try:
        H_inv = np.linalg.inv(H)
        for col in range(1, GRID_COLS):
            pts = np.float32([[[col, 0]], [[col, GRID_ROWS]]])
            src = cv2.perspectiveTransform(pts, H_inv)
            p1 = tuple(src[0][0].astype(int))
            p2 = tuple(src[1][0].astype(int))
            cv2.line(frame, p1, p2, (60, 60, 120), 1)
        for row in range(1, GRID_ROWS):
            pts = np.float32([[[0, row]], [[GRID_COLS, row]]])
            src = cv2.perspectiveTransform(pts, H_inv)
            p1 = tuple(src[0][0].astype(int))
            p2 = tuple(src[1][0].astype(int))
            cv2.line(frame, p1, p2, (60, 60, 120), 1)
    except Exception:
        pass
