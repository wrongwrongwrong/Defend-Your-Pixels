import cv2
import numpy as np

# ============================================================
# CONFIGURATION — change the IP address here to match your phone
# ============================================================
PHONE_IP = "172.16.11.211"   # <-- replace with your phone's IP
PHONE_PORT = 4747            # default DroidCam port
CAMERA_URL = f"http://{PHONE_IP}:{PHONE_PORT}/video"

# Use a local webcam instead of phone camera (set to True for testing)
USE_WEBCAM = True
WEBCAM_INDEX = 0

# ArUco dictionary — must match the printed markers
ARUCO_DICT = cv2.aruco.DICT_4X4_50

# Rotation thresholds (degrees). Angles within ±TOLERANCE of a target
# are snapped to that direction.
TOLERANCE = 30

# Direction definitions: (target_angle, label, BGR_color)
DIRECTIONS = [
    (  0, "ATTACK HQ",    (  0, 255,   0)),   # green
    ( 90, "ATTACK RIGHT", (255,   0,   0)),   # blue
    (180, "DEFEND",       (  0,   0, 255)),   # red
    (270, "ATTACK LEFT",  (  0, 255, 255)),   # yellow
]


def open_camera():
    """
    Open the video stream.
    Returns a cv2.VideoCapture object, or None if it could not be opened.
    Tries the phone camera URL unless USE_WEBCAM is True.
    """
    if USE_WEBCAM:
        cap = cv2.VideoCapture(WEBCAM_INDEX)
        source_name = f"webcam index {WEBCAM_INDEX}"
    else:
        cap = cv2.VideoCapture(CAMERA_URL)
        source_name = CAMERA_URL

    if not cap.isOpened():
        print(f"[ERROR] Could not open camera: {source_name}")
        return None

    print(f"[OK] Camera opened: {source_name}")
    return cap


def build_aruco_detector():
    """
    Create and return an ArUco detector configured for DICT_4X4_50.
    Uses the modern API (OpenCV 4.7+) if available, otherwise falls back
    to the legacy detectMarkers() approach.
    """
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    params = cv2.aruco.DetectorParameters()

    # Modern API: ArucoDetector object
    if hasattr(cv2.aruco, "ArucoDetector"):
        detector = cv2.aruco.ArucoDetector(aruco_dict, params)
        return detector, aruco_dict, params, "modern"

    # Legacy API fallback
    return None, aruco_dict, params, "legacy"


def compute_rotation_angle(corners):
    """
    Calculate the rotation angle (in degrees, 0-360) of a single detected marker.

    corners: numpy array of shape (1, 4, 2) containing the four corner points
             returned by the ArUco detector. The corners are ordered:
             [top-left, top-right, bottom-right, bottom-left].

    The angle is measured as the direction of the top edge (top-left → top-right)
    relative to the positive X axis, then converted to a 0-360 range.
    """
    pts = corners[0]          # shape (4, 2)
    top_left  = pts[0]
    top_right = pts[1]

    # Vector along the top edge
    dx = top_right[0] - top_left[0]
    dy = top_right[1] - top_left[1]

    # atan2 returns angle in radians; convert to degrees
    angle_rad = np.arctan2(dy, dx)
    angle_deg = np.degrees(angle_rad)

    # Normalize to [0, 360)
    angle_deg = angle_deg % 360

    return angle_deg


def angle_to_direction(angle_deg):
    """
    Map a rotation angle (degrees) to a game direction label and display color.

    Returns (label, color) where color is a BGR tuple, or (None, None) if the
    angle does not fall within TOLERANCE of any defined direction.
    """
    for target_angle, label, color in DIRECTIONS:
        # Compute the shortest angular distance between angle_deg and target_angle
        diff = abs((angle_deg - target_angle + 180) % 360 - 180)
        if diff <= TOLERANCE:
            return label, color

    return None, None


def draw_marker_info(frame, corners, marker_id, angle_deg, label, color):
    """
    Draw the marker outline, ID, angle, and direction label onto the frame.

    frame     : the BGR image to draw on (modified in-place)
    corners   : corner array for this marker (shape 1×4×2)
    marker_id : integer marker ID
    angle_deg : computed rotation angle in degrees
    label     : direction string, or None if angle is unrecognized
    color     : BGR tuple for the direction label
    """
    pts = corners[0].astype(int)

    # Draw the marker outline
    cv2.polylines(frame, [pts], isClosed=True, color=(0, 200, 200), thickness=2)

    # Mark the top-left corner so the orientation is visible
    cv2.circle(frame, tuple(pts[0]), 6, (0, 255, 255), -1)

    # Position text just above the top-left corner
    text_x = int(pts[:, 0].min())
    text_y = int(pts[:, 1].min()) - 10

    # Marker ID
    cv2.putText(frame, f"ID:{marker_id}", (text_x, text_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    # Rotation angle
    cv2.putText(frame, f"{angle_deg:.1f} deg", (text_x, text_y + 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

    # Direction label (if recognized)
    if label:
        cv2.putText(frame, label, (text_x, text_y + 45),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)


def detect_and_process(frame, detector, aruco_dict, params, api_mode):
    """
    Detect all ArUco markers in the frame, compute their rotation angles,
    determine directions, and annotate the frame.

    Returns a list of dicts with keys: id, angle, label
    so the caller can also print results to the terminal.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    if api_mode == "modern":
        corners, ids, _ = detector.detectMarkers(gray)
    else:
        corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=params)

    results = []

    if ids is None:
        return results   # nothing detected

    for i, marker_id in enumerate(ids.flatten()):
        angle_deg = compute_rotation_angle(corners[i])
        label, color = angle_to_direction(angle_deg)

        draw_marker_info(frame, corners[i], marker_id, angle_deg, label, color)

        results.append({
            "id":    marker_id,
            "angle": angle_deg,
            "label": label if label else "UNKNOWN",
        })

    return results


def print_results(results):
    """
    Print the detection results to the terminal in a readable format.
    Only called when at least one marker is detected.
    """
    print("-" * 40)
    for r in results:
        print(f"  Marker ID {r['id']:>3}  |  {r['angle']:>6.1f} deg  |  {r['label']}")
    print("-" * 40)


def main():
    """
    Main loop: open the camera, continuously grab frames, detect markers,
    annotate the video feed, and print results to the terminal.
    Press 'q' to quit.
    """
    print("=== ArUco Rotation Test ===")
    print(f"Dictionary : DICT_4X4_50")
    print(f"Camera     : {'webcam' if USE_WEBCAM else CAMERA_URL}")
    print("Press 'q' to quit.\n")

    cap = open_camera()
    if cap is None:
        return

    detector, aruco_dict, params, api_mode = build_aruco_detector()
    print(f"ArUco API  : {api_mode}\n")

    prev_ids = set()   # track changes so terminal isn't flooded

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Failed to read frame — check camera connection.")
            break

        results = detect_and_process(frame, detector, aruco_dict, params, api_mode)

        # Print to terminal only when the set of detected IDs changes
        current_ids = {r["id"] for r in results}
        if current_ids != prev_ids and results:
            print_results(results)
        prev_ids = current_ids

        # Overlay a small help text at the bottom of the frame
        h, w = frame.shape[:2]
        cv2.putText(frame, "Press 'q' to quit", (10, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

        cv2.imshow("ArUco Rotation Test", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Camera released. Goodbye.")


if __name__ == "__main__":
    main()
