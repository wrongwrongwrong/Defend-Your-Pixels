import sys
import cv2

def open_first_available_camera(preferred_index: int = 0, max_index: int = 4):
    order = [preferred_index] + [i for i in range(0, max_index + 1) if i != preferred_index]
    for index in order:
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            ok, frame = cap.read()
            if ok and frame is not None:
                return cap, index
            cap.release()
            continue
        cap.release()
    return None, None


def main(camera_index: int = 0) -> int:
    cap, active_index = open_first_available_camera(preferred_index=camera_index, max_index=4)
    if cap is None:
        print(
            "Could not find a working webcam from index 0 to 4.\n"
            "On macOS, also check Camera permissions for your Terminal/Python, "
            "and close any other app using the camera.",
            file=sys.stderr,
        )
        return 1
    print(f"Using camera index: {active_index}")

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("Failed to read webcam frame.", file=sys.stderr)
                break

            cv2.imshow("camera", frame)

            # ESC key to quit
            if cv2.waitKey(1) == 27:
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    sys.exit(main())