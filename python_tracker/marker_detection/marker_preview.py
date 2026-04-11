"""ArUco marker preview (camera -> detect -> overlay IDs).

This script is a lightweight debug tool that:
- opens the camera
- runs ArUco detection
- draws detected markers and their IDs onto the frame
"""

import cv2

from python_tracker.camera.camera_runtime import open_camera, release_camera
from python_tracker.marker_detection.aruco_detector import create_detector


def main():
    cap = open_camera(1)

    if cap is None:
        print("Error: Cannot open camera")
        return 1

    detector = create_detector()

    print("Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Cannot read frame")
            break

        corners, ids, _ = detector.detectMarkers(frame)

        # If any markers were detected, draw them and annotate with IDs.
        if ids is not None and len(ids) > 0:
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)

            for i, marker_id in enumerate(ids.flatten()):
                # Use the marker's top-left corner as an anchor for the label.
                top_left = corners[i][0][0]
                x = int(top_left[0])
                y = int(top_left[1]) - 10

                cv2.putText(
                    frame,
                    f"ID: {marker_id}",
                    (x, y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA
                )

                print(f"Detected marker ID: {marker_id}")

        # Show the annotated frame.
        cv2.imshow("ArUco Detection", frame)

        # Press 'q' to quit.
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    release_camera(cap)
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
