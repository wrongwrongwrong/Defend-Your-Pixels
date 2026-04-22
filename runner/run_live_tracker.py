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
<<<<<<< Updated upstream
from python_tracker.state_output.tracker_snapshot import (
    CONFIRM_PLAYER_MAP,
    annotate_tracker_preview,
    apply_calibration_fallback,
    build_tracker_preview,
)
=======
from python_tracker.state_output.tracker_snapshot import annotate_tracker_preview, apply_calibration_fallback, build_tracker_preview
from python_tracker.tracked_markers import TOKEN_MARKERS, TURN_MARKER_ID
from runner.setup_flow import PHASE_GAME, PHASE_HQ_PLACEMENT, PLAYERS, SetupState, make_error, new_side_state, sanitize_token_states
from yu_test1 import game_model, terrain_gen
>>>>>>> Stashed changes


CAMERA_ID = 0
SEND_FPS = 10
CONFIRM_HOLD_SECONDS = 5.0

_CONFIRM_PLAYER_ID = {mid: PlayerId.P1 if pnum == 1 else PlayerId.P2
                      for mid, pnum in CONFIRM_PLAYER_MAP.items()}


def _snapshot_has_detected_markers(snapshot: dict) -> bool:
    return bool(snapshot.get("markers")) or bool(snapshot.get("board_corners"))


<<<<<<< Updated upstream
def _merge_unit_metadata(
    cached_metadata: dict[str, dict], current_metadata: dict[str, dict]
) -> dict[str, dict]:
    merged_metadata = dict(cached_metadata)
    merged_metadata.update(current_metadata)
    return merged_metadata
=======
def _merge_visible_snapshot(cached_snapshot: dict | None, current_snapshot: dict) -> dict:
    if cached_snapshot is None:
        if current_snapshot.get("markers"):
            current_snapshot = {
                **current_snapshot,
                "markers": [{**marker, "stale": False} for marker in current_snapshot.get("markers", [])],
            }
        turn_marker = current_snapshot.get("turn_marker")
        if isinstance(turn_marker, dict):
            current_snapshot["turn_marker"] = {**turn_marker, "stale": False}
        return current_snapshot

    merged_markers: dict[int, dict] = {
        int(marker["id"]): {**marker, "stale": True}
        for marker in cached_snapshot.get("markers", [])
        if isinstance(marker, dict) and isinstance(marker.get("id"), int)
    }
    for marker in current_snapshot.get("markers", []):
        if isinstance(marker, dict) and isinstance(marker.get("id"), int):
            merged_markers[int(marker["id"])] = {**marker, "stale": False}

    current_turn_marker = current_snapshot.get("turn_marker")
    cached_turn_marker = cached_snapshot.get("turn_marker")
    turn_marker = None
    if isinstance(current_turn_marker, dict):
        turn_marker = {**current_turn_marker, "stale": False}
    elif isinstance(cached_turn_marker, dict):
        turn_marker = {**cached_turn_marker, "stale": True}

    return {
        **cached_snapshot,
        **current_snapshot,
        "markers": list(merged_markers.values()),
        "turn_marker": turn_marker,
        "board_corners": current_snapshot.get("board_corners") or cached_snapshot.get("board_corners", []),
        "playable_corners": current_snapshot.get("playable_corners") or cached_snapshot.get("playable_corners", []),
        "calibration_ready": bool(current_snapshot.get("calibration_ready") or cached_snapshot.get("calibration_ready")),
        "homography": current_snapshot.get("homography") if current_snapshot.get("homography") is not None else cached_snapshot.get("homography"),
    }
>>>>>>> Stashed changes


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

<<<<<<< Updated upstream
    def seconds_held(self, marker_id: int) -> float:
        start = self._first_seen.get(marker_id)
        if start is None:
            return 0.0
        return time.monotonic() - start


async def publish_live_tracker(camera_id: int = CAMERA_ID, send_fps: int = SEND_FPS):
    # This coroutine owns the live loop. Everything else is an adapter/helper.
=======

class Session:
    def __init__(self):
        self.setup = SetupState()
        self.accepted_p1 = new_side_state()
        self.accepted_p2 = new_side_state()
        self.turn: int | None = None
        self.model: game_model.GameModel | None = None
        self.reset(board_scan_ready=False)

    def reset(self, *, board_scan_ready: bool) -> None:
        self.seed = int(time.time() * 1000) % (2 ** 31)
        self.terrain = terrain_gen.generate(seed=self.seed)
        self.model = None
        self.turn = None
        self.setup.reset(board_scan_ready=board_scan_ready)
        print(f"[MAP] New game (seed={self.seed})")

    def apply_command(self, command: dict, *, board_scan_ready: bool) -> list[dict]:
        errors: list[dict] = []
        command_type = command.get("type")
        action_name = command.get("action")
        if command_type == "new_map":
            self.reset(board_scan_ready=board_scan_ready)
            return errors

        if command_type == "tier":
            if self.model is None:
                return errors
            try:
                player = int(command.get("player"))
                delta = int(command.get("delta"))
            except (TypeError, ValueError):
                return errors

            if player == 1:
                self.model.tier_p1 = max(1, min(4, self.model.tier_p1 + delta))
            elif player == 2:
                self.model.tier_p2 = max(1, min(4, self.model.tier_p2 + delta))
            return errors

        if action_name == "choose_side":
            first_player_side = command.get("first_player_side")
            if isinstance(first_player_side, str):
                self.setup.choose_side(first_player_side)
            return errors

        if action_name == "set_hq_candidate":
            side = command.get("side")
            position = command.get("position") if isinstance(command.get("position"), dict) else None
            if side in PLAYERS:
                error = self.setup.set_hq_candidate(side, position)
                if error is not None:
                    errors.append(error)
            return errors

        if action_name == "confirm_hq":
            side = command.get("side")
            if side in PLAYERS:
                game_ready, setup_event = self.setup.confirm_hq(side)
                if game_ready:
                    self._ensure_model_started()
                if setup_event is not None and setup_event["code"] != "hq_setup_complete":
                    errors.append(setup_event)
            return errors

        if action_name in {"reset_setup", "cancel_hq"}:
            self.model = None
            self.setup.reset_hq_setup()
            return errors

        return errors

    def sync_scan_state(self, board_scan_ready: bool) -> None:
        self.setup.set_board_scan_ready(board_scan_ready)

    def update_tokens(self, raw_p1: dict, raw_p2: dict, turn: int | None) -> list[dict]:
        self.turn = turn
        active_side = None
        if self.setup.phase == PHASE_GAME and turn in (1, 2):
            active_side = "p1" if turn == 1 else "p2"

        self.accepted_p1, self.accepted_p2, errors = sanitize_token_states(
            raw_p1,
            raw_p2,
            self.accepted_p1,
            self.accepted_p2,
            active_side=active_side,
            require_full_detection=self.setup.phase in {PHASE_HQ_PLACEMENT, PHASE_GAME},
        )
        return errors

    def game_events(self) -> list[dict]:
        if self.setup.phase != PHASE_GAME or self.model is None or self.turn not in (1, 2):
            return []
        return self.model.on_turn_change(self.turn, self.accepted_p1, self.accepted_p2)

    def payload(self, *, corners_found: int, turn_angle: float | None, errors: list[dict], events: list[dict]) -> dict:
        return {
            "phase": self.setup.phase,
            "corners_found": corners_found,
            "turn": self.turn,
            "turn_angle": turn_angle,
            "p1": self.accepted_p1,
            "p2": self.accepted_p2,
            "terrain": self.terrain,
            "map_seed": self.seed,
            "game": self.model.snapshot() if self.model is not None else {},
            "events": events,
            "setup": self.setup.public_payload(),
            "errors": _dedupe_errors(errors),
        }

    def _ensure_model_started(self) -> None:
        if self.model is not None:
            return
        hidden_hq_positions = self.setup.hidden_hq_positions()
        if hidden_hq_positions is None:
            return
        hq_p1, hq_p2 = hidden_hq_positions
        self.model = game_model.new_game(self.terrain, seed=self.seed, hq_p1=hq_p1, hq_p2=hq_p2)
        if self.turn in (1, 2):
            self.model.on_turn_change(self.turn, self.accepted_p1, self.accepted_p2)
        print("[MAP] HQ setup complete. Hidden HQs locked in.")


def _dedupe_errors(errors: list[dict]) -> list[dict]:
    deduped_errors: list[dict] = []
    seen_codes: set[str] = set()
    for error in errors:
        code = error.get("code")
        if not isinstance(code, str) or code in seen_codes:
            continue
        seen_codes.add(code)
        deduped_errors.append(error)
    return deduped_errors


def _build_token_state(snapshot: dict) -> tuple[dict, dict, int | None]:
    p1 = new_side_state()
    p2 = new_side_state()

    for marker in snapshot.get("markers", []):
        role = ROLE_BY_MARKER_ID.get(marker.get("id"))
        if role is None:
            continue

        side, slot = role
        target = p1 if side == "p1" else p2
        position = marker.get("position") if isinstance(marker.get("position"), dict) else None
        col = _grid_index(position.get("x")) if position else None
        row = _grid_index(position.get("y")) if position else None
        rotation = marker.get("rotation")

        target[slot] = {
            "col": col,
            "row": row,
            "angle": round(float(rotation), 1) if isinstance(rotation, (int, float)) else None,
            "direction": _snap_direction_8(float(rotation)) if isinstance(rotation, (int, float)) else None,
            "stale": bool(marker.get("stale", False)),
        }

    turn_marker = snapshot.get("turn_marker") if isinstance(snapshot.get("turn_marker"), dict) else None
    turn_rotation = turn_marker.get("rotation") if turn_marker else None
    turn = _turn_from_rotation(float(turn_rotation)) if isinstance(turn_rotation, (int, float)) else None
    return p1, p2, turn


async def publish_live_tracker(camera_id: int = CAMERA_ID, send_fps: int = SEND_FPS):
    session = Session()
>>>>>>> Stashed changes
    cap = open_camera(camera_id)
    if cap is None:
        print(f"[Camera] ERROR: Cannot open camera (index {camera_id})")
        interval = 1.0 / send_fps
        while True:
            frame_errors = [make_error("camera_unavailable")]
            for command in await drain_actions():
                frame_errors.extend(session.apply_command(command, board_scan_ready=False))
            await broadcast(json.dumps(session.payload(corners_found=0, turn_angle=None, errors=frame_errors, events=[])))
            await asyncio.sleep(interval)

<<<<<<< Updated upstream
    game = build_react_integration_level()
    confirm_timer = ConfirmMarkerTimer()

=======
>>>>>>> Stashed changes
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

<<<<<<< Updated upstream
            # First apply any explicit UI actions that arrived over WebSocket.
            for action in await drain_actions():
                apply_action(game, action)

            # Then derive tracker telemetry from the camera frame.
            snapshot, annotated = build_tracker_preview(frame, detector)
=======
            snapshot, _ = build_tracker_preview(frame, detector)
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
=======
            turn_angle = snapshot_for_ui.get("turn_marker", {}).get("rotation") if isinstance(snapshot_for_ui.get("turn_marker"), dict) else None
            board_scan_ready = bool(snapshot_for_ui.get("calibration_ready"))
            session.sync_scan_state(board_scan_ready)

            raw_p1, raw_p2, turn = _build_token_state(snapshot_for_ui)
            frame_errors: list[dict] = []
            if not board_scan_ready and session.setup.phase != PHASE_GAME:
                frame_errors.append(make_error("marker_map_scan_failed"))
            frame_errors.extend(session.update_tokens(raw_p1, raw_p2, turn))

            for command in await drain_actions():
                frame_errors.extend(session.apply_command(command, board_scan_ready=board_scan_ready))

            events = session.game_events()
            payload = session.payload(
                corners_found=len(snapshot_for_ui.get("board_corners", [])),
                turn_angle=turn_angle,
                errors=frame_errors,
                events=events,
            )
>>>>>>> Stashed changes

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

            cv2.imshow("Old Mick MVP — Camera View  [Q to quit]", annotated)
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
    print("  Old Mick MVP Live Tracker")
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
