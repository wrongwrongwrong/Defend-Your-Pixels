"""
PixelWar Tracker — server.py

What this does:
  1. Opens the camera (webcam or phone via DroidCam)
  2. Detects ArUco markers on every frame
  3. Uses the 4 corner markers to map camera pixels → 12×12 grid positions
     (accounts for the 14×14 outer border so tokens don't overlap corner markers)
  4. Reads each token marker's rotation → direction (HORIZONTAL / VERTICAL / DIAGONAL)
  5. Reads the turn marker's rotation → whose turn it is (P1 or P2)
  6. Broadcasts the full game state to the Phaser frontend via WebSocket

Marker ID assignment:
  0–3   : board corner markers (top-left, top-right, bottom-left, bottom-right)
  10    : P1 ATK-A
  11    : P1 ATK-B
  12    : P1 DEF
  14    : P2 ATK-A
  15    : P2 ATK-B
  16    : P2 DEF
  20    : turn marker  (0° = P1's turn,  180° = P2's turn)
"""

import cv2
import numpy as np
import asyncio
import json
import websockets

# ── Configuration ─────────────────────────────────────────────────────────────

USE_WEBCAM   = True          # set False to use phone camera instead
WEBCAM_INDEX = 0
PHONE_IP     = "172.16.11.211"
PHONE_PORT   = 4747

WS_HOST = "localhost"
WS_PORT = 8765

# The physical board is printed as 14×14, but the playable area is 12×12.
# PADDING pushes the grid boundary inward so the outer marker strip is ignored.
GRID_COLS = 12
GRID_ROWS = 12
PADDING   = 1 / 14   # one cell's worth of space on each side

ARUCO_DICT_ID = cv2.aruco.DICT_4X4_50
TOLERANCE     = 35   # degrees — how much rotation error is allowed

# Which marker ID maps to which board corner
CORNER_IDS = {0: "TL", 1: "TR", 2: "BL", 3: "BR"}

# Token role by marker ID
P1_TOKENS = {10: "atk_a", 11: "atk_b", 12: "def"}   # 13 is used as turn marker
P2_TOKENS = {14: "atk_a", 15: "atk_b", 16: "def"}

TURN_MARKER_ID = 13

# Rotation angles → direction label (used for ATK tokens)
DIRECTIONS = [
    (  0, "HORIZONTAL"),
    ( 90, "VERTICAL"),
    (180, "DIAGONAL"),
]


# ── Camera ────────────────────────────────────────────────────────────────────

def open_camera():
    source = WEBCAM_INDEX if USE_WEBCAM else f"http://{PHONE_IP}:{PHONE_PORT}/video"
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open camera: {source}")
        return None
    print(f"[OK] Camera opened: {source}")
    return cap


# ── ArUco helpers ─────────────────────────────────────────────────────────────

def build_detector():
    d = cv2.aruco.getPredefinedDictionary(int(ARUCO_DICT_ID))
    p = cv2.aruco.DetectorParameters()
    if hasattr(cv2.aruco, "ArucoDetector"):
        return cv2.aruco.ArucoDetector(d, p), d, p, "modern"
    return None, d, p, "legacy"


def get_center(corners):
    """Average the 4 corners to find the marker's center point."""
    pts = corners[0]
    return float(np.mean(pts[:, 0])), float(np.mean(pts[:, 1]))


def get_angle(corners):
    """
    Compute rotation angle (0–360°) from the top edge of the marker.
    Top-left → top-right vector angle, measured from the positive X axis.
    """
    tl = corners[0][0]
    tr = corners[0][1]
    dx, dy = tr[0] - tl[0], tr[1] - tl[1]
    return float(np.degrees(np.arctan2(dy, dx)) % 360)


def snap_direction(angle):
    """Map a rotation angle to the nearest direction label, or None if too far off."""
    for target, label in DIRECTIONS:
        diff = abs((angle - target + 180) % 360 - 180)
        if diff <= TOLERANCE:
            return label
    return None


def get_turn_from_angle(angle):
    """
    Read the turn marker's rotation:
      ~0°   → P1's turn
      ~180° → P2's turn
    """
    if abs((angle - 0   + 180) % 360 - 180) <= 60:
        return 1
    if abs((angle - 180 + 180) % 360 - 180) <= 60:
        return 2
    return None


# ── Homography (camera pixels → normalised board coords) ─────────────────────

def compute_homography(corner_centers):
    """
    Build a perspective transform matrix from the 4 detected corner markers.
    Maps their pixel positions to the unit square [0,1] × [0,1].
    Returns None if fewer than 4 corners are visible.
    """
    if not all(k in corner_centers for k in ["TL", "TR", "BL", "BR"]):
        return None
    src = np.float32([
        list(corner_centers["TL"]), list(corner_centers["TR"]),
        list(corner_centers["BL"]), list(corner_centers["BR"]),
    ])
    dst = np.float32([[0, 0], [1, 0], [0, 1], [1, 1]])
    H, _ = cv2.findHomography(src, dst)
    return H


def to_grid_cell(H, point):
    """
    Transform a pixel-space point through the homography and
    then remap from the full 14×14 space down to the 12×12 inner grid.
    """
    pt = np.float32([[point]]).reshape(-1, 1, 2)
    nx, ny = cv2.perspectiveTransform(pt, H)[0][0]

    # Shift and scale so the inner 12×12 area fills the full [0,1] range
    nx = (nx - PADDING) / (1 - 2 * PADDING)
    ny = (ny - PADDING) / (1 - 2 * PADDING)

    col = int(np.clip(nx * GRID_COLS, 0, GRID_COLS - 1))
    row = int(np.clip(ny * GRID_ROWS, 0, GRID_ROWS - 1))
    return col, row


# ── Frame detection ───────────────────────────────────────────────────────────

def detect_frame(frame, detector, aruco_dict, params, api_mode):
    """
    Run ArUco detection on one frame.
    Returns:
      corner_centers  — dict: corner name → (x, y) in pixels
      p1_tokens       — dict: role → {angle, center, direction}
      p2_tokens       — same for P2
      turn_angle      — float or None (from the turn marker)
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    if api_mode == "modern":
        corners, ids, _ = detector.detectMarkers(gray)
    else:
        corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=params)

    corner_centers = {}
    p1_tokens      = {}
    p2_tokens      = {}
    turn_angle     = None

    if ids is None:
        return corner_centers, p1_tokens, p2_tokens, turn_angle

    for i, mid in enumerate(ids.flatten()):
        center = get_center(corners[i])
        angle  = get_angle(corners[i])

        if mid in CORNER_IDS:
            corner_centers[CORNER_IDS[mid]] = center

        elif mid in P1_TOKENS:
            role = P1_TOKENS[mid]
            p1_tokens[role] = {
                "angle":     round(angle, 1),
                "center":    center,
                "direction": snap_direction(angle),
            }

        elif mid in P2_TOKENS:
            role = P2_TOKENS[mid]
            p2_tokens[role] = {
                "angle":     round(angle, 1),
                "center":    center,
                "direction": snap_direction(angle),
            }

        elif mid == TURN_MARKER_ID:
            turn_angle = angle

    return corner_centers, p1_tokens, p2_tokens, turn_angle


# ── WebSocket ─────────────────────────────────────────────────────────────────

connected_clients = set()


async def ws_handler(websocket):
    connected_clients.add(websocket)
    print(f"[WS] Client connected  ({len(connected_clients)} total)")
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.discard(websocket)
        print(f"[WS] Client disconnected ({len(connected_clients)} total)")


async def broadcast(data: dict):
    if not connected_clients:
        return
    msg = json.dumps(data)
    await asyncio.gather(*[c.send(msg) for c in connected_clients])


# ── Main camera loop ──────────────────────────────────────────────────────────

async def camera_loop():
    cap = open_camera()
    if cap is None:
        return

    detector, aruco_dict, params, api_mode = build_detector()
    print(f"[OK] ArUco detector ready ({api_mode} API)")
    print("Press 'q' in the camera window to quit.\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Failed to read frame — check camera.")
            break

        corner_centers, p1_tokens, p2_tokens, turn_angle = detect_frame(
            frame, detector, aruco_dict, params, api_mode
        )
        H = compute_homography(corner_centers)

        # --- Resolve pixel positions → grid cells ---
        def resolve(token_dict):
            out = {}
            for role, info in token_dict.items():
                if H is not None:
                    col, row = to_grid_cell(H, info["center"])
                else:
                    col, row = None, None
                out[role] = {
                    "col":       col,
                    "row":       row,
                    "direction": info["direction"],
                }
            return out

        turn = get_turn_from_angle(turn_angle) if turn_angle is not None else None

        state = {
            "corners_found": len(corner_centers),
            "turn":          turn,
            "p1":            resolve(p1_tokens),
            "p2":            resolve(p2_tokens),
        }
        await broadcast(state)

        # --- Camera overlay ---
        corners_ok = len(corner_centers) == 4
        cv2.putText(frame, f"Corners: {len(corner_centers)}/4",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (0, 255, 0) if corners_ok else (0, 100, 255), 2)

        if turn is not None:
            cv2.putText(frame, f"Turn: P{turn}",
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 220, 0), 2)

        cv2.imshow("PixelWar Tracker", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        await asyncio.sleep(0.01)

    cap.release()
    cv2.destroyAllWindows()


async def main():
    print("=== PixelWar Tracker Server ===")
    print(f"WebSocket : ws://{WS_HOST}:{WS_PORT}")
    print(f"Camera    : {'webcam' if USE_WEBCAM else f'{PHONE_IP}:{PHONE_PORT}'}\n")
    async with websockets.serve(ws_handler, WS_HOST, WS_PORT):
        await camera_loop()


if __name__ == "__main__":
    asyncio.run(main())
