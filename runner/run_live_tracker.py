import asyncio

import cv2

from bridge.adapters.tracker_message_adapter import build_tracker_message
from bridge.transport.websocket_transport import WS_HOST, WS_PORT, broadcast, run_server
from python_tracker.camera.camera_runtime import configure_camera, open_camera, release_camera
from python_tracker.marker_detection.aruco_detector import create_detector
from python_tracker.state_output.tracker_snapshot import build_tracker_preview


CAMERA_ID = 0
SEND_FPS = 10


async def publish_live_tracker(camera_id: int = CAMERA_ID, send_fps: int = SEND_FPS):
    cap = open_camera(camera_id)
    if cap is None:
        print(f"[Camera] ERROR: Cannot open camera (index {camera_id})")
        return

    configure_camera(cap)
    detector = create_detector()
    interval = 1.0 / send_fps

    print(f"[Camera] Capturing at {send_fps} fps  (press Q to quit)")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[Camera] WARNING: Frame read failed — retrying…")
                await asyncio.sleep(0.1)
                continue

            snapshot, annotated = build_tracker_preview(frame, detector)
            await broadcast(build_tracker_message(snapshot))

            cv2.imshow("Pixel Defense — Camera View  [Q to quit]", annotated)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("[Camera] Quit signal received.")
                break

            await asyncio.sleep(interval)
    finally:
        release_camera(cap)
        cv2.destroyAllWindows()
        print("[Camera] Released.")


async def async_main():
    print("=" * 55)
    print("  Pixel Defense Live Tracker")
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
    print("[Server] Open http://localhost:5173 in your browser\n")

    await run_server(publish_live_tracker)


def main() -> int:
    asyncio.run(async_main())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
