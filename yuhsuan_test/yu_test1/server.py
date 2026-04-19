"""
Old Mick Against the Mob — Tracker Server  (yu_test1)

Changes from yuhsuan_test/server.py:
  1. 8-direction attack angles (E / NE / N / NW / W / SW / S / SE)
  2. Terrain marker detection  (Fence / Scarecrow / Termite Mound / Spinifex)
  3. Two game phases  → terrain_placement  →  game  (locked by browser button)
  4. Bidirectional WebSocket: client sends {"type":"lock_terrain"} to lock terrain
  5. Raw angle forwarded for every token so the browser can draw direction arrows

Marker ID assignment:
  0–3   : board corner markers
  10    : P1 ATK-A  (Rifleman 1)
  11    : P1 ATK-B  (Rifleman 2)
  12    : P1 DEF    (Old Mick)
  13    : turn marker  (0° = P1, 180° = P2)
  14    : P2 ATK-A  (Mob 1)
  15    : P2 ATK-B  (Mob 2)
  16    : P2 DEF    (Cassowary)
  17–18 : P1 hard terrain  (Fence Barricades)
  19–20 : P1 soft terrain  (Wheat Scarecrows)
  21–22 : P2 hard terrain  (Termite Mounds)
  23–24 : P2 soft terrain  (Spinifex)
  ─ Adjust any IDs above to match the markers you have printed ─
"""

import cv2
import numpy as np
import asyncio
import json
import websockets

# ── Configuration ─────────────────────────────────────────────────────────────

USE_WEBCAM   = True
WEBCAM_INDEX = 0
PHONE_IP     = "172.16.11.211"
PHONE_PORT   = 4747

WS_HOST = "localhost"
WS_PORT = 8765

GRID_COLS = 12
GRID_ROWS = 12
PADDING   = 1 / 14   # one border cell on each side (14×14 outer, 12×12 inner)

ARUCO_DICT_ID = cv2.aruco.DICT_4X4_50

# ── Marker ID tables ───────────────────────────────────────────────────────────

CORNER_IDS   = {0: "TL", 1: "TR", 2: "BL", 3: "BR"}
TURN_MARKER_ID = 13

P1_TOKENS = {10: "atk_a", 11: "atk_b", 12: "def"}
P2_TOKENS = {14: "atk_a", 15: "atk_b", 16: "def"}

# Terrain — each entry: marker_id → (group_key, display_name)
TERRAIN_IDS: dict[int, tuple[str, str]] = {
    17: ("p1_hard", "fence_1"),
    18: ("p1_hard", "fence_2"),
    19: ("p1_soft", "scarecrow_1"),
    20: ("p1_soft", "scarecrow_2"),
    21: ("p2_hard", "mound_1"),
    22: ("p2_hard", "mound_2"),
    23: ("p2_soft", "spinifex_1"),
    24: ("p2_soft", "spinifex_2"),
}

# ── 8-direction compass ────────────────────────────────────────────────────────

COMPASS_8 = [
    (0,   "E"),
    (45,  "SE"),
    (90,  "S"),
    (135, "SW"),
    (180, "W"),
    (225, "NW"),
    (270, "N"),
    (315, "NE"),
]


def snap_direction_8(angle: float) -> str:
    """Return the nearest compass label for a rotation angle."""
    return min(COMPASS_8, key=lambda d: abs((angle - d[0] + 180) % 360 - 180))[1]


def get_turn_from_angle(angle: float) -> int | None:
    if abs((angle - 0   + 180) % 360 - 180) <= 60:
        return 1
    if abs((angle - 180 + 180) % 360 - 180) <= 60:
        return 2
    return None

# ── Game phase state (mutated by WS handler) ──────────────────────────────────

game_phase      = "terrain_placement"   # "terrain_placement" | "game"
terrain_locked  = False
locked_terrain: dict = {}               # frozen terrain snapshot


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


def get_center(corners) -> tuple[float, float]:
    pts = corners[0]
    return float(np.mean(pts[:, 0])), float(np.mean(pts[:, 1]))


def get_angle(corners) -> float:
    tl, tr = corners[0][0], corners[0][1]
    return float(np.degrees(np.arctan2(tr[1] - tl[1], tr[0] - tl[0])) % 360)


# ── Homography ────────────────────────────────────────────────────────────────

def compute_homography(cc: dict):
    if not all(k in cc for k in ["TL", "TR", "BL", "BR"]):
        return None
    src = np.array([list(cc["TL"]), list(cc["TR"]),
                    list(cc["BL"]), list(cc["BR"])], dtype=np.float32)
    dst = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=np.float32)
    H, _ = cv2.findHomography(src, dst)
    return H


def to_grid_cell(H, point: tuple) -> tuple[int, int]:
    pt = np.array([[point]], dtype=np.float32).reshape(-1, 1, 2)
    nx, ny = cv2.perspectiveTransform(pt, H)[0][0]
    nx = (nx - PADDING) / (1 - 2 * PADDING)
    ny = (ny - PADDING) / (1 - 2 * PADDING)
    col = int(np.clip(nx * GRID_COLS, 0, GRID_COLS - 1))
    row = int(np.clip(ny * GRID_ROWS, 0, GRID_ROWS - 1))
    return col, row


# ── Frame detection ───────────────────────────────────────────────────────────

def detect_frame(frame, detector, aruco_dict, params, api_mode):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if api_mode == "modern":
        corners, ids, _ = detector.detectMarkers(gray)
    else:
        corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=params)

    corner_centers: dict = {}
    p1_tokens:      dict = {}
    p2_tokens:      dict = {}
    terrain_raw:    dict = {}   # marker_id → {center, angle}
    turn_angle            = None

    if ids is None:
        return corner_centers, p1_tokens, p2_tokens, terrain_raw, turn_angle

    for i, mid in enumerate(ids.flatten()):
        center = get_center(corners[i])
        angle  = get_angle(corners[i])

        if mid in CORNER_IDS:
            corner_centers[CORNER_IDS[mid]] = center

        elif mid in P1_TOKENS:
            p1_tokens[P1_TOKENS[mid]] = {
                "angle": round(angle, 1), "center": center,
                "direction": snap_direction_8(angle),
            }

        elif mid in P2_TOKENS:
            p2_tokens[P2_TOKENS[mid]] = {
                "angle": round(angle, 1), "center": center,
                "direction": snap_direction_8(angle),
            }

        elif mid in TERRAIN_IDS:
            terrain_raw[mid] = {"center": center, "angle": round(angle, 1)}

        elif mid == TURN_MARKER_ID:
            turn_angle = angle

    return corner_centers, p1_tokens, p2_tokens, terrain_raw, turn_angle


# ── WebSocket ─────────────────────────────────────────────────────────────────

connected_clients: set = set()


async def ws_handler(websocket):
    global game_phase, terrain_locked, locked_terrain

    connected_clients.add(websocket)
    print(f"[WS] Client connected  ({len(connected_clients)} total)")
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                if data.get("type") == "lock_terrain":
                    terrain_locked = True
                    game_phase     = "game"
                    print("[PHASE] Terrain locked → Battle phase!")
            except (json.JSONDecodeError, KeyError):
                pass
    except websockets.exceptions.ConnectionClosed:
        pass
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
    global locked_terrain

    cap = open_camera()
    if cap is None:
        return

    detector, aruco_dict, params, api_mode = build_detector()
    print(f"[OK] ArUco detector ready ({api_mode} API)")
    print("[PHASE 1] Place terrain markers, then click LOCK TERRAIN in the browser.\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Failed to read frame — check camera.")
            break

        cc, p1t, p2t, terrain_raw, turn_angle = detect_frame(
            frame, detector, aruco_dict, params, api_mode
        )
        H = compute_homography(cc)

        # ── Resolve token pixel → grid ─────────────────────────────────────
        def resolve_tokens(token_dict: dict) -> dict:
            out = {}
            for role, info in token_dict.items():
                col, row = to_grid_cell(H, info["center"]) if H is not None else (None, None)
                out[role] = {
                    "col":       col,
                    "row":       row,
                    "angle":     info["angle"],     # raw angle for arrow drawing
                    "direction": info["direction"], # snapped 8-direction for ray
                }
            return out

        # ── Resolve terrain pixel → grid ───────────────────────────────────
        if terrain_locked and locked_terrain:
            # Phase 2: use frozen positions
            terrain_state = locked_terrain
        else:
            terrain_state: dict = {"p1_hard": [], "p1_soft": [], "p2_hard": [], "p2_soft": []}
            for mid, info in terrain_raw.items():
                group, name = TERRAIN_IDS[mid]
                col, row = to_grid_cell(H, info["center"]) if H is not None else (None, None)
                terrain_state[group].append({"id": int(mid), "name": name, "col": col, "row": row})

            # Freeze the moment the lock arrives
            if terrain_locked and not locked_terrain:
                locked_terrain = terrain_state
                print(f"[OK] Terrain frozen: {locked_terrain}")

        turn = get_turn_from_angle(turn_angle) if turn_angle is not None else None

        state = {
            "phase":          game_phase,
            "terrain_locked": terrain_locked,
            "corners_found":  len(cc),
            "turn":           turn,
            "turn_angle":     round(turn_angle, 1) if turn_angle is not None else None,
            "p1":             resolve_tokens(p1t),
            "p2":             resolve_tokens(p2t),
            "terrain":        terrain_state,
        }
        await broadcast(state)

        # ── Camera overlay ─────────────────────────────────────────────────
        phase_color = (0, 255, 100) if game_phase == "game" else (100, 200, 255)
        cv2.putText(frame, f"Phase: {game_phase.upper()}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, phase_color, 2)
        cv2.putText(frame, f"Corners: {len(cc)}/4",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (0, 255, 0) if len(cc) == 4 else (0, 100, 255), 2)
        if turn is not None:
            cv2.putText(frame, f"Turn: P{turn}",
                        (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 220, 0), 2)
        terrain_count = sum(len(v) for v in terrain_state.values())
        cv2.putText(frame, f"Terrain: {terrain_count}  Locked: {terrain_locked}",
                    (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 180, 100), 1)

        cv2.imshow("Old Mick Tracker", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        await asyncio.sleep(0.01)

    cap.release()
    cv2.destroyAllWindows()


async def main():
    print("=== Old Mick Against the Mob — Tracker Server ===")
    print(f"WebSocket : ws://{WS_HOST}:{WS_PORT}")
    print(f"Camera    : {'webcam (index 0)' if USE_WEBCAM else f'{PHONE_IP}:{PHONE_PORT}'}\n")
    async with websockets.serve(ws_handler, WS_HOST, WS_PORT):
        await camera_loop()


if __name__ == "__main__":
    asyncio.run(main())
