"""Entry point. Run: python3 main.py [--no-camera] [--camera-index N] [--debug-window]"""

import asyncio
import argparse
import threading
import queue
import cv2


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--no-camera", action="store_true",
                   help="Run without camera (manual testing via frontend)")
    p.add_argument("--camera-index", type=int, default=0,
                   help="Camera device index (default 0)")
    p.add_argument("--debug-window", action="store_true",
                   help="Show OpenCV debug window (runs on main thread)")
    return p.parse_args()


def run_debug_window(frame_queue: queue.Queue, stop_event: threading.Event):
    """Must run on the main thread — macOS requires OpenCV GUI on main thread."""
    cv2.namedWindow("ArUco Debug", cv2.WINDOW_NORMAL)
    while not stop_event.is_set():
        try:
            frame = frame_queue.get(timeout=0.1)
            cv2.imshow("ArUco Debug", frame)
        except queue.Empty:
            pass
        if cv2.waitKey(1) & 0xFF == ord('q'):
            stop_event.set()
            break
    cv2.destroyAllWindows()


async def async_main(args, frame_queue):
    from ws_server import GameServer

    tracker = None
    if not args.no_camera:
        try:
            from camera_tracker import MarkerTracker
            tracker = MarkerTracker(camera_index=args.camera_index)
            print(f"Camera {args.camera_index} opened.")
        except Exception as e:
            print(f"Camera init failed: {e}. Running without camera.")

    server = GameServer(tracker=tracker, debug_frame_queue=frame_queue)
    await server.serve()


if __name__ == "__main__":
    args = parse_args()

    if args.debug_window and not args.no_camera:
        # OpenCV GUI must be on the main thread — run asyncio in background thread
        frame_queue = queue.Queue(maxsize=2)
        stop_event = threading.Event()

        def run_async():
            asyncio.run(async_main(args, frame_queue))

        t = threading.Thread(target=run_async, daemon=True)
        t.start()
        run_debug_window(frame_queue, stop_event)
    else:
        asyncio.run(async_main(args, None))
