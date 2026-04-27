"""
Camera-side ArUco tracker.

- Detects 4 corner markers (IDs 0-3), 6 token markers, 1 turn marker
- Maps pixel positions → 12×12 grid cells using homography
- Caches last-known token state so brief marker loss doesn't flicker

Marker ID table:
  0-3  : board corners (TL/TR/BL/BR)
  10-12: P1 tokens (atk_a / atk_b / def)
  13   : turn marker   (0° = P1, 180° = P2)
  14-16: P2 tokens (atk_a / atk_b / def)
"""

import time
import cv2
import numpy as np

GRID_COLS = 12
GRID_ROWS = 12
PADDING   = 1 / 14   # 14×14 outer, 12×12 playable inner
ARUCO_DICT_ID = cv2.aruco.DICT_4X4_50
CACHE_TTL_SEC = 1.0

CORNER_IDS     = {0: "TL", 1: "TR", 2: "BL", 3: "BR"}
TURN_MARKER_ID = 13
HELP_MARKER_ID = 17   # tutorial summon marker — present = show, rotate = page flip
P1_TOKENS      = {10: "atk_a", 11: "atk_b", 12: "def"}
P2_TOKENS      = {14: "atk_a", 15: "atk_b", 16: "def"}


def help_page_from_angle(angle: float | None) -> int | None:
    """0–90 → 1, 90–180 → 2, 180–270 → 3, 270–360 → 4. None if no help marker."""
    if angle is None:
        return None
    return int((angle % 360) // 90) + 1

COMPASS_8 = [
    (  0, "E"),  ( 45, "SE"), ( 90, "S"),  (135, "SW"),
    (180, "W"),  (225, "NW"), (270, "N"),  (315, "NE"),
]


def snap_direction_8(angle: float) -> str:
    return min(COMPASS_8, key=lambda d: abs((angle - d[0] + 180) % 360 - 180))[1]


def turn_from_angle(angle: float):
    if angle is None: return None
    if abs((angle -   0 + 180) % 360 - 180) <= 60: return 1
    if abs((angle - 180 + 180) % 360 - 180) <= 60: return 2
    return None


# ─── ArUco helpers ────────────────────────────────────────────────────────────

def build_detector():
    d = cv2.aruco.getPredefinedDictionary(int(ARUCO_DICT_ID))
    p = cv2.aruco.DetectorParameters()
    if hasattr(cv2.aruco, "ArucoDetector"):
        return cv2.aruco.ArucoDetector(d, p), d, p, "modern"
    return None, d, p, "legacy"


def _center(corners):
    pts = corners[0]
    return float(np.mean(pts[:, 0])), float(np.mean(pts[:, 1]))


def _angle(corners):
    tl, tr = corners[0][0], corners[0][1]
    return float(np.degrees(np.arctan2(tr[1] - tl[1], tr[0] - tl[0])) % 360)


# ─── Homography ───────────────────────────────────────────────────────────────

def compute_homography(cc):
    if not all(k in cc for k in ["TL", "TR", "BL", "BR"]):
        return None
    src = np.array([list(cc["TL"]), list(cc["TR"]),
                    list(cc["BL"]), list(cc["BR"])], dtype=np.float32)
    dst = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=np.float32)
    H, _ = cv2.findHomography(src, dst)
    return H


def to_grid_cell(H, point):
    pt = np.array([[point]], dtype=np.float32).reshape(-1, 1, 2)
    nx, ny = cv2.perspectiveTransform(pt, H)[0][0]
    nx = (nx - PADDING) / (1 - 2 * PADDING)
    ny = (ny - PADDING) / (1 - 2 * PADDING)
    col = int(np.clip(nx * GRID_COLS, 0, GRID_COLS - 1))
    row = int(np.clip(ny * GRID_ROWS, 0, GRID_ROWS - 1))
    return col, row


# ─── Frame detection ──────────────────────────────────────────────────────────

def detect_frame(frame, detector, aruco_dict, params, api_mode):
    """Returns (corner_centers, p1_raw, p2_raw, turn_angle, help_angle)."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if api_mode == "modern":
        corners, ids, _ = detector.detectMarkers(gray)
    else:
        corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=params)

    cc, p1, p2, turn_angle, help_angle = {}, {}, {}, None, None
    if ids is None:
        return cc, p1, p2, turn_angle, help_angle

    for i, mid in enumerate(ids.flatten()):
        mid = int(mid)
        centre = _center(corners[i])
        angle  = _angle(corners[i])

        if mid in CORNER_IDS:
            cc[CORNER_IDS[mid]] = centre
        elif mid in P1_TOKENS:
            p1[P1_TOKENS[mid]] = {"angle": round(angle, 1), "center": centre,
                                  "direction": snap_direction_8(angle)}
        elif mid in P2_TOKENS:
            p2[P2_TOKENS[mid]] = {"angle": round(angle, 1), "center": centre,
                                  "direction": snap_direction_8(angle)}
        elif mid == TURN_MARKER_ID:
            turn_angle = angle
        elif mid == HELP_MARKER_ID:
            help_angle = angle

    return cc, p1, p2, turn_angle, help_angle


# ─── Token cache (survives brief marker loss) ─────────────────────────────────

class TokenCache:
    def __init__(self, ttl: float = CACHE_TTL_SEC):
        self.ttl   = ttl
        self.store = {}

    def _update(self, player, role, resolved):
        self.store[(player, role)] = (resolved, time.time())

    def _get(self, player, role):
        entry = self.store.get((player, role))
        if entry is None: return None
        resolved, ts = entry
        if time.time() - ts > self.ttl: return None
        return resolved

    def resolve_side(self, player, live_tokens, H) -> dict:
        out = {}
        for role in ("atk_a", "atk_b", "def"):
            info = live_tokens.get(role)
            if info is not None and H is not None:
                col, row = to_grid_cell(H, info["center"])
                resolved = {"col": col, "row": row, "angle": info["angle"],
                            "direction": info["direction"], "stale": False}
                self._update(player, role, resolved)
                out[role] = resolved
            else:
                cached = self._get(player, role)
                out[role] = ({**cached, "stale": True} if cached
                             else {"col": None, "row": None, "angle": None,
                                   "direction": None, "stale": True})
        return out
