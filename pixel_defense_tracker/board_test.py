import sys
from pathlib import Path

import cv2
import numpy as np
# this code is modified from:
# http://github.com/yunus-temurlenk/Augmented-Reality-Projects-with-Aruco-Markers/blob/main/main.cpp

MARKER_ORDER = (10, 11, 12, 13)
ARUCO_DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)


def open_first_available_camera(preferred_index: int = 0, max_index: int = 4):
    order = [preferred_index] + [i for i in range(0, max_index + 1) if i != preferred_index]
    for index in order:
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            ok, frame = cap.read()
            if ok and frame is not None:
                return cap, index
        cap.release()
    return None, None


def resolve_overlay_source(base: Path) -> str:
    candidates = ("board.jpg", "Board.jpg", "overlay.mp4", "board.mp4")
    for name in candidates:
        p = base / name
        if p.is_file():
            return str(p)
    raise FileNotFoundError(
        f"No overlay source found in {base}. Add one of: {', '.join(candidates)}"
    )


def center_from_marker(corner: np.ndarray) -> np.ndarray:
    pts = corner.reshape(4, 2)
    center = (pts[0] + pts[2]) / 2.0
    return center.astype(np.float32)


def get_destination_points(corners, ids) -> np.ndarray | None:
    if ids is None or len(ids) < 4:
        return None

    flat_ids = ids.flatten().astype(int)
    found = {int(flat_ids[i]): corners[i] for i in range(len(flat_ids))}
    if not all(marker_id in found for marker_id in MARKER_ORDER):
        return None

    pts_out = [center_from_marker(found[marker_id]) for marker_id in MARKER_ORDER]
    return np.float32(pts_out)


def load_next_overlay_frame(overlay_cap: cv2.VideoCapture, fallback_image: np.ndarray):
    if overlay_cap is None:
        return fallback_image

    ok, frame = overlay_cap.read()
    if ok and frame is not None:
        return frame

    overlay_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    ok, frame = overlay_cap.read()
    if ok and frame is not None:
        return frame
    return fallback_image


def main() -> int:
    overlay_path = "/Users/yuxuanshi/Downloads/Defend-Your-Pixels/Board.jpg"
   
    cap_in, cam_idx = open_first_available_camera(0, 4)
    if cap_in is None:
        print("Cannot open camera (tried indices 0..4).", file=sys.stderr)
        return 1

    overlay_image = cv2.imread(overlay_path)
    overlay_cap = None
    if overlay_image is None:
        overlay_cap = cv2.VideoCapture(overlay_path)
        if not overlay_cap.isOpened():
            print(f"Cannot open overlay source: {overlay_path}", file=sys.stderr)
            cap_in.release()
            return 1

    detector = cv2.aruco.ArucoDetector(ARUCO_DICT, cv2.aruco.DetectorParameters())
    cv2.namedWindow("Out", cv2.WINDOW_NORMAL)
    print(f"Using camera index: {cam_idx}")
    print(f"Overlay source: {overlay_path}")
    print("Detect marker IDs 0,34,30,4. Press q to quit.")

    try:
        while True:
            ok_in, img_in = cap_in.read()
            if not ok_in or img_in is None:
                break

            frame_backup = img_in.copy()
            overlay_frame = load_next_overlay_frame(overlay_cap, overlay_image)
            if overlay_frame is None:
                print("Overlay frame is empty; check overlay source file.", file=sys.stderr)
                break

            corners, ids, _ = detector.detectMarkers(img_in)
            pts_out = get_destination_points(corners, ids)

            if pts_out is not None:
                h, w = overlay_frame.shape[:2]
                pts_in = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
                matrix = cv2.getPerspectiveTransform(pts_in, pts_out)
                warped = cv2.warpPerspective(overlay_frame, matrix, (img_in.shape[1], img_in.shape[0]))

                # Match the original C++ behavior: keep camera pixels where warped image is near black.
                img_in = warped.copy()
                black_mask = np.all(warped <= 5, axis=2)
                img_in[black_mask] = frame_backup[black_mask]

            cv2.imshow("Out", img_in)
            if (cv2.waitKey(1) & 0xFF) == ord("q"):
                break
    finally:
        cap_in.release()
        if overlay_cap is not None:
            overlay_cap.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    sys.exit(main())
