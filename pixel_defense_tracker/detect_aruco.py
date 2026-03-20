import cv2


def main():
    # 開啟預設攝影機
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Cannot open camera")
        return

    # 選擇 ArUco dictionary
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)

    # 建立 detector parameters
    detector_params = cv2.aruco.DetectorParameters()

    # 建立 ArUco detector
    detector = cv2.aruco.ArucoDetector(aruco_dict, detector_params)

    print("Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Cannot read frame")
            break

        # 偵測 marker
        corners, ids, rejected = detector.detectMarkers(frame)

        # 如果有偵測到 marker
        if ids is not None and len(ids) > 0:
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)

            for i, marker_id in enumerate(ids.flatten()):
                # 取 marker 左上角座標來顯示文字
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

        # 顯示畫面
        cv2.imshow("ArUco Detection", frame)

        # 按 q 離開
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()