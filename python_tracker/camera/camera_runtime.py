import cv2


def open_camera(camera_id: int = 0):
    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        return None
    return cap


def configure_camera(cap, width: int = 1280, height: int = 720):
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)


def release_camera(cap):
    if cap is not None:
        cap.release()
