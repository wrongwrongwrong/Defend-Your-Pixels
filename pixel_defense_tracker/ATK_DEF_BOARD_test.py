import cv2


ATK_IDS = {10, 11}
DEF_IDS = {12, 13}
BOARD_IDS = {0, 1, 2, 3}


def get_marker_type(marker_id: int) -> str:
    if marker_id in ATK_IDS:
        return "ATK"
    if marker_id in DEF_IDS:
        return "DEF"
    if marker_id in BOARD_IDS:
        return "BOARD"
    return "UNKNOWN"


def get_marker_center(corner):
    points = corner[0]
    center_x = int(points[:, 0].mean())
    center_y = int(points[:, 1].mean())
    return center_x, center_y


def main():
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Cannot open camera")
        return

    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    detector_params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, detector_params)

    print("Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Cannot read frame")
            break

        corners, ids, _ = detector.detectMarkers(frame)

        if ids is not None and len(ids) > 0:
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)

            for i, marker_id in enumerate(ids.flatten()):
                marker_type = get_marker_type(int(marker_id))
                center_x, center_y = get_marker_center(corners[i])

                label = f"{marker_type} | ID {marker_id} | ({center_x}, {center_y})"

                cv2.putText(
                    frame,
                    label,
                    (center_x - 80, center_y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA
                )

                print(label)

        cv2.imshow("Token Detection", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()