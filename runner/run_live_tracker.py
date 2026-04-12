"""Live runtime entrypoint: camera -> tracker -> model -> WebSocket -> React UI.

This module wires the full local dev loop together:
- capture frames from an OpenCV camera
- detect ArUco markers and build a tracker snapshot (telemetry)
- translate tracker state into *proposed* move actions (tracker is not authoritative)
- apply actions and update the authoritative `model_backend` game state
- broadcast board_state + tracker_frame JSON to all connected WebSocket clients

Run:
- `python3 runner/run_live_tracker.py`
"""

import asyncio

import cv2

from bridge.actions.model_action_dispatcher import apply_action
from bridge.adapters.board_state_message_adapter import build_board_state_message
from bridge.adapters.tracker_model_sync import build_tracker_move_actions
from bridge.adapters.tracker_message_adapter import build_tracker_message
from bridge.transport.websocket_transport import WS_HOST, WS_PORT, broadcast, drain_actions, run_server
from model_backend.scenarios import build_react_integration_level
from model_backend.serialization import serialize_game_state
from python_tracker.camera.camera_runtime import configure_camera, open_camera, release_camera
from python_tracker.marker_detection.aruco_detector import create_detector
from python_tracker.state_output.tracker_snapshot import (
    annotate_tracker_preview,
    apply_calibration_fallback,
    build_tracker_preview,
)


CAMERA_ID = 1
SEND_FPS = 10


def _snapshot_has_detected_markers(snapshot: dict) -> bool:
    return bool(snapshot.get("markers")) or bool(snapshot.get("board_corners"))


def _merge_unit_metadata(
    cached_metadata: dict[str, dict], current_metadata: dict[str, dict]
) -> dict[str, dict]:
    merged_metadata = dict(cached_metadata)
    merged_metadata.update(current_metadata)
    return merged_metadata


async def publish_live_tracker(camera_id: int = CAMERA_ID, send_fps: int = SEND_FPS):
    cap = open_camera(camera_id)
    if cap is None:
        print(f"[Camera] ERROR: Cannot open camera (index {camera_id})")
        return

    game = build_react_integration_level()

    configure_camera(cap)
    detector = create_detector()
    interval = 1.0 / send_fps
    last_visible_snapshot: dict | None = None
    last_calibrated_snapshot: dict | None = None
    last_unit_metadata: dict[str, dict] = {}

    print(f"[Camera] Capturing at {send_fps} fps  (press Q to quit)")

    try:
        while True:
            game.advance_timers()

            ret, frame = cap.read()
            if not ret:
                print("[Camera] WARNING: Frame read failed — retrying…")
                await asyncio.sleep(0.1)
                continue

            for action in await drain_actions():
                apply_action(game, action)

            snapshot, annotated = build_tracker_preview(frame, detector)
            if snapshot.get("calibration_ready"):
                last_calibrated_snapshot = snapshot
            effective_snapshot = apply_calibration_fallback(snapshot, last_calibrated_snapshot)

            annotated = annotate_tracker_preview(frame.copy(), effective_snapshot)
            tracker_actions, current_unit_metadata = build_tracker_move_actions(game, effective_snapshot)
            last_unit_metadata = _merge_unit_metadata(last_unit_metadata, current_unit_metadata)

            if _snapshot_has_detected_markers(effective_snapshot):
                last_visible_snapshot = effective_snapshot

            snapshot_for_ui = last_visible_snapshot or effective_snapshot

            if not effective_snapshot.get("calibration_ready"):
                game.last_action = "Tracker waiting for board calibration"
            elif game.move_countdown_active:
                pass
            elif tracker_actions:
                moved_units = []
                for action in tracker_actions:
                    if apply_action(game, action):
                        position = action["position"]
                        moved_units.append(f"{action['unit_id']}->({position['x']},{position['y']})")
                if moved_units:
                    game.last_action = f"Tracker move intents: {', '.join(moved_units)}"

            game.advance_timers()

            # Keep the last stable tracker-derived board state visible during
            # short marker dropouts instead of clearing the UI immediately.
            await broadcast(build_board_state_message(serialize_game_state(game, last_unit_metadata)))
            await broadcast(build_tracker_message(snapshot_for_ui))

            cv2.imshow("Pixel Defense — Camera View  [Q to quit]", annotated)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
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
    print("    ID 10=P1 ATK")
    print("    ID 14=P2 ATK")
    print("    Other token IDs are currently disabled for this prototype")
    print()
    print("[Server] Open http://localhost:5173 in your browser\n")

    await run_server(publish_live_tracker)


def main() -> int:
    asyncio.run(async_main())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
