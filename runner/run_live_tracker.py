"""Live runtime entrypoint: camera -> tracker -> yu_test1 rules -> WebSocket UI.

This runtime keeps the current `python_tracker` camera/grid-mapping pipeline, but the
authoritative gameplay loop and browser payload now follow `yu_test1`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
import sys
import cv2


from bridge.transport.websocket_transport import WS_HOST, WS_PORT, broadcast, drain_actions, run_server
from python_tracker.camera.camera_runtime import configure_camera, open_camera, release_camera
from python_tracker.marker_detection.aruco_detector import create_detector
from python_tracker.state_output.tracker_snapshot import annotate_tracker_preview, apply_calibration_fallback, build_tracker_preview
from python_tracker.tracked_markers import TOKEN_MARKERS, TURN_MARKER_ID
from runner.setup_flow import PHASE_GAME, PHASE_HQ_PLACEMENT, PLAYERS, SetupState, dedupe_errors, make_error, new_side_state, sanitize_token_states
from yu_test1 import game_model, terrain_gen


CAMERA_ID = 0 if sys.platform == "darwin" else 1
SEND_FPS = 10
HEADLESS = os.environ.get("DYP_HEADLESS", "").strip().lower() in ("1", "true", "yes", "on")

# Fixed seed for tutorial mode - ensures F6 is clear and no terrain blocks Mob's line of fire
TUTORIAL_SEED = 42
TUTORIAL_MODE = False  # Set via --tutorial command line flag

ROLE_BY_MARKER_ID = {
    10: ("p1", "atk_a"),
    11: ("p1", "atk_b"),
    12: ("p1", "def"),
    14: ("p2", "atk_a"),
    15: ("p2", "atk_b"),
    16: ("p2", "def"),
}

COMPASS_8 = [
    (0, "E"),
    (45, "SE"),
    (90, "S"),
    (135, "SW"),
    (180, "W"),
    (225, "NW"),
    (270, "N"),
    (315, "NE"),
]


def _snapshot_has_detected_markers(snapshot: dict) -> bool:
    return bool(snapshot.get("markers")) or bool(snapshot.get("board_corners")) or bool(snapshot.get("turn_marker"))


def _merge_visible_snapshot(cached_snapshot: dict | None, current_snapshot: dict) -> dict:
    if cached_snapshot is None:
        merged_snapshot = dict(current_snapshot)
        merged_snapshot["markers"] = [{**marker, "stale": False} for marker in current_snapshot.get("markers", [])]
        turn_marker = current_snapshot.get("turn_marker")
        if isinstance(turn_marker, dict):
            merged_snapshot["turn_marker"] = {**turn_marker, "stale": False}
        return merged_snapshot

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


def _angular_distance(angle: float, target: float) -> float:
    return abs((angle - target + 180.0) % 360.0 - 180.0)


def _snap_direction_8(angle: float | None) -> str | None:
    if angle is None:
        return None
    return min(COMPASS_8, key=lambda item: _angular_distance(angle, item[0]))[1]


def _turn_from_rotation(angle: float | None) -> int | None:
    if angle is None:
        return None
    if _angular_distance(angle, 0.0) <= 60.0:
        return 1
    if _angular_distance(angle, 180.0) <= 60.0:
        return 2
    return None


def _grid_index(value: float | int | None) -> int | None:
    if not isinstance(value, (int, float)):
        return None
    return max(0, min(11, int(round(float(value)))))


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


class Session:
    def __init__(self):
        self.setup = SetupState()
        self.reset(board_scan_ready=False)

    def reset(self, *, board_scan_ready: bool) -> None:
        if TUTORIAL_MODE:
            self.seed = TUTORIAL_SEED
        else:
            self.seed = int(time.time() * 1000) % (2**31)
        self.terrain = terrain_gen.generate(seed=self.seed)
        self.accepted_p1 = new_side_state()
        self.accepted_p2 = new_side_state()
        self.turn: int | None = None
        self.model: game_model.GameModel | None = None
        self.pending_events: list[dict] = []
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
                self.model.tier_p1 = max(0, min(4, self.model.tier_p1 + delta))
            elif player == 2:
                self.model.tier_p2 = max(0, min(4, self.model.tier_p2 + delta))
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
                error = self.setup.set_hq_candidate(side, position, self.terrain)
                if error is not None:
                    errors.append(error)
            return errors

        if action_name == "confirm_hq":
            side = command.get("side")
            if side in PLAYERS:
                game_ready, setup_event = self.setup.confirm_hq(side)
                if setup_event is not None:
                    errors.append(setup_event)
                if game_ready:
                    self._ensure_model_started()
            return errors

        if action_name in {"reset_setup", "cancel_hq"}:
            self.model = None
            self.setup.reset_hq_setup()
            return errors

        if action_name == "trigger_nuke":
            if self.setup.phase != PHASE_GAME or self.model is None or self.turn not in (1, 2):
                return errors
            side = command.get("side")
            position = command.get("position") if isinstance(command.get("position"), dict) else None
            active_side = "p1" if self.turn == 1 else "p2"
            if side != active_side or not isinstance(position, dict):
                return errors
            col = position.get("x")
            row = position.get("y")
            if not isinstance(col, int) or not isinstance(row, int):
                return errors
            self.pending_events.extend(self.model.trigger_nuke(active_side, (col, row)))
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
        events = self.pending_events
        self.pending_events = []
        if self.setup.phase != PHASE_GAME or self.model is None or self.turn not in (1, 2):
            return events
        return events + self.model.on_turn_change(self.turn, self.accepted_p1, self.accepted_p2)

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
            "errors": dedupe_errors(errors),
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


async def publish_live_tracker(camera_id: int = CAMERA_ID, send_fps: int = SEND_FPS):
    session = Session()
    interval = 1.0 / send_fps
    cap = open_camera(camera_id)
    if cap is None:
        print(f"[Camera] ERROR: Cannot open camera (index {camera_id})")
        while True:
            frame_errors = [make_error("camera_unavailable")]
            for command in await drain_actions():
                frame_errors.extend(session.apply_command(command, board_scan_ready=False))
            await broadcast(json.dumps(session.payload(corners_found=0, turn_angle=None, errors=frame_errors, events=[])))
            await asyncio.sleep(interval)

    configure_camera(cap)
    detector = create_detector()
    last_visible_snapshot: dict | None = None
    last_calibrated_snapshot: dict | None = None

    print(f"[Camera] Capturing at {send_fps} fps  (press Q to quit)")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[Camera] WARNING: Frame read failed - retrying...")
                await asyncio.sleep(0.1)
                continue

            snapshot, _ = build_tracker_preview(frame, detector)
            if snapshot.get("calibration_ready"):
                last_calibrated_snapshot = snapshot
            effective_snapshot = apply_calibration_fallback(snapshot, last_calibrated_snapshot)

            if _snapshot_has_detected_markers(effective_snapshot):
                last_visible_snapshot = _merge_visible_snapshot(last_visible_snapshot, effective_snapshot)

            snapshot_for_ui = last_visible_snapshot or effective_snapshot
            board_scan_ready = bool(snapshot_for_ui.get("calibration_ready"))
            turn_angle = snapshot_for_ui.get("turn_marker", {}).get("rotation") if isinstance(snapshot_for_ui.get("turn_marker"), dict) else None

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
            await broadcast(json.dumps(payload))

            if not HEADLESS:
                annotated = annotate_tracker_preview(frame.copy(), snapshot_for_ui)
                cv2.imshow("Old Mick MVP - Camera View  [Q to quit]", annotated)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), ord("Q"), 27):
                    print("[Camera] Quit signal received.")
                    break

            await asyncio.sleep(interval)
    finally:
        release_camera(cap)
        if not HEADLESS:
            cv2.destroyAllWindows()
        print("[Camera] Released.")


async def async_main():
    print("=" * 55)
    print("  Old Mick Live Tracker")
    print(f"  ws://{WS_HOST}:{WS_PORT}")
    print("=" * 55)
    print()
    print("  Board corner markers (ArUco DICT_4X4_50):")
    print("    ID 0 = top-left     ID 1 = top-right")
    print("    ID 2 = bottom-left  ID 3 = bottom-right")
    print()
    print("  Token markers:")
    for marker in TOKEN_MARKERS:
        print(f"    ID {marker.id}=P{int(marker.player)} {marker.label}")
    print()
    print(f"  Turn marker:\n    ID {TURN_MARKER_ID}=TURN")
    print()
    print("[Server] Open yu_test1/index.html in your browser\n")

    await run_server(publish_live_tracker)


def main() -> int:
    global TUTORIAL_MODE
    parser = argparse.ArgumentParser(description="Old Mick Live Tracker")
    parser.add_argument("--tutorial", action="store_true", help="Run in tutorial mode with fixed map seed")
    args = parser.parse_args()
    
    if args.tutorial:
        TUTORIAL_MODE = True
        print("[Tutorial] Running in tutorial mode with fixed seed")
    
    asyncio.run(async_main())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
