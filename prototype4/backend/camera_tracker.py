"""
ArUco marker detection and board calibration — self-contained.

Incorporates the improved calibration logic from Defend-Your-Pixels/python_tracker:
  - Inward-offset corner calculation (accounts for physical marker size)
  - Homography maps pixels directly to grid coordinates (0–11)
  - Fallback: retains last valid homography when corner markers drop out
  - Grid overlay drawn in camera perspective (inverted homography)

Marker ID assignment:
  0  = P1 Attack A          6  = Corner TL (calibration)
  1  = P1 Attack B          7  = Corner TR
  2  = P1 Defense           8  = Corner BR
  3  = P2 Attack A          9  = Corner BL
  4  = P2 Attack B
  5  = P2 Defense
  10 = P1 Hard terrain A    20 = Side selection: Farmer
  11 = P1 Hard terrain B    21 = Side selection: Emu
  12 = P1 Soft terrain      22 = Resolve attack
  13 = P2 Hard terrain A    23 = Cube: Player 1 face
  14 = P2 Hard terrain B    24 = Cube: Player 2 face
  15 = P2 Soft terrain      25 = P1 HQ marker
                            26 = P2 HQ marker
"""

import math
import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple

# ── Constants ─────────────────────────────────────────────────────────────────
GRID_SIZE = 12
GRID_MIN  = -0.5
GRID_MAX  = GRID_SIZE - 0.5   # 11.5

# ── Marker ID maps ────────────────────────────────────────────────────────────
MARKER_MAP = {
    0: ("p1", "attack_a"), 1: ("p1", "attack_b"), 2: ("p1", "defense"),
    3: ("p2", "attack_a"), 4: ("p2", "attack_b"), 5: ("p2", "defense"),
}
TERRAIN_MAP = {
    10: ("p1", "hard"), 11: ("p1", "hard"), 12: ("p1", "soft"),
    13: ("p2", "hard"), 14: ("p2", "hard"), 15: ("p2", "soft"),
}
# Our corner IDs and their board positions
# Mapped to internal keys 0-3 for homography: 0=TL,1=TR,2=BL,3=BR
CORNER_IDS   = {6: "TL", 7: "TR", 8: "BR", 9: "BL"}
CORNER_REMAP = {6: 0, 7: 1, 9: 2, 8: 3}   # our ID → internal key

SIDE_IDS     = {20: "farmer", 21: "emu"}
CONTROL_IDS  = {22: "resolve"}
TURN_IDS     = {23: 1, 24: 2}
HQ_IDS       = {25: 1, 26: 2}


# ── Calibration helpers (ported from python_tracker) ─────────────────────────

def _marker_size_px(corners4: np.ndarray) -> float:
    """Average edge length of a detected marker in pixels."""
    edges = []
    for i in range(4):
        p1, p2 = corners4[i], corners4[(i + 1) % 4]
        edges.append(float(np.linalg.norm(p2 - p1)))
    return sum(edges) / len(edges)


def _unit_vec(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else np.zeros(2, dtype=np.float32)


def _build_playable_corners(corners_px: dict) -> Optional[np.ndarray]:
    """
    Push each corner center inward by half a marker size along the two board
    edges meeting at that corner — gives the true playable area boundary.
    corners_px keys: 0=TL, 1=TR, 2=BL, 3=BR
    """
    if not all(k in corners_px for k in [0, 1, 2, 3]):
        return None

    def center(k):
        return np.asarray(corners_px[k]["center"], dtype=np.float32)

    def half(k):
        return corners_px[k]["size_px"] / 2.0

    c = {k: center(k) for k in range(4)}
    h = {k: half(k)   for k in range(4)}

    playable = np.float32([
        c[0] + _unit_vec(c[1] - c[0]) * h[0] + _unit_vec(c[2] - c[0]) * h[0],  # TL
        c[1] + _unit_vec(c[0] - c[1]) * h[1] + _unit_vec(c[3] - c[1]) * h[1],  # TR
        c[2] + _unit_vec(c[3] - c[2]) * h[2] + _unit_vec(c[0] - c[2]) * h[2],  # BL
        c[3] + _unit_vec(c[2] - c[3]) * h[3] + _unit_vec(c[1] - c[3]) * h[3],  # BR
    ])
    return playable


def _build_homography(corners_px: dict) -> Optional[np.ndarray]:
    """Compute homography: camera pixels → grid coordinates (0–11)."""
    src = _build_playable_corners(corners_px)
    if src is None:
        return None
    dst = np.float32([
        [GRID_MIN, GRID_MIN],   # TL
        [GRID_MAX, GRID_MIN],   # TR
        [GRID_MIN, GRID_MAX],   # BL
        [GRID_MAX, GRID_MAX],   # BR
    ])
    H, _ = cv2.findHomography(src, dst)
    return H


def _pixel_to_grid(px: float, py: float, H: np.ndarray) -> Tuple[Optional[float], Optional[float]]:
    if H is None:
        return None, None
    try:
        pt     = np.float32([[[px, py]]])
        warped = cv2.perspectiveTransform(pt, H)[0][0]
        gx     = float(np.clip(warped[0], 0, GRID_SIZE - 1))
        gy     = float(np.clip(warped[1], 0, GRID_SIZE - 1))
        if not (math.isfinite(gx) and math.isfinite(gy)):
            return None, None
        return gx, gy
    except Exception:
        return None, None


def _compute_rotation(corners4: np.ndarray) -> float:
    """0-360° rotation from marker corner orientation."""
    tl, tr = corners4[0], corners4[1]
    dx = float(tr[0] - tl[0])
    dy = float(tr[1] - tl[1])
    return (math.degrees(math.atan2(dy, dx)) + 360) % 360


def _rotation_to_angle(rot360: float) -> float:
    """Convert 0-360° to 0-180° for angle_to_direction()."""
    return rot360 % 180


# ── Debug draw helpers ────────────────────────────────────────────────────────

def _draw_grid_overlay(frame: np.ndarray, H: np.ndarray):
    """Draw the 12×12 grid in camera perspective by inverting the homography."""
    try:
        H_inv = np.linalg.inv(H)
        if not np.all(np.isfinite(H_inv)):
            return
        fh, fw = frame.shape[:2]
        MAX_COORD = max(fw, fh) * 4  # anything beyond this is off-screen garbage

        def safe_pt(raw) -> Optional[Tuple[int, int]]:
            x, y = float(raw[0]), float(raw[1])
            if not (math.isfinite(x) and math.isfinite(y)):
                return None
            if abs(x) > MAX_COORD or abs(y) > MAX_COORD:
                return None
            return (int(x), int(y))

        for col in range(GRID_SIZE + 1):
            gx  = col - 0.5
            pts = np.float32([[[gx, GRID_MIN]], [[gx, GRID_MAX]]])
            src = cv2.perspectiveTransform(pts, H_inv)
            p1  = safe_pt(src[0][0])
            p2  = safe_pt(src[1][0])
            if p1 and p2:
                cv2.line(frame, p1, p2, (60, 60, 100), 1)

        for row in range(GRID_SIZE + 1):
            gy  = row - 0.5
            pts = np.float32([[[GRID_MIN, gy]], [[GRID_MAX, gy]]])
            src = cv2.perspectiveTransform(pts, H_inv)
            p1  = safe_pt(src[0][0])
            p2  = safe_pt(src[1][0])
            if p1 and p2:
                cv2.line(frame, p1, p2, (60, 60, 100), 1)
    except Exception:
        pass


# ── Main tracker class ────────────────────────────────────────────────────────

class MarkerTracker:
    def __init__(self, camera_index: int = 0, grid_size: int = 12):
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT,  720)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)   # don't let old frames pile up

        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        params     = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(aruco_dict, params)

        # Calibration state
        self._H: Optional[np.ndarray] = None          # current homography
        self._playable: Optional[np.ndarray] = None   # 4 playable corner pixels

        # Smoothing: rolling average of last N positions per marker
        self._history: Dict[int, List[Tuple[int, int]]] = {}
        self._HISTORY_LEN = 5

    def _smooth(self, mid: int, col: int, row: int) -> Tuple[int, int]:
        hist = self._history.setdefault(mid, [])
        hist.append((col, row))
        if len(hist) > self._HISTORY_LEN:
            hist.pop(0)
        return (
            int(round(sum(p[0] for p in hist) / len(hist))),
            int(round(sum(p[1] for p in hist) / len(hist))),
        )

    def read_frame(self) -> Optional[dict]:
        ret, frame = self.cap.read()
        if not ret:
            return None

        h_px, w_px = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners_list, ids, _ = self.detector.detectMarkers(gray)

        marker_data: Dict[int, dict]     = {}
        corners_px:  Dict[int, dict]     = {}   # internal 0-3 keyed
        our_corners: Dict[str, Tuple]    = {}   # label → pixel center

        if ids is not None:
            # ── Pass 1: collect corner markers for calibration ────────────
            for i, mid in enumerate(ids.flatten()):
                if mid not in CORNER_IDS:
                    continue
                c4     = corners_list[i][0]
                center = c4.mean(axis=0)
                key    = CORNER_REMAP[mid]
                corners_px[key] = {
                    "center":  center,
                    "size_px": _marker_size_px(c4),
                }
                our_corners[CORNER_IDS[mid]] = (float(center[0]), float(center[1]))

            # Update homography when all 4 corners visible
            if len(corners_px) == 4:
                H_new = _build_homography(corners_px)
                if H_new is not None:
                    self._H       = H_new
                    self._playable = _build_playable_corners(corners_px)

            # ── Pass 2: process all other markers ─────────────────────────
            for i, mid in enumerate(ids.flatten()):
                if mid in CORNER_IDS:
                    continue

                c4  = corners_list[i][0]
                cx  = float(np.mean(c4[:, 0]))
                cy  = float(np.mean(c4[:, 1]))
                rot = _compute_rotation(c4)
                ang = _rotation_to_angle(rot)

                # Grid position
                gx, gy = _pixel_to_grid(cx, cy, self._H)
                if gx is None:
                    # Fallback: linear mapping
                    gx = cx / w_px * GRID_SIZE
                    gy = cy / h_px * GRID_SIZE
                col = int(np.clip(round(gx), 0, GRID_SIZE - 1))
                row = int(np.clip(round(gy), 0, GRID_SIZE - 1))
                col, row = self._smooth(mid, col, row)

                if mid in MARKER_MAP:
                    ps, role = MARKER_MAP[mid]
                    marker_data[mid] = {
                        "id": int(mid), "player": int(ps[1]), "role": role,
                        "col": col, "row": row, "angle": ang,
                        "center_x": cx, "center_y": cy,
                    }
                elif mid in TERRAIN_MAP:
                    owner, ttype = TERRAIN_MAP[mid]
                    marker_data[mid] = {
                        "id": int(mid), "role": "terrain",
                        "terrain_type": ttype, "owner": owner,
                        "col": col, "row": row, "angle": ang,
                        "center_x": cx, "center_y": cy,
                    }
                elif mid in SIDE_IDS:
                    marker_data[mid] = {"id": int(mid), "role": "side_selection",
                                        "side": SIDE_IDS[mid]}
                elif mid in CONTROL_IDS:
                    marker_data[mid] = {"id": int(mid), "role": "control",
                                        "action": CONTROL_IDS[mid]}
                elif mid in TURN_IDS:
                    marker_data[mid] = {"id": int(mid), "role": "turn_cube",
                                        "player": TURN_IDS[mid]}
                elif mid in HQ_IDS:
                    marker_data[mid] = {"id": int(mid), "role": "hq",
                                        "player": HQ_IDS[mid],
                                        "col": col, "row": row}

        return {
            "frame":            frame,
            "markers":          marker_data,
            "frame_size":       (w_px, h_px),
            "raw_corners":      corners_list if ids is not None else [],
            "raw_ids":          ids.flatten().tolist() if ids is not None else [],
            "corner_positions": our_corners,
            "calibrated":       self._H is not None,
            "playable":         self._playable,
            "homography":       self._H,
        }

    # ── Debug window ──────────────────────────────────────────────────────────

    def draw_debug(self, frame_data: dict) -> np.ndarray:
        frame = frame_data["frame"].copy()
        H     = frame_data.get("homography")
        cal   = frame_data.get("calibrated", False)
        h_px  = frame.shape[0]

        # Grid drawn in camera perspective
        if H is not None:
            _draw_grid_overlay(frame, H)

        # Playable area border
        playable = frame_data.get("playable")
        if playable is not None and len(playable) == 4:
            pts = playable.astype(np.int32).reshape(-1, 1, 2)
            cv2.polylines(frame, [pts], True, (0, 255, 255), 3)

        # Calibration status
        cal_color = (0, 220, 0) if cal else (0, 60, 220)
        cal_text  = "CALIBRATED" if cal else "NO CALIBRATION — place corner markers 6-9"
        cv2.putText(frame, cal_text, (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, cal_color, 2)

        # Corner labels
        for label, (cx, cy) in frame_data.get("corner_positions", {}).items():
            if math.isfinite(cx) and math.isfinite(cy):
                cv2.circle(frame, (int(cx), int(cy)), 8, (0, 255, 255), 2)
                cv2.putText(frame, label, (int(cx) + 10, int(cy) + 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

        # Marker outlines (color-coded by type)
        COLORS = {
            "corner": (0, 255, 255), "p1": (80, 180, 255), "p2": (80, 220, 120),
            "hard": (180, 100, 255), "soft": (255, 180, 60),
            "side": (255, 255, 255), "control": (0, 60, 255),
            "turn": (200, 200, 60),  "hq": (255, 60, 200), "unk": (100, 100, 100),
        }
        for i, mid in enumerate(frame_data.get("raw_ids", [])):
            c4    = frame_data["raw_corners"][i][0].astype(int)
            shape = c4.reshape(-1, 1, 2)
            if mid in CORNER_IDS:
                color = COLORS["corner"]
            elif mid in MARKER_MAP:
                color = COLORS[f"p{MARKER_MAP[mid][0][1]}"]
            elif mid in TERRAIN_MAP:
                color = COLORS[TERRAIN_MAP[mid][1]]
            elif mid in SIDE_IDS:   color = COLORS["side"]
            elif mid in CONTROL_IDS:color = COLORS["control"]
            elif mid in TURN_IDS:   color = COLORS["turn"]
            elif mid in HQ_IDS:     color = COLORS["hq"]
            else:                   color = COLORS["unk"]
            cv2.polylines(frame, [shape], True, color, 2)

        # Rich labels for tracked markers
        for mid, data in frame_data["markers"].items():
            role = data.get("role")

            # Bottom-of-screen overlays for non-board markers
            if role == "side_selection":
                cv2.putText(frame, f"SIDE: {data['side'].upper()}",
                            (10, h_px - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
                continue
            if role == "control":
                cv2.putText(frame, f">>> {data['action'].upper()} <<<",
                            (10, h_px - 44), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 60, 255), 2)
                continue
            if role == "turn_cube":
                cv2.putText(frame, f"TURN: P{data['player']}",
                            (10, h_px - 68), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 60), 2)
                continue
            if role == "hq":
                cv2.putText(frame, f"HQ P{data['player']}: ({data['col']},{data['row']})",
                            (10, h_px - 92), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 60, 200), 2)
                continue

            if "center_x" not in data:
                continue
            cx, cy = int(data["center_x"]), int(data["center_y"])
            ang    = data.get("angle", 0)

            if role in ("attack_a", "attack_b", "defense"):
                pid   = data["player"]
                color = COLORS[f"p{pid}"]
                short = {"attack_a": "ATK-A", "attack_b": "ATK-B", "defense": "DEF"}[role]
                dlbl  = "HORIZ" if ang < 22.5 or ang >= 157.5 else ("DIAG" if ang < 67.5 else "VERT")
                cv2.putText(frame, f"P{pid} {short}",
                            (cx + 10, cy - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1)
                cv2.putText(frame, f"({data['col']},{data['row']}) {dlbl}",
                            (cx + 10, cy + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1)
                rad = math.radians(ang)
                cv2.arrowedLine(frame, (cx, cy),
                                (int(cx + 28 * math.cos(rad)), int(cy + 28 * math.sin(rad))),
                                color, 2, tipLength=0.4)

            elif role == "terrain":
                color = COLORS[data["terrain_type"]]
                cv2.putText(frame, f"{data['owner'].upper()} {data['terrain_type'].upper()}",
                            (cx + 10, cy - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                cv2.putText(frame, f"({data['col']},{data['row']})",
                            (cx + 10, cy + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.36, color, 1)

        return frame

    def release(self):
        self.cap.release()
