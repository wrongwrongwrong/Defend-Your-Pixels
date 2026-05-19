"""Simple camera preview window (no marker detection)."""

import cv2

from python_tracker.camera.camera_runtime import open_camera, release_camera


def main(camera_id: int = 1):
    cap = open_camera(camera_id)
    if cap is None:
        print(f"Error: Cannot open camera (index {camera_id})")
        return 1

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("Error: Cannot read frame")
                return 1

            cv2.imshow("Camera Preview", frame)
            if cv2.waitKey(1) == 27:
                break
    finally:
        release_camera(cap)
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
