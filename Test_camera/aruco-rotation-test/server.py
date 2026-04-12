import cv2
import numpy as np
import asyncio
import json
import websockets

# ============================================================
# CONFIGURATION — change the IP address here to match your phone
# ============================================================
PHONE_IP   = "172.16.11.211"
PHONE_PORT = 4747
CAMERA_URL = f"http://{PHONE_IP}:{PHONE_PORT}/video"

# Set to True to use laptop webcam instead of phone camera
USE_WEBCAM = True
WEBCAM_INDEX = 0

# WebSocket server address
WS_HOST = "localhost"
WS_PORT = 8765

# ArUco dictionary — must match the printed markers
ARUCO_DICT_ID = cv2.aruco.DICT_4X4_50

# Grid dimensions — must match index.html
GRID_COLS = 6
GRID_ROWS = 4

# Rotation detection tolerance (degrees)
TOLERANCE = 30
DIRECTIONS = [
    (  0, "ATTACK HQ"),
    ( 90, "ATTACK RIGHT"),
    (180, "DEFEND"),
    (270, "ATTACK LEFT"),
]

# Corner marker IDs — which ID maps to which board corner
CORNER_IDS = {
    0: "TL",   # top-left
    1: "TR",   # top-right
    2: "BL",   # bottom-left
    3: "BR",   # bottom-right
}

# Token player assignment by marker ID
PLAYER1_IDS = range(10, 14)   # ID 10, 11, 12, 13
PLAYER2_IDS = range(14, 18)   # ID 14, 15, 16, 17

# Global set of connected WebSocket clients
connected_clients = set()


# ---------- Camera ----------

def open_camera():
    """Open the phone camera stream (or webcam if USE_WEBCAM is True)."""
    source = WEBCAM_INDEX if USE_WEBCAM else CAMERA_URL
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[ERROR] Could not open camera: {source}")
        return None
    print(f"[OK] Camera opened: {source}")
    return cap


# ---------- ArUco ----------

def build_detector():
    """Create an ArUco detector for DICT_4X4_50."""
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT_ID)
    params     = cv2.aruco.DetectorParameters()
    if hasattr(cv2.aruco, "ArucoDetector"):
        return cv2.aruco.ArucoDetector(aruco_dict, params), aruco_dict, params, "modern"
    return None, aruco_dict, params, "legacy"


def get_center(corners):
    """Get the center point of a marker by averaging its 4 corners."""
    pts = corners[0]
    return (float(np.mean(pts[:, 0])), float(np.mean(pts[:, 1])))


def get_angle(corners):
    """Calculate the rotation angle (0–360°) from the top edge of a marker."""
    top_left  = corners[0][0]
    top_right = corners[0][1]
    dx = top_right[0] - top_left[0]
    dy = top_right[1] - top_left[1]
    return np.degrees(np.arctan2(dy, dx)) % 360


def get_direction(angle):
    """Map a rotation angle to a direction string, or None if unrecognized."""
    for target, label in DIRECTIONS:
        if abs((angle - target + 180) % 360 - 180) <= TOLERANCE:
            return label
    return None


def get_player(marker_id):
    """Return 1 or 2 depending on which player owns the marker ID."""
    if marker_id in PLAYER1_IDS:
        return 1
    if marker_id in PLAYER2_IDS:
        return 2
    return None


# ---------- Homography (board position) ----------

def compute_homography(corner_centers):
    """
    Compute a perspective transform from the 4 corner marker positions.
    This corrects for camera angle — maps any point on the board to
    normalized coordinates [0, 1] x [0, 1].

    corner_centers: dict with keys "TL", "TR", "BL", "BR" -> (x, y)
    Returns a 3x3 matrix, or None if not all 4 corners are visible.
    """
    if not all(k in corner_centers for k in ["TL", "TR", "BL", "BR"]):
        return None

    src = np.float32([
        corner_centers["TL"],
        corner_centers["TR"],
        corner_centers["BL"],
        corner_centers["BR"],
    ])

    # Map corners to a unit square [0,1] x [0,1]
    dst = np.float32([[0, 0], [1, 0], [0, 1], [1, 1]])

    H, _ = cv2.findHomography(src, dst)
    return H


def apply_homography(H, point):
    """
    Transform a single (x, y) point using the homography matrix.
    Returns normalized board coordinates (nx, ny) in range [0, 1].
    """
    p = np.float32([[point]]).reshape(-1, 1, 2)
    result = cv2.perspectiveTransform(p, H)
    return float(result[0][0][0]), float(result[0][0][1])


def to_grid_cell(nx, ny):
    """
    Convert normalized coordinates [0,1] x [0,1] to a grid cell (col, row).
    Clamps to valid grid range.
    """
    col = max(0, min(GRID_COLS - 1, int(nx * GRID_COLS)))
    row = max(0, min(GRID_ROWS - 1, int(ny * GRID_ROWS)))
    return col, row


# ---------- Detection ----------

def detect_all_markers(frame, detector, aruco_dict, params, api_mode):
    """
    Detect all markers in a frame.
    Returns:
      corner_centers — dict mapping corner name to (x, y)
      tokens         — list of token info dicts (id, player, angle, direction, center)
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    if api_mode == "modern":
        corners, ids, _ = detector.detectMarkers(gray)
    else:
        corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=params)

    corner_centers = {}
    tokens         = []

    if ids is None:
        return corner_centers, tokens

    for i, marker_id in enumerate(ids.flatten()):
        center = get_center(corners[i])
        angle  = get_angle(corners[i])

        if marker_id in CORNER_IDS:
            # It's a board corner — save its center for homography
            corner_centers[CORNER_IDS[marker_id]] = center
        else:
            # It's a token — save position and direction
            player    = get_player(marker_id)
            direction = get_direction(angle)
            if player and direction:
                tokens.append({
                    "id":        int(marker_id),
                    "player":    player,
                    "angle":     round(float(angle), 1),
                    "direction": direction,
                    "center":    center,
                })

    return corner_centers, tokens


# ---------- WebSocket ----------

async def ws_handler(websocket):
    """Handle a new WebSocket client connection."""
    connected_clients.add(websocket)
    print(f"[WS] Client connected — total: {len(connected_clients)}")
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.discard(websocket)
        print(f"[WS] Client disconnected — total: {len(connected_clients)}")


async def broadcast(message: dict):
    """Send a JSON message to every connected WebSocket client."""
    if not connected_clients:
        return
    data = json.dumps(message)
    await asyncio.gather(*[client.send(data) for client in connected_clients])


# ---------- Main loop ----------

async def camera_loop():
    """
    Continuously read frames, detect markers, calculate grid positions,
    and broadcast results to all WebSocket clients.
    """
    cap = open_camera()
    if cap is None:
        return

    detector, aruco_dict, params, api_mode = build_detector()
    print(f"[OK] ArUco detector ready ({api_mode} API)")
    print("Press 'q' in the camera window to quit.\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Failed to read frame.")
            break

        corner_centers, tokens = detect_all_markers(frame, detector, aruco_dict, params, api_mode)
        H = compute_homography(corner_centers)

        # Show how many corners are visible on the camera feed
        corners_found = len(corner_centers)
        status_color  = (0, 255, 0) if corners_found == 4 else (0, 100, 255)
        cv2.putText(frame, f"Corners: {corners_found}/4", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

        for token in tokens:
            # Calculate grid position if all 4 corners are visible
            if H is not None:
                nx, ny    = apply_homography(H, token["center"])
                col, row  = to_grid_cell(nx, ny)
            else:
                col, row  = None, None

            message = {
                "id":        token["id"],
                "player":    token["player"],
                "col":       col,
                "row":       row,
                "direction": token["direction"],
                "angle":     token["angle"],
            }
            await broadcast(message)

            pos_str = f"({col},{row})" if col is not None else "(?,?)"
            print(f"  P{token['player']} ID {token['id']:>3} | {pos_str} | "
                  f"{token['angle']:>6.1f}° | {token['direction']}")

        cv2.imshow("ArUco Server", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        await asyncio.sleep(0.01)

    cap.release()
    cv2.destroyAllWindows()


async def main():
    """Start the WebSocket server and the camera loop together."""
    print("=== ArUco WebSocket Server ===")
    print(f"WebSocket : ws://{WS_HOST}:{WS_PORT}")
    print(f"Camera    : {'webcam' if USE_WEBCAM else CAMERA_URL}\n")

    async with websockets.serve(ws_handler, WS_HOST, WS_PORT):
        await camera_loop()


if __name__ == "__main__":
    asyncio.run(main())
