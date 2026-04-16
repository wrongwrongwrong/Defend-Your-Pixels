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
import time

import cv2

from bridge.actions.model_action_dispatcher import apply_action
from bridge.adapters.board_state_message_adapter import build_board_state_message
from bridge.adapters.tracker_model_sync import build_tracker_move_actions
from bridge.adapters.tracker_message_adapter import build_tracker_message
from bridge.transport.websocket_transport import WS_HOST, WS_PORT, broadcast, drain_actions, run_server
from model_backend.game import PlayerId
from model_backend.scenarios import build_react_integration_level
from model_backend.serialization import serialize_game_state
from python_tracker.camera.camera_runtime import configure_camera, open_camera, release_camera
from python_tracker.marker_detection.aruco_detector import create_detector
from python_tracker.state_output.tracker_snapshot import (
    CONFIRM_PLAYER_MAP,
    annotate_tracker_preview,
    apply_calibration_fallback,
    build_tracker_preview,
)


CAMERA_ID = 0
SEND_FPS = 10
CONFIRM_HOLD_SECONDS = 5.0

_CONFIRM_PLAYER_ID = {mid: PlayerId.P1 if pnum == 1 else PlayerId.P2
                      for mid, pnum in CONFIRM_PLAYER_MAP.items()}


def _snapshot_has_detected_markers(snapshot: dict) -> bool:
    return bool(snapshot.get("markers")) or bool(snapshot.get("board_corners"))


def _merge_unit_metadata(
    cached_metadata: dict[str, dict], current_metadata: dict[str, dict]
) -> dict[str, dict]:
    merged_metadata = dict(cached_metadata)
    merged_metadata.update(current_metadata)
    return merged_metadata


class ConfirmMarkerTimer:
    """Track how long each confirmation marker has been continuously visible."""

    def __init__(self, hold_seconds: float = CONFIRM_HOLD_SECONDS):
        self.hold_seconds = hold_seconds
        self._first_seen: dict[int, float] = {}

    def check(self, game, snapshot: dict) -> bool:
        """Return True if a confirm marker triggered end_turn this frame."""
        detected = {m["id"] for m in snapshot.get("confirm_markers", [])}
        now = time.monotonic()

        for mid in list(self._first_seen):
            if mid not in detected:
                del self._first_seen[mid]

        for mid in detected:
            player = _CONFIRM_PLAYER_ID.get(mid)
            if player is None:
                continue
            if mid not in self._first_seen:
                self._first_seen[mid] = now
                pname = "P1" if player == PlayerId.P1 else "P2"
                game.last_action = f"{pname} confirm marker detected — hold {self.hold_seconds:.0f}s to end turn"
                continue

            elapsed = now - self._first_seen[mid]
            if elapsed >= self.hold_seconds and player == game.active_player and not game.game_over:
                apply_action(game, {"action": "end_turn"})
                del self._first_seen[mid]
                return True

        return False

    def seconds_held(self, marker_id: int) -> float:
        start = self._first_seen.get(marker_id)
        if start is None:
            return 0.0
        return time.monotonic() - start


async def publish_live_tracker(camera_id: int = CAMERA_ID, send_fps: int = SEND_FPS):
    # This coroutine owns the live loop. Everything else is an adapter/helper.
    cap = open_camera(camera_id)
    if cap is None:
        print(f"[Camera] ERROR: Cannot open camera (index {camera_id})")
        return

    game = build_react_integration_level()
    confirm_timer = ConfirmMarkerTimer()

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

            # First apply any explicit UI actions that arrived over WebSocket.
            for action in await drain_actions():
                apply_action(game, action)

            # Then derive tracker telemetry from the camera frame.
            snapshot, annotated = build_tracker_preview(frame, detector)
            if snapshot.get("calibration_ready"):
                last_calibrated_snapshot = snapshot
            effective_snapshot = apply_calibration_fallback(snapshot, last_calibrated_snapshot)

            annotated = annotate_tracker_preview(frame.copy(), effective_snapshot)
            # Tracker movement remains advisory; the model still validates every action.
            tracker_actions, current_unit_metadata = build_tracker_move_actions(game, effective_snapshot)
            last_unit_metadata = _merge_unit_metadata(last_unit_metadata, current_unit_metadata)

            if _snapshot_has_detected_markers(effective_snapshot):
                last_visible_snapshot = effective_snapshot

            # Prefer the last visible tracker snapshot so short dropouts do not cause
            # the frontend markers to flicker off immediately.
            snapshot_for_ui = last_visible_snapshot or effective_snapshot

            confirm_timer.check(game, effective_snapshot)

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
    print()
    print(f"  Confirm markers (hold {CONFIRM_HOLD_SECONDS:.0f}s to end turn):")
    print("    ID 13=P1 CONFIRM")
    print("    ID 17=P2 CONFIRM")
    print()
    print("[Server] Open http://localhost:5173 in your browser\n")

    await run_server(publish_live_tracker)


def main() -> int:
    asyncio.run(async_main())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
