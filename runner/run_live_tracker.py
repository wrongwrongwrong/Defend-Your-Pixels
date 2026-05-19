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
from python_tracker.tracked_markers import CONFIRM_MARKERS, HELP_MARKERS, HQ_MARKERS, NUKE_MARKERS, TOKEN_MARKERS, TURN_MARKERS
from runner.setup_flow import FIRST_PLAYER_SIDE_TO_PLAYER, PHASE_GAME, PHASE_HQ_PLACEMENT, PLAYERS, SetupState, dedupe_errors, is_valid_hq_position, make_error, new_side_state, sanitize_token_states, side_of_cell
from live_rules import game_model, terrain_gen, tutorial
from runner.frontend_static_server import start_frontend_http_server
from runner.port_check import DEFAULT_HTTP_PORT, ensure_ports_available
>>>>>>> Stashed changes


CAMERA_ID = 0
SEND_FPS = 10
<<<<<<< Updated upstream
CONFIRM_HOLD_SECONDS = 5.0
=======
HTTP_PORT = DEFAULT_HTTP_PORT
HEADLESS = os.environ.get("DYP_HEADLESS", "").strip().lower() in ("1", "true", "yes", "on")
SETUP_MARKER_STABLE_SECONDS = 0.35
FRONTEND_DIR = ROOT_DIR / "frontend"
PHASE_MODE_SELECT = "mode_select"
MODE_NORMAL = "normal"
MODE_TUTORIAL = "tutorial"
>>>>>>> Stashed changes

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

<<<<<<< Updated upstream
        for mid in detected:
            player = _CONFIRM_PLAYER_ID.get(mid)
            if player is None:
=======
        if self.session.setup.phase == PHASE_GAME:
            active_side = self.session.battle_active_side or self.session.battle_waiting_for_side or "p1"
            if active_side != self._battle_side:
                self._battle_side = active_side
                self._battle_since = now
            elapsed = now - self._battle_since
            turn = 1 if active_side == "p1" else 2
            if self.session.battle_active_side in PLAYERS:
                confirm_present = self._pulse(1.0, 0.35, elapsed)
            return self.p1_tokens, self.p2_tokens, turn, hq_markers, confirm_present, help_present

        return self.p1_tokens, self.p2_tokens, turn, hq_markers, confirm_present, help_present


def _confirm_marker_present(snapshot: dict) -> bool:
    confirm_markers = [
        marker
        for marker in snapshot.get("confirm_markers", [])
        if isinstance(marker, dict) and int(marker.get("id", -1)) == 4 and not marker.get("stale", False)
    ]
    return bool(confirm_markers)


def _help_marker_present(snapshot: dict) -> bool:
    help_markers = [
        marker
        for marker in snapshot.get("help_markers", [])
        if isinstance(marker, dict) and int(marker.get("id", -1)) == 5 and not marker.get("stale", False)
    ]
    return bool(help_markers)


def _turn_from_markers(snapshot: dict) -> int | None:
    turn_markers = [
        marker
        for marker in snapshot.get("turn_markers", [])
        if isinstance(marker, dict) and marker.get("id") in TURN_BY_MARKER_ID and not marker.get("stale", False)
    ]

    if len(turn_markers) == 1:
        return TURN_BY_MARKER_ID[int(turn_markers[0]["id"])]
    return None


def _turn_angle(snapshot: dict) -> float | None:
    turn_markers = [
        marker
        for marker in snapshot.get("turn_markers", [])
        if isinstance(marker, dict) and isinstance(marker.get("rotation"), (int, float))
    ]
    active_turn_markers = [marker for marker in turn_markers if not marker.get("stale", False)]

    if len(active_turn_markers) == 1:
        return round(float(active_turn_markers[0]["rotation"]), 1)
    if len(turn_markers) == 1:
        return round(float(turn_markers[0]["rotation"]), 1)
    return None


def _build_token_state(snapshot: dict) -> tuple[dict, dict, int | None, dict, bool, bool]:
    p1 = new_side_state()
    p2 = new_side_state()
    hq_markers = _new_hq_marker_state()

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

    for marker in snapshot.get("hq_markers", []):
        side = HQ_BY_MARKER_ID.get(marker.get("id"))
        if side is None:
            continue

        position = marker.get("position") if isinstance(marker.get("position"), dict) else None
        hq_markers[side] = {
            "col": _grid_index(position.get("x")) if position else None,
            "row": _grid_index(position.get("y")) if position else None,
            "stale": bool(marker.get("stale", False)),
        }

    return p1, p2, _turn_from_markers(snapshot), hq_markers, _confirm_marker_present(snapshot), _help_marker_present(snapshot)


def _nuke_markers(snapshot: dict) -> list[dict]:
    return [
        marker
        for marker in snapshot.get("nuke_markers", [])
        if isinstance(marker, dict) and int(marker.get("id", -1)) in NUKE_BY_MARKER_ID and not marker.get("stale", False)
    ]


class Session:
    def __init__(self):
        self.setup = SetupState()
        self.selected_mode: str | None = None
        self.tutorial_ctrl: tutorial.TutorialController | None = None
        self.tutorial_state: dict | None = None
        self.board_scan_ready = False
        self.reset(board_scan_ready=False)

    def reset(self, *, board_scan_ready: bool) -> None:
        self.board_scan_ready = bool(board_scan_ready)
        if self.selected_mode == MODE_TUTORIAL:
            self.seed = tutorial.TUTORIAL_SEED
            self.tutorial_ctrl = tutorial.new_tutorial()
        else:
            self.seed = int(time.time() * 1000) % (2**31)
            self.tutorial_ctrl = None
        self.tutorial_state = None
        self.terrain = terrain_gen.generate(seed=self.seed)
        self.accepted_p1 = new_side_state()
        self.accepted_p2 = new_side_state()
        self.hq_markers = _new_hq_marker_state()
        self.turn: int | None = None
        self.help_visible = False
        self.model: game_model.GameModel | None = None
        self.pending_events: list[dict] = []
        self._reset_setup_tracking()
        self._reset_battle_tracking()
        self.setup.reset(board_scan_ready=self.board_scan_ready)
        mode_tag = f" mode={self.selected_mode}" if self.selected_mode else ""
        print(f"[MAP] New game (seed={self.seed}{mode_tag})")

    def select_mode(self, mode: str, *, board_scan_ready: bool) -> bool:
        if self.selected_mode is not None or mode not in {MODE_NORMAL, MODE_TUTORIAL}:
            return False
        self.selected_mode = mode
        self.reset(board_scan_ready=board_scan_ready)
        print(f"[MODE] Selected {mode}")
        return True

    def _finish_tutorial_mode(self) -> None:
        if self.selected_mode != MODE_TUTORIAL:
            return
        self.selected_mode = MODE_NORMAL
        self.tutorial_ctrl = None
        self.tutorial_state = None
        print("[MODE] Tutorial complete. Continuing in normal game mode.")

    def _reset_setup_tracking(self) -> None:
        self._observed_turn_side: str | None = None
        self._observed_turn_since = 0.0
        self._debounced_turn_side: str | None = None
        self._observed_hq_cells = {side: None for side in PLAYERS}
        self._observed_hq_cell_since = {side: 0.0 for side in PLAYERS}
        self._stable_hq_cells = {side: None for side in PLAYERS}
        self._observed_confirm_present = False
        self._observed_confirm_since = 0.0
        self._stable_confirm_present = False
        self._confirm_consumed = False

    def _reset_battle_tracking(self) -> None:
        self.battle_active_side: str | None = None
        self.battle_waiting_for_side: str | None = None
        self._pending_nuke_cell: dict[str, tuple[int, int] | None] = {side: None for side in PLAYERS}

    def _pending_nuke_payload(self, side: str | None) -> dict | None:
        if side not in PLAYERS:
            return None
        cell = self._pending_nuke_cell.get(side)
        if cell is None:
            return None
        return {
            "side": side,
            "col": cell[0],
            "row": cell[1],
            "marker_id": 19 if side == "p1" else 29,
        }

    def _battle_payload(self) -> dict:
        if self.setup.phase != PHASE_GAME:
            return {
                "active_side": None,
                "waiting_for_side": None,
                "status_code": "inactive",
                "status_message": "Battle flow inactive until HQ setup completes.",
            }

        if self.battle_active_side in PLAYERS:
            marker_id = 10 if self.battle_active_side == "p1" else 20
            confirm_id = 4
            return {
                "active_side": self.battle_active_side,
                "waiting_for_side": None,
                "status_code": "positioning",
                "status_message": f"{self.battle_active_side.upper()} positioning active. Arrange that side's tokens, then scan ID{confirm_id} to attack.",
                "turn_marker_id": marker_id,
                "confirm_marker_id": confirm_id,
                "pending_nuke": self._pending_nuke_payload(self.battle_active_side),
            }

        waiting_side = self.battle_waiting_for_side
        if waiting_side in PLAYERS:
            marker_id = 10 if waiting_side == "p1" else 20
            side_name = "Old Mick" if waiting_side == "p1" else "The Mob"
            return {
                "active_side": None,
                "waiting_for_side": waiting_side,
                "status_code": "waiting_for_turn_marker",
                "status_message": f"Waiting for {side_name}. Scan ID{marker_id} to begin that side's turn.",
                "turn_marker_id": marker_id,
                "confirm_marker_id": 4,
            }

        return {
            "active_side": None,
            "waiting_for_side": None,
            "status_code": "waiting_for_first_turn_marker",
            "status_message": "Scan ID10 or ID20 to begin the first battle turn.",
            "confirm_marker_id": 4,
        }

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

        if action_name == "select_mode":
            mode = command.get("mode")
            if isinstance(mode, str):
                self.select_mode(mode, board_scan_ready=board_scan_ready)
            return errors

        if action_name == "tutorial_dismiss":
            if self.tutorial_ctrl is not None:
                self.tutorial_ctrl.dismiss()
                if self.tutorial_ctrl.finished:
                    self._finish_tutorial_mode()
            return errors
        
        if action_name == "tutorial_undo":
            if self.tutorial_ctrl is not None:
                self.tutorial_ctrl.undo()
            return errors

        if action_name in {"choose_side", "set_hq_candidate", "confirm_hq", "reset_setup", "cancel_hq"}:
            # Live tracker setup is marker-driven only: ID10/ID20 choose the active
            # setup side, ID11/ID21 position HQs, and ID4 confirms.
            return errors

        if action_name == "trigger_nuke":
            if self.setup.phase != PHASE_GAME or self.model is None or self.battle_active_side not in PLAYERS:
                return errors
            side = command.get("side")
            position = command.get("position") if isinstance(command.get("position"), dict) else None
            active_side = self.battle_active_side
            if side != active_side or not isinstance(position, dict):
                return errors
            col = position.get("x")
            row = position.get("y")
            if not isinstance(col, int) or not isinstance(row, int):
                return errors
            enemy_side = _opponent_side(active_side)
            if enemy_side is None or side_of_cell(col, row) != enemy_side:
                return errors
            snapshot = self.model.snapshot()
            if not snapshot.get(f"nuke_available_{active_side}", False):
                return errors
            self._pending_nuke_cell[active_side] = (col, row)
            return errors

        return errors

    def sync_scan_state(self, board_scan_ready: bool) -> None:
        self.board_scan_ready = bool(board_scan_ready)
        if not board_scan_ready and self.setup.phase != PHASE_GAME:
            self._reset_setup_tracking()
        self.setup.set_board_scan_ready(board_scan_ready)

    def update_tokens(self, raw_p1: dict, raw_p2: dict, turn: int | None, hq_markers: dict, confirm_present: bool, help_present: bool, nuke_markers: list[dict] | None = None) -> list[dict]:
        self.hq_markers = hq_markers
        self.help_visible = help_present
        active_side = None
        if self.setup.phase == PHASE_GAME:
            self._update_marker_driven_battle_flow(turn, confirm_present)
            active_side = self.battle_active_side

        if self.setup.phase == PHASE_GAME and active_side not in PLAYERS:
            raw_p1 = self.accepted_p1
            raw_p2 = self.accepted_p2

        self.accepted_p1, self.accepted_p2, errors = sanitize_token_states(
            raw_p1,
            raw_p2,
            self.accepted_p1,
            self.accepted_p2,
            active_side=active_side,
            require_full_detection=self.setup.phase in {PHASE_HQ_PLACEMENT, PHASE_GAME},
        )
        if self.setup.phase == PHASE_HQ_PLACEMENT:
            self._update_marker_driven_hq_setup(turn, hq_markers, confirm_present)
        if self.setup.phase == PHASE_GAME:
            self.turn = 1 if self.battle_active_side == "p1" else 2 if self.battle_active_side == "p2" else None
        elif self.setup.phase == PHASE_HQ_PLACEMENT and self.setup.active_setup_side in PLAYERS:
            self.turn = 1 if self.setup.active_setup_side == "p1" else 2
        else:
            self.turn = None
        self._update_marker_driven_nukes(nuke_markers or [])
        if self.tutorial_ctrl is not None:
            self.tutorial_state = self.tutorial_ctrl.tick(self.accepted_p1, self.accepted_p2, self.turn, self.hq_markers, confirm_present)
            if self.tutorial_ctrl.finished:
                self._finish_tutorial_mode()
        return errors

    def _update_marker_driven_nukes(self, nuke_markers: list[dict]) -> None:
        if self.setup.phase != PHASE_GAME or self.model is None:
            return

        active_side = self.battle_active_side
        if active_side not in PLAYERS:
            return

        pending_set = False
        for marker in nuke_markers:
            marker_id = int(marker.get("id", -1))
            side = NUKE_BY_MARKER_ID.get(marker_id)
            if side is None or side != active_side:
>>>>>>> Stashed changes
                continue
            if mid not in self._first_seen:
                self._first_seen[mid] = now
                pname = "P1" if player == PlayerId.P1 else "P2"
                game.last_action = f"{pname} confirm marker detected — hold {self.hold_seconds:.0f}s to end turn"
                continue
<<<<<<< Updated upstream

            elapsed = now - self._first_seen[mid]
            if elapsed >= self.hold_seconds and player == game.active_player and not game.game_over:
                apply_action(game, {"action": "end_turn"})
                del self._first_seen[mid]
                return True
=======
            col = _grid_index(position.get("x"))
            row = _grid_index(position.get("y"))
            enemy_side = _opponent_side(side)
            if col is None or row is None or side_of_cell(col, row) != enemy_side:
                self._pending_nuke_cell[active_side] = None
                continue
            snapshot = self.model.snapshot()
            if not snapshot.get(f"nuke_available_{side}", False):
                self._pending_nuke_cell[active_side] = None
                continue
            self._pending_nuke_cell[active_side] = (col, row)
            pending_set = True

        if not pending_set:
            self._pending_nuke_cell[active_side] = None
>>>>>>> Stashed changes

        return False

    def seconds_held(self, marker_id: int) -> float:
        start = self._first_seen.get(marker_id)
        if start is None:
            return 0.0
        return time.monotonic() - start


<<<<<<< Updated upstream
async def publish_live_tracker(camera_id: int = CAMERA_ID, send_fps: int = SEND_FPS):
    # This coroutine owns the live loop. Everything else is an adapter/helper.
=======
def _process_camera_frame(
    frame,
    detector,
    last_visible_snapshot: dict | None,
    last_calibrated_snapshot: dict | None,
) -> tuple[dict, dict | None, dict | None]:
    """Blocking ArUco + snapshot work (run via asyncio.to_thread)."""
    snapshot, _ = build_tracker_preview(frame, detector)
    if snapshot.get("calibration_ready"):
        last_calibrated_snapshot = snapshot
    effective_snapshot = apply_calibration_fallback(snapshot, last_calibrated_snapshot)

    if _snapshot_has_detected_markers(effective_snapshot):
        last_visible_snapshot = _merge_visible_snapshot(last_visible_snapshot, effective_snapshot)

    snapshot_for_ui = last_visible_snapshot or effective_snapshot
    return snapshot_for_ui, last_visible_snapshot, last_calibrated_snapshot


async def publish_live_tracker(camera_id: int = DEFAULT_CAMERA_ID, send_fps: int = SEND_FPS):
    session = Session()
    interval = 1.0 / send_fps
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
            game.advance_timers()

            ret, frame = cap.read()
=======
            tick_started = time.perf_counter()
            ret, frame = await asyncio.to_thread(cap.read)
>>>>>>> Stashed changes
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
=======
            snapshot_for_ui, last_visible_snapshot, last_calibrated_snapshot = await asyncio.to_thread(
                _process_camera_frame,
                frame,
                detector,
                last_visible_snapshot,
                last_calibrated_snapshot,
            )
            board_scan_ready = bool(snapshot_for_ui.get("calibration_ready"))
            turn_angle = _turn_angle(snapshot_for_ui)
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

<<<<<<< Updated upstream
            cv2.imshow("Old Mick MVP — Camera View  [Q to quit]", annotated)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                print("[Camera] Quit signal received.")
                break
=======
            if not HEADLESS:
                annotated = await asyncio.to_thread(annotate_tracker_preview, frame.copy(), snapshot_for_ui)
                cv2.imshow("Old Mick MVP - Camera View  [Q to quit]", annotated)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), ord("Q"), 27):
                    print("[Camera] Quit signal received.")
                    break
>>>>>>> Stashed changes

            elapsed = time.perf_counter() - tick_started
            if elapsed > interval * 0.85:
                print(
                    f"[Camera] Slow tick {elapsed * 1000:.0f}ms "
                    f"(budget {interval * 1000:.0f}ms) — WS heartbeat may lag"
                )

            await asyncio.sleep(interval)
    finally:
        release_camera(cap)
        cv2.destroyAllWindows()
        print("[Camera] Released.")


<<<<<<< Updated upstream
async def async_main():
    print("=" * 55)
    print("  Old Mick MVP Live Tracker")
    print(f"  ws://{WS_HOST}:{WS_PORT}")
=======
async def publish_no_camera(send_fps: int = SEND_FPS):
    session = Session()
    simulation = NoCameraSimulation(session)
    interval = 1.0 / send_fps

    print(f"[Runtime] --no-camera active at {send_fps} fps")

    while True:
        session.sync_scan_state(board_scan_ready=True)
        frame_errors: list[dict] = []

        for command in await drain_actions():
            frame_errors.extend(session.apply_command(command, board_scan_ready=True))

        raw_p1, raw_p2, turn, hq_markers, confirm_present, help_present = simulation.step()
        frame_errors.extend(session.update_tokens(raw_p1, raw_p2, turn, hq_markers, confirm_present, help_present, []))

        events = session.game_events()
        payload = session.payload(
            corners_found=4,
            turn_angle=0.0 if turn == 1 else 180.0 if turn == 2 else None,
            errors=frame_errors,
            events=events,
        )
        await broadcast(json.dumps(payload))
        await asyncio.sleep(interval)


async def async_main(args: argparse.Namespace):
    if not FRONTEND_DIR.is_dir():
        raise RuntimeError(f"Missing frontend directory: {FRONTEND_DIR}")

    ensure_ports_available(
        http_port=args.http_port,
        ws_port=args.ws_port,
        ws_host=WS_HOST,
        runtime_name="Live tracker",
    )
    start_frontend_http_server(args.http_port, FRONTEND_DIR, ROOT_DIR / "protocol")

    print("=" * 55)
    print("  Old Mick Live Tracker")
    print(f"  ws://{WS_HOST}:{args.ws_port}")
    print(f"  http://localhost:{args.http_port}?ws_port={args.ws_port}")
>>>>>>> Stashed changes
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
