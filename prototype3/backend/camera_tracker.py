"""
ArUco marker detection, orientation reading, and board calibration.

Marker ID assignment:
  0  = P1 Attack A
  1  = P1 Attack B
  2  = P1 Defense
  3  = P2 Attack A
  4  = P2 Attack B
  5  = P2 Defense
  6  = Corner TL (calibration)
  7  = Corner TR (calibration)
  8  = Corner BR (calibration)
  9  = Corner BL (calibration)
  10 = P1 Hard terrain A
  11 = P1 Hard terrain B
  12 = P1 Soft terrain
  13 = P2 Hard terrain A
  14 = P2 Hard terrain B
  15 = P2 Soft terrain
  20 = Side selection: Farmer (intro)
  21 = Side selection: Emu (intro)
  22 = Resolve attack (hold up to fire)
"""

import cv2
import numpy as np
import math
from typing import Optional, Dict, Tuple, List

MARKER_MAP = {
    0: ("p1", "attack_a"),
    1: ("p1", "attack_b"),
    2: ("p1", "defense"),
    3: ("p2", "attack_a"),
    4: ("p2", "attack_b"),
    5: ("p2", "defense"),
}
TERRAIN_MAP = {
    10: ("p1", "hard"),
    11: ("p1", "hard"),
    12: ("p1", "soft"),
    13: ("p2", "hard"),
    14: ("p2", "hard"),
    15: ("p2", "soft"),
}
CORNER_IDS = {6: "TL", 7: "TR", 8: "BR", 9: "BL"}
SIDE_IDS = {20: "farmer", 21: "emu"}
CONTROL_IDS = {22: "resolve"}


def compute_marker_angle(corners: np.ndarray) -> float:
    """
    Compute rotation angle of marker from its corner points.
    Returns angle in degrees [0, 180).
    """
    tl = corners[0]
    tr = corners[1]
    dx = tr[0] - tl[0]
    dy = tr[1] - tl[1]
    angle = math.degrees(math.atan2(dy, dx)) % 180
    return angle


class BoardCalibrator:
    """Maintains homography from camera space to board space using corner markers."""

    def __init__(self, grid_size: int = 12):
        self.grid_size = grid_size
        self.homography: Optional[np.ndarray] = None
        # Fallback: use full frame as board
        self._frame_size: Tuple[int, int] = (640, 480)

    def update_from_corners(self, corners_map: Dict[str, Tuple[float, float]],
                             frame_w: int, frame_h: int):
        self._frame_size = (frame_w, frame_h)
        keys = ["TL", "TR", "BR", "BL"]
        if all(k in corners_map for k in keys):
            src = np.float32([corners_map[k] for k in keys])
            dst = np.float32([[0, 0], [frame_w, 0], [frame_w, frame_h], [0, frame_h]])
            self.homography, _ = cv2.findHomography(src, dst)

    def image_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        """Map image pixel coords to grid cell (col, row)."""
        fw, fh = self._frame_size
        if self.homography is not None:
            pt = np.array([[[x, y]]], dtype=np.float32)
            mapped = cv2.perspectiveTransform(pt, self.homography)[0][0]
            nx, ny = mapped[0] / fw, mapped[1] / fh
        else:
            nx, ny = x / fw, y / fh

        col = int(np.clip(nx * self.grid_size, 0, self.grid_size - 1))
        row = int(np.clip(ny * self.grid_size, 0, self.grid_size - 1))
        return col, row


class MarkerTracker:
    def __init__(self, camera_index: int = 0, grid_size: int = 12):
        self.cap = cv2.VideoCapture(camera_index)
        self.calibrator = BoardCalibrator(grid_size)
        self.grid_size = grid_size

        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        params = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(aruco_dict, params)

        # Smoothing: rolling average of last N positions per marker
        self._history: Dict[int, List[Tuple[int, int]]] = {}
        self._HISTORY_LEN = 5

    def _smooth_position(self, marker_id: int, col: int, row: int) -> Tuple[int, int]:
        hist = self._history.setdefault(marker_id, [])
        hist.append((col, row))
        if len(hist) > self._HISTORY_LEN:
            hist.pop(0)
        avg_col = int(round(sum(p[0] for p in hist) / len(hist)))
        avg_row = int(round(sum(p[1] for p in hist) / len(hist)))
        return avg_col, avg_row

    def read_frame(self) -> Optional[dict]:
        """
        Read one frame, detect markers, return parsed marker data.
        Returns None if frame can't be read.
        """
        ret, frame = self.cap.read()
        if not ret:
            return None

        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners_list, ids, _ = self.detector.detectMarkers(gray)

        corner_positions: Dict[str, Tuple[float, float]] = {}
        marker_data = {}

        if ids is not None:
            for i, marker_id in enumerate(ids.flatten()):
                c = corners_list[i][0]
                center_x = float(np.mean(c[:, 0]))
                center_y = float(np.mean(c[:, 1]))

                if marker_id in CORNER_IDS:
                    label = CORNER_IDS[marker_id]
                    corner_positions[label] = (center_x, center_y)

            # Update calibration if corners present
            if corner_positions:
                self.calibrator.update_from_corners(corner_positions, w, h)

            for i, marker_id in enumerate(ids.flatten()):
                if marker_id in CORNER_IDS:
                    continue

                c = corners_list[i][0]
                center_x = float(np.mean(c[:, 0]))
                center_y = float(np.mean(c[:, 1]))
                angle = compute_marker_angle(c)
                col, row = self.calibrator.image_to_grid(center_x, center_y)
                col, row = self._smooth_position(marker_id, col, row)

                if marker_id in MARKER_MAP:
                    player_str, role = MARKER_MAP[marker_id]
                    marker_data[marker_id] = {
                        "id": int(marker_id),
                        "player": int(player_str[1]),
                        "role": role,
                        "col": col,
                        "row": row,
                        "angle": angle,
                        "center_x": center_x,
                        "center_y": center_y,
                    }
                elif marker_id in TERRAIN_MAP:
                    owner, terrain_type = TERRAIN_MAP[marker_id]
                    marker_data[marker_id] = {
                        "id": int(marker_id),
                        "role": "terrain",
                        "terrain_type": terrain_type,
                        "owner": owner,
                        "col": col,
                        "row": row,
                        "angle": angle,
                    }
                elif marker_id in SIDE_IDS:
                    marker_data[marker_id] = {
                        "id": int(marker_id),
                        "role": "side_selection",
                        "side": SIDE_IDS[marker_id],
                    }
                elif marker_id in CONTROL_IDS:
                    marker_data[marker_id] = {
                        "id": int(marker_id),
                        "role": "control",
                        "action": CONTROL_IDS[marker_id],
                    }

        return {
            "frame": frame,
            "markers": marker_data,
            "frame_size": (w, h),
            "raw_corners": corners_list if ids is not None else [],
            "raw_ids": ids.flatten().tolist() if ids is not None else [],
            "corner_positions": corner_positions,
        }

    def draw_debug(self, frame_data: dict) -> np.ndarray:
        """Draw detected markers and grid overlay on frame."""
        frame = frame_data["frame"].copy()
        w, h = frame_data["frame_size"]
        gs = self.grid_size

        # Role display names
        ROLE_NAMES = {
            "attack_a": "ATK-A", "attack_b": "ATK-B", "defense": "DEF",
        }
        SIDE_COLORS = {
            1: (80, 180, 255),   # P1 — gold-ish in BGR
            2: (80, 220, 120),   # P2 — green
        }

        # Grid lines (subtle)
        for i in range(gs + 1):
            x = int(i * w / gs)
            y = int(i * h / gs)
            cv2.line(frame, (x, 0), (x, h), (60, 60, 60), 1)
            cv2.line(frame, (0, y), (w, y), (60, 60, 60), 1)

        # Diagonal territory line
        cv2.line(frame, (0, 0), (w, h), (0, 200, 255), 2)

        # Calibration status overlay
        cal_ok = self.calibrator.homography is not None
        cal_color = (0, 220, 0) if cal_ok else (0, 60, 220)
        cal_text = "CALIBRATED" if cal_ok else "NO CALIBRATION — place corner markers 6-9"
        cv2.putText(frame, cal_text, (10, 22), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, cal_color, 2)

        # Draw corner markers
        for label, (cx, cy) in frame_data.get("corner_positions", {}).items():
            cv2.circle(frame, (int(cx), int(cy)), 10, (0, 255, 255), 2)
            cv2.putText(frame, label, (int(cx) + 12, int(cy) + 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        # Draw calibrated board border using corner marker positions
        corner_pos = frame_data.get("corner_positions", {})
        if all(k in corner_pos for k in ["TL", "TR", "BR", "BL"]):
            pts = np.array([
                corner_pos["TL"], corner_pos["TR"],
                corner_pos["BR"], corner_pos["BL"],
            ], dtype=np.int32)
            cv2.polylines(frame, [pts], True, (0, 255, 255), 3)
            # Filled semi-transparent tint inside calibrated area
            overlay = frame.copy()
            cv2.fillPoly(overlay, [pts], (0, 255, 255))
            cv2.addWeighted(overlay, 0.06, frame, 0.94, 0, frame)

        # Draw raw ArUco outlines for ALL detected markers
        raw_corners = frame_data.get("raw_corners", [])
        raw_ids = frame_data.get("raw_ids", [])
        for i, mid in enumerate(raw_ids):
            c = raw_corners[i][0].astype(int)
            if mid in CORNER_IDS:
                color = (0, 255, 255)   # cyan for corners
            elif mid in MARKER_MAP:
                pid = int(MARKER_MAP[mid][0][1])
                color = SIDE_COLORS.get(pid, (200, 200, 200))
            elif mid in TERRAIN_MAP:
                color = (180, 100, 255) if TERRAIN_MAP[mid][1] == "hard" else (255, 180, 60)
            elif mid in SIDE_IDS:
                color = (255, 255, 255)
            elif mid in CONTROL_IDS:
                color = (0, 60, 255)    # red for resolve
            else:
                color = (120, 120, 120)
            cv2.polylines(frame, [c], True, color, 2)

        # Draw rich labels for known markers
        for mid, data in frame_data["markers"].items():
            role = data.get("role")

            if role == "side_selection":
                side = data.get("side", "?")
                cv2.putText(frame, f"SIDE: {side.upper()}", (10, h - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                continue
            if role == "control":
                action = data.get("action", "?")
                cv2.putText(frame, f">>> {action.upper()} <<<", (10, h - 44),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 60, 255), 2)
                continue

            cx = int(data["center_x"])
            cy = int(data["center_y"])

            if role in ("attack_a", "attack_b", "defense"):
                pid = data["player"]
                color = SIDE_COLORS.get(pid, (200, 200, 200))
                role_label = ROLE_NAMES.get(role, role)
                angle = data.get("angle", 0)

                # Direction from angle
                if angle < 22.5 or angle >= 157.5:
                    dir_label = "HORIZ"
                elif angle < 67.5:
                    dir_label = "DIAG"
                else:
                    dir_label = "VERT"

                # Direction arrow
                arrow_len = 28
                rad = math.radians(angle)
                ax = int(cx + arrow_len * math.cos(rad))
                ay = int(cy + arrow_len * math.sin(rad))
                cv2.arrowedLine(frame, (cx, cy), (ax, ay), color, 2, tipLength=0.4)

                line1 = f"P{pid} {role_label}"
                line2 = f"({data['col']},{data['row']}) {dir_label}"
                cv2.putText(frame, line1, (cx + 12, cy - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
                cv2.putText(frame, line2, (cx + 12, cy + 12),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

            elif role == "terrain":
                ttype = data.get("terrain_type", "soft")
                owner = data.get("owner", "?")
                color = (180, 100, 255) if ttype == "hard" else (255, 180, 60)
                label = f"{owner.upper()} {ttype.upper()}"
                sub = f"({data['col']},{data['row']})"
                cv2.putText(frame, label, (cx + 12, cy - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1)
                cv2.putText(frame, sub, (cx + 12, cy + 12),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1)

        return frame

    def release(self):
        self.cap.release()
