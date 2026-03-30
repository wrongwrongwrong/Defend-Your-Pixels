"""
server.py — Pixel Defense WebSocket Bridge
==========================================
Opens the webcam, detects ArUco markers, maps positions to the 12x12 game
grid using a perspective transform, then broadcasts JSON game-state updates
to all connected React clients at ~10 fps.

Board setup:
  Place 4 corner markers (ID 0–3) at the physical corners of the board:
    ID 0 = top-left
    ID 1 = top-right
    ID 2 = bottom-left
    ID 3 = bottom-right

  Token markers:
    ID 10–13 = Player 1 tokens  (Infantry, Tank, Bomber, DEF)
    ID 14–17 = Player 2 tokens  (Infantry, Tank, Bomber, DEF)

Run:
    python server.py

Then open the React app at http://localhost:5173
Press Q in the camera preview window to stop the server.
"""

import asyncio
import json
import math

import cv2
import numpy as np
import websockets
from websockets.server import serve

# ── Constants ────────────────────────────────────────────────────────────────

GRID_COLS = 12
GRID_ROWS = 12
WS_HOST   = "localhost"
WS_PORT   = 8765
CAMERA_ID = 0           # Change to 1, 2, … if you have multiple cameras
SEND_FPS  = 10          # How many updates per second to send to React

BOARD_CORNER_IDS = {0, 1, 2, 3}
TOKEN_IDS        = set(range(10, 18))

# ── Shared WebSocket state ────────────────────────────────────────────────────

connected_clients: set = set()


# ── Perspective transform helpers ────────────────────────────────────────────

def build_homography(board_corners_px: dict):
    """
    Compute a 3×3 homography from the 4 board-corner markers' pixel positions
    to 12×12 grid space.
    Returns H matrix or None if fewer than 4 corners are visible.
    """
    if not all(k in board_corners_px for k in [0, 1, 2, 3]):
        return None

    # Source: pixel positions of the four physical corners
    src = np.float32([
        board_corners_px[0],  # top-left
        board_corners_px[1],  # top-right
        board_corners_px[2],  # bottom-left
        board_corners_px[3],  # bottom-right
    ])

    # Destination: corresponding positions in 12×12 grid space
    dst = np.float32([
        [0,          0         ],  # top-left
        [GRID_COLS,  0         ],  # top-right
        [0,          GRID_ROWS ],  # bottom-left
        [GRID_COLS,  GRID_ROWS ],  # bottom-right
    ])

    H, _ = cv2.findHomography(src, dst)
    return H


def pixel_to_grid(px: float, py: float, H) -> tuple[float, float] | tuple[None, None]:
    """Apply homography to map a pixel position to grid (x, y) coordinates."""
    if H is None:
        return None, None
    pt = np.float32([[[px, py]]])
    warped = cv2.perspectiveTransform(pt, H)[0][0]
    gx = float(np.clip(warped[0], 0, GRID_COLS - 1))
    gy = float(np.clip(warped[1], 0, GRID_ROWS - 1))
    return round(gx, 2), round(gy, 2)


def compute_rotation_deg(corners4) -> float:
    """
    Compute the marker's facing direction in degrees (0° = pointing right/east).
    The React frontend converts this to forward/left/right/backward strings.
    corners4: shape (4, 2) — [top-left, top-right, bottom-right, bottom-left]
    """
    tl = corners4[0]
    tr = corners4[1]
    dx = float(tr[0] - tl[0])
    dy = float(tr[1] - tl[1])
    angle_deg = math.degrees(math.atan2(dy, dx))
    return (angle_deg + 360) % 360  # normalise to 0–360


# ── Frame processing ──────────────────────────────────────────────────────────

def process_frame(frame, detector) -> tuple[list, list, object]:
    """
    Detect ArUco markers in a frame.
    Returns (markers_data, board_corners_data, annotated_frame).
    """
    corners, ids, _ = detector.detectMarkers(frame)

    markers_out       = []
    board_corners_out = []
    board_corners_px  = {}

    if ids is None:
        cv2.putText(frame, "No markers detected", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 100, 255), 2)
        return markers_out, board_corners_out, frame

    cv2.aruco.drawDetectedMarkers(frame, corners, ids)

    # ── Pass 1: collect board corner markers ─────────────────────────────
    for i, mid in enumerate(ids.flatten()):
        if mid in BOARD_CORNER_IDS:
            center = corners[i][0].mean(axis=0)
            board_corners_px[int(mid)] = center
            board_corners_out.append({
                "id": int(mid),
                "position": {"x": round(float(center[0]), 1),
                             "y": round(float(center[1]), 1)},
            })

    # Show how many corners are found
    n_corners = len(board_corners_px)
    corner_color = (0, 255, 0) if n_corners == 4 else (0, 140, 255)
    cv2.putText(frame, f"Board corners: {n_corners}/4", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, corner_color, 2)

    # Build perspective transform only when all 4 corners are visible
    H = build_homography(board_corners_px)

    if H is not None:
        # Draw warped grid overlay for debugging
        _draw_grid_overlay(frame, H)

    # ── Pass 2: process token markers ────────────────────────────────────
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
            label = f"ID:{mid} G({gx:.1f},{gy:.1f}) R:{rotation_deg:.0f}°"
        else:
            # No homography yet — report raw pixel position
            markers_out.append({
                "id": int(mid),
                "position": {"x": round(px, 1), "y": round(py, 1)},
                "rotation": round(rotation_deg, 1),
            })
            label = f"ID:{mid} (no corners)"

        cv2.putText(frame, label,
                    (int(px) + 5, int(py) - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 255, 100), 1, cv2.LINE_AA)

    return markers_out, board_corners_out, frame


def _draw_grid_overlay(frame, H):
    """Draw a faint 12×12 grid projected onto the camera view (inverse H)."""
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
        pass  # Singular matrix or invalid transform — skip overlay


# ── WebSocket handlers ────────────────────────────────────────────────────────

async def ws_handler(websocket):
    """Accept a new client and keep the connection open."""
    connected_clients.add(websocket)
    addr = websocket.remote_address
    print(f"[WS] Client connected: {addr}  (total: {len(connected_clients)})")
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.discard(websocket)
        print(f"[WS] Client disconnected: {addr}  (total: {len(connected_clients)})")


async def broadcast(message: str):
    """Send a message to all connected clients, ignoring failures."""
    if not connected_clients:
        return
    await asyncio.gather(
        *[client.send(message) for client in connected_clients],
        return_exceptions=True,
    )


# ── Camera loop ───────────────────────────────────────────────────────────────

async def camera_loop():
    cap = cv2.VideoCapture(CAMERA_ID)
    if not cap.isOpened():
        print(f"[Camera] ERROR: Cannot open camera (index {CAMERA_ID})")
        print("  → Try changing CAMERA_ID at the top of server.py")
        return

    # Optionally increase resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    params     = cv2.aruco.DetectorParameters()
    detector   = cv2.aruco.ArucoDetector(aruco_dict, params)

    interval = 1.0 / SEND_FPS
    print(f"[Camera] Capturing at {SEND_FPS} fps  (press Q to quit)")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[Camera] WARNING: Frame read failed — retrying…")
                await asyncio.sleep(0.1)
                continue

            markers, board_corners, annotated = process_frame(frame, detector)

            # Build and broadcast the JSON message
            msg = json.dumps({
                "type": "game_state",
                "data": {
                    "markers":       markers,
                    "board_corners": board_corners,
                },
            })
            await broadcast(msg)

            # Show annotated preview
            cv2.imshow("Pixel Defense — Camera View  [Q to quit]", annotated)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("[Camera] Quit signal received.")
                break

            await asyncio.sleep(interval)

    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("[Camera] Released.")


# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    print("=" * 55)
    print("  Pixel Defense WebSocket Server")
    print(f"  ws://{WS_HOST}:{WS_PORT}")
    print("=" * 55)
    print()
    print("  Board corner markers (ArUco DICT_4X4_50):")
    print("    ID 0 = top-left     ID 1 = top-right")
    print("    ID 2 = bottom-left  ID 3 = bottom-right")
    print()
    print("  Token markers:")
    print("    ID 10=P1 Infantry  11=P1 Tank  12=P1 Bomber  13=P1 DEF")
    print("    ID 14=P2 Infantry  15=P2 Tank  16=P2 Bomber  17=P2 DEF")
    print()

    async with serve(ws_handler, WS_HOST, WS_PORT):
        print(f"[Server] Listening on ws://{WS_HOST}:{WS_PORT}")
        print("[Server] Open http://localhost:5173 in your browser\n")
        await camera_loop()


if __name__ == "__main__":
    asyncio.run(main())
