"""
Camera-side ArUco tracker (macOS webcam friendly).

Marker IDs (from generate_markers.py):
  0-3  : board corners (TL / TR / BL / BR)
  4    : shared CONFIRM marker (locks active HQ)
  10   : P1 TURN marker
  11   : P1 HQ placement marker
  12   : P1 ATK_A
  13   : P1 ATK_B
  14   : P1 DEF
  20   : P2 TURN marker
  21   : P2 HQ placement marker
  22   : P2 ATK_A
  23   : P2 ATK_B
  24   : P2 DEF

Returns 8-direction compass labels (E/SE/S/SW/W/NW/N/NE).
"""

import time
import cv2
import numpy as np

GRID_COLS = 12
GRID_ROWS = 12
PADDING   = 1 / 14   # 14×14 outer, 12×12 playable inner
ARUCO_DICT_ID = cv2.aruco.DICT_4X4_50
CACHE_TTL_SEC = 2.5  # seconds to keep last-known position when marker is briefly hidden

CORNER_IDS      = {0: "TL", 1: "TR", 2: "BL", 3: "BR"}
CONFIRM_ID      = 4    # shared marker that locks the active HQ
P1_TURN_ID      = 10   # P1 turn marker
P1_HQ_ID        = 11   # P1 HQ placement marker
P2_TURN_ID      = 20   # P2 turn marker
P2_HQ_ID        = 21   # P2 HQ placement marker

# Gameplay tokens: maps marker ID → role key used in the state object
P1_TOKENS       = {12: "atk_a", 13: "atk_b", 14: "def"}
P2_TOKENS       = {22: "atk_a", 23: "atk_b", 24: "def"}

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
    """Returns (corner_centers, p1_raw, p2_raw, turn_angle, hq_raw, raw)
    where `raw` = {"corners": ..., "ids": ...} for optional preview overlay.
    `hq_raw` = {"p1": {"center": (px, py)}, "p2": {...}} for detected HQ markers.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if api_mode == "modern":
        corners, ids, _ = detector.detectMarkers(gray)
    else:
        corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=params)

    cc, p1, p2, turn_angle, hq_raw = {}, {}, {}, None, {}
    raw = {"corners": corners, "ids": ids}
    if ids is None:
        return cc, p1, p2, turn_angle, hq_raw, raw

    for i, mid in enumerate(ids.flatten()):
        mid = int(mid)
        centre = _center(corners[i])
        angle  = _angle(corners[i])

        if mid in CORNER_IDS:
            cc[CORNER_IDS[mid]] = centre
        elif mid in P1_TOKENS:
            # Gameplay token: record position + direction
            p1[P1_TOKENS[mid]] = {"angle": round(angle, 1), "center": centre,
                                  "direction": snap_direction_8(angle)}
        elif mid in P2_TOKENS:
            p2[P2_TOKENS[mid]] = {"angle": round(angle, 1), "center": centre,
                                  "direction": snap_direction_8(angle)}
        elif mid in (P1_TURN_ID, P2_TURN_ID):
            # Turn markers — record angle so server can tell which side is acting
            turn_angle = angle
        elif mid == P1_HQ_ID:
            # P1 HQ placement marker — record pixel centre for homography later
            hq_raw["p1"] = {"center": centre}
        elif mid == P2_HQ_ID:
            # P2 HQ placement marker
            hq_raw["p2"] = {"center": centre}
        # CONFIRM_ID (4) is intentionally ignored in this simplified server

    return cc, p1, p2, turn_angle, hq_raw, raw


# ─── Preview overlay ──────────────────────────────────────────────────────────

# Friendly label for each known marker ID (shown in the camera preview window)
MARKER_LABELS = {
    0: "TL",   1: "TR",   2: "BL",   3: "BR",
    4:  "CONFIRM",
    10: "P1.TURN",  11: "P1.HQ",
    12: "P1.atk_a", 13: "P1.atk_b", 14: "P1.def",
    20: "P2.TURN",  21: "P2.HQ",
    22: "P2.atk_a", 23: "P2.atk_b", 24: "P2.def",
}


def annotate_frame(frame, raw):
    """Draw bounding boxes + friendly labels for each detected marker."""
    if raw is None or raw.get("ids") is None:
        return
    corners = raw["corners"]
    ids = raw["ids"].flatten()
    for i, mid in enumerate(ids):
        mid = int(mid)
        pts = corners[i][0].astype(int)
        # Box outline
        for j in range(4):
            cv2.line(frame, tuple(pts[j]), tuple(pts[(j + 1) % 4]),
                     (0, 255, 0), 2)
        # Centre dot
        cx = int(pts[:, 0].mean())
        cy = int(pts[:, 1].mean())
        cv2.circle(frame, (cx, cy), 3, (0, 255, 255), -1)
        # Label (ID + role)
        label = MARKER_LABELS.get(mid, f"id={mid}")
        cv2.putText(frame, f"{mid} {label}", (cx + 8, cy - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)


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


# ─── HQ marker cache ──────────────────────────────────────────────────────────

class HqCache:
    """Remembers last-seen HQ marker positions with the same TTL as TokenCache."""

    def __init__(self, ttl: float = CACHE_TTL_SEC):
        self.ttl   = ttl
        self.store = {}   # side → (col, row, timestamp)

    def resolve(self, side: str, hq_raw: dict, H) -> dict:
        """Return {"col", "row", "stale"} for `side` ("p1" or "p2")."""
        info = hq_raw.get(side)
        if info is not None and H is not None:
            col, row = to_grid_cell(H, info["center"])
            self.store[side] = (col, row, time.time())
            return {"col": col, "row": row, "stale": False}

        entry = self.store.get(side)
        if entry:
            col, row, ts = entry
            if time.time() - ts <= self.ttl:
                return {"col": col, "row": row, "stale": True}

        return {"col": None, "row": None, "stale": True}
