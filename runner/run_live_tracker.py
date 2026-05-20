"""Live runtime entrypoint: camera -> tracker -> shared live rules -> WebSocket UI.

This runtime keeps the current `python_tracker` camera/grid-mapping pipeline, but the
authoritative gameplay loop and browser payload now follow the shared live rules.
"""

from __future__ import annotations

import argparse
import asyncio
import functools
import json
import os
from pathlib import Path
import sys
import time

import cv2

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
for import_root in (ROOT_DIR, BACKEND_DIR):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from bridge.transport.websocket_transport import WS_HOST, WS_PORT, broadcast, drain_actions, run_server
from python_tracker.camera.camera_runtime import configure_camera, open_camera, release_camera
from python_tracker.marker_detection.aruco_detector import create_detector
from python_tracker.state_output.tracker_snapshot import annotate_tracker_preview, apply_calibration_fallback, build_tracker_preview
from python_tracker.tracked_markers import CONFIRM_MARKERS, HELP_MARKERS, HQ_MARKERS, NUKE_MARKERS, TOKEN_MARKERS, TURN_MARKERS
from runner.setup_flow import FIRST_PLAYER_SIDE_TO_PLAYER, PHASE_GAME, PHASE_HQ_PLACEMENT, PHASE_SCAN, PLAYERS, SetupState, dedupe_errors, is_valid_hq_position, make_error, new_side_state, sanitize_token_states, side_of_cell
from live_rules import game_model, terrain_gen, tutorial
from runner.frontend_static_server import start_frontend_http_server
from runner.port_check import DEFAULT_HTTP_PORT, ensure_ports_available


DEFAULT_CAMERA_ID = 0 if sys.platform == "darwin" else 1
SEND_FPS = 10
HTTP_PORT = DEFAULT_HTTP_PORT
HEADLESS = os.environ.get("DYP_HEADLESS", "").strip().lower() in ("1", "true", "yes", "on")
SETUP_MARKER_STABLE_SECONDS = 0.35
FRONTEND_DIR = ROOT_DIR / "frontend"
PHASE_MODE_SELECT = "mode_select"
MODE_NORMAL = "normal"
MODE_TUTORIAL = "tutorial"

_TUTORIAL_P1_BATTLE_STEPS = frozenset({
    "resume_p1_turn",
    "place_atk_a",
    "place_atk_b",
    "aim_atk_a",
    "explain_ray",
    "place_def",
    "explain_defense",
    "end_turn",
    "explain_upgrade_sidebar",
    "explain_nuke",
    "explain_nuke_launch",
})
_TUTORIAL_STEPS_ALLOW_BATTLE_CONFIRM = frozenset({"end_turn", "explain_nuke_launch"})
_TUTORIAL_P1_HQ_CELL = (1, 9)  # B10 — matches tutorial place_hq_p1 highlight

ROLE_BY_MARKER_ID = {
    12: ("p1", "atk_a"),
    13: ("p1", "atk_b"),
    14: ("p1", "def"),
    22: ("p2", "atk_a"),
    23: ("p2", "atk_b"),
    24: ("p2", "def"),
}
TURN_BY_MARKER_ID = {
    10: 1,
    20: 2,
}
HQ_BY_MARKER_ID = {
    11: "p1",
    21: "p2",
}
NUKE_BY_MARKER_ID = {
    19: "p1",
    29: "p2",
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Old Mick live tracker")
    parser.add_argument(
        "--camera-index",
        type=int,
        default=DEFAULT_CAMERA_ID,
        help="Camera index for the live tracker. (macOS default: 0, others: 1)",
    )
    parser.add_argument("--send-fps", type=int, default=SEND_FPS, help="Broadcast rate for frontend payloads.")
    parser.add_argument("--http-port", type=int, default=HTTP_PORT, help="HTTP port for the frontend.")
    parser.add_argument("--ws-port", type=int, default=WS_PORT, help="WebSocket port for frontend state sync.")
    parser.add_argument("--no-camera", action="store_true", help="Run the live frontend without opening a camera.")
    return parser.parse_args()


def _opponent_side(side: str | None) -> str | None:
    if side == "p1":
        return "p2"
    if side == "p2":
        return "p1"
    return None


def _snapshot_has_detected_markers(snapshot: dict) -> bool:
    return bool(snapshot.get("markers")) or bool(snapshot.get("hq_markers")) or bool(snapshot.get("nuke_markers")) or bool(snapshot.get("board_corners")) or bool(snapshot.get("turn_markers")) or bool(snapshot.get("confirm_markers")) or bool(snapshot.get("help_markers"))


def _merge_marker_collection(cached_markers: list[dict], current_markers: list[dict]) -> list[dict]:
    merged_markers: dict[int, dict] = {
        int(marker["id"]): {**marker, "stale": True}
        for marker in cached_markers
        if isinstance(marker, dict) and isinstance(marker.get("id"), int)
    }
    for marker in current_markers:
        if isinstance(marker, dict) and isinstance(marker.get("id"), int):
            merged_markers[int(marker["id"])] = {**marker, "stale": False}
    return list(merged_markers.values())


def _merge_visible_snapshot(cached_snapshot: dict | None, current_snapshot: dict) -> dict:
    if cached_snapshot is None:
        merged_snapshot = dict(current_snapshot)
        merged_snapshot["markers"] = [{**marker, "stale": False} for marker in current_snapshot.get("markers", [])]
        merged_snapshot["hq_markers"] = [{**marker, "stale": False} for marker in current_snapshot.get("hq_markers", [])]
        merged_snapshot["turn_markers"] = [{**marker, "stale": False} for marker in current_snapshot.get("turn_markers", [])]
        merged_snapshot["confirm_markers"] = [{**marker, "stale": False} for marker in current_snapshot.get("confirm_markers", [])]
        merged_snapshot["help_markers"] = [{**marker, "stale": False} for marker in current_snapshot.get("help_markers", [])]
        merged_snapshot["nuke_markers"] = [{**marker, "stale": False} for marker in current_snapshot.get("nuke_markers", [])]
        return merged_snapshot

    merged_markers = _merge_marker_collection(cached_snapshot.get("markers", []), current_snapshot.get("markers", []))
    merged_hq_markers = _merge_marker_collection(cached_snapshot.get("hq_markers", []), current_snapshot.get("hq_markers", []))
    merged_turn_markers = _merge_marker_collection(cached_snapshot.get("turn_markers", []), current_snapshot.get("turn_markers", []))
    merged_confirm_markers = _merge_marker_collection(cached_snapshot.get("confirm_markers", []), current_snapshot.get("confirm_markers", []))
    merged_help_markers = _merge_marker_collection(cached_snapshot.get("help_markers", []), current_snapshot.get("help_markers", []))
    merged_nuke_markers = _merge_marker_collection(cached_snapshot.get("nuke_markers", []), current_snapshot.get("nuke_markers", []))

    return {
        **cached_snapshot,
        **current_snapshot,
        "markers": merged_markers,
        "hq_markers": merged_hq_markers,
        "turn_markers": merged_turn_markers,
        "confirm_markers": merged_confirm_markers,
        "help_markers": merged_help_markers,
        "nuke_markers": merged_nuke_markers,
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


def _grid_index(value: float | int | None) -> int | None:
    if not isinstance(value, (int, float)):
        return None
    return max(0, min(11, int(round(float(value)))))


def _new_hq_marker_state(*, stale: bool = True) -> dict:
    return {
        "p1": {"col": None, "row": None, "stale": stale},
        "p2": {"col": None, "row": None, "stale": stale},
    }


def _demo_hq_cell(side: str, terrain: dict) -> tuple[int, int]:
    for row in range(12):
        for col in range(12):
            position = {"x": col, "y": row}
            if side_of_cell(col, row) == side and is_valid_hq_position(side, position, terrain):
                return col, row
    raise RuntimeError(f"Cannot find a simulated HQ cell for {side}")


def _demo_side_states() -> tuple[dict, dict]:
    p1 = new_side_state(stale=False)
    p2 = new_side_state(stale=False)
    p1["atk_a"] = {"col": 2, "row": 7, "angle": 0.0, "direction": "E", "stale": False}
    p1["atk_b"] = {"col": 4, "row": 6, "angle": 45.0, "direction": "SE", "stale": False}
    p1["def"] = {"col": 1, "row": 8, "angle": 90.0, "direction": None, "stale": False}
    p2["atk_a"] = {"col": 9, "row": 4, "angle": 180.0, "direction": "W", "stale": False}
    p2["atk_b"] = {"col": 8, "row": 6, "angle": 225.0, "direction": "NW", "stale": False}
    p2["def"] = {"col": 10, "row": 3, "angle": 270.0, "direction": None, "stale": False}
    return p1, p2


class NoCameraSimulation:
    def __init__(self, session: "Session"):
        self.session = session
        self.p1_tokens, self.p2_tokens = _demo_side_states()
        self._terrain_seed = session.seed
        self.hq_cells = self._build_hq_cells()
        self._setup_side: str | None = None
        self._setup_since = 0.0
        self._battle_side: str | None = None
        self._battle_since = 0.0

    def _build_hq_cells(self) -> dict[str, tuple[int, int]]:
        return {
            "p1": _demo_hq_cell("p1", self.session.terrain),
            "p2": _demo_hq_cell("p2", self.session.terrain),
        }

    def _pulse(self, start_after: float, duration: float, elapsed: float) -> bool:
        return start_after <= elapsed < start_after + duration

    def step(self) -> tuple[dict, dict, int | None, dict, bool, bool]:
        if self.session.seed != self._terrain_seed:
            self._terrain_seed = self.session.seed
            self.hq_cells = self._build_hq_cells()

        hq_markers = _new_hq_marker_state()
        turn: int | None = None
        confirm_present = False
        help_present = False
        now = time.monotonic()

        if self.session.setup.phase == PHASE_HQ_PLACEMENT:
            active_side = self.session.setup.active_setup_side
            if active_side != self._setup_side:
                self._setup_side = active_side
                self._setup_since = now
            if active_side in PLAYERS:
                elapsed = now - self._setup_since
                col, row = self.hq_cells[active_side]
                hq_markers[active_side] = {"col": col, "row": row, "stale": False}
                turn = 1 if active_side == "p1" else 2
                confirm_present = self._pulse(0.9, 0.35, elapsed)
            return self.p1_tokens, self.p2_tokens, turn, hq_markers, confirm_present, help_present

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
        self._tutorial_last_confirm = False
        self._tutorial_last_turn: int | None = None
        self._tutorial_fx_step_id: str | None = None
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
        self._tutorial_fx_step_id = None
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
        self._tutorial_fx_step_id = None
        print("[MODE] Tutorial complete. Continuing in normal game mode.")

    def _tutorial_step_id(self) -> str | None:
        if self.tutorial_state is None:
            return None
        step_id = self.tutorial_state.get("step_id")
        return step_id if isinstance(step_id, str) else None

    def _tutorial_is_battle_visual_step(self) -> bool:
        return (
            self.selected_mode == MODE_TUTORIAL
            and self._tutorial_step_id() in _TUTORIAL_P1_BATTLE_STEPS
        )

    def _tutorial_forces_p1_tokens(self) -> bool:
        return self._tutorial_is_battle_visual_step() and self.setup.phase == PHASE_GAME

    def _tutorial_suppress_battle_confirm(self) -> bool:
        if self.selected_mode != MODE_TUTORIAL:
            return False
        step_id = self._tutorial_step_id()
        if step_id is None or step_id not in _TUTORIAL_P1_BATTLE_STEPS:
            return False
        return step_id not in _TUTORIAL_STEPS_ALLOW_BATTLE_CONFIRM

    def _tutorial_positioning_side(self) -> str | None:
        if self.battle_active_side in PLAYERS:
            return self.battle_active_side
        if self._tutorial_forces_p1_tokens():
            return "p1"
        return None

    def _sync_tutorial_runner_effects(self) -> None:
        if self.tutorial_ctrl is None or self.tutorial_state is None:
            return

        step_id = self.tutorial_state.get("step_id")
        if step_id == self._tutorial_fx_step_id:
            self._apply_tutorial_battle_posture(step_id)
            return
        self._tutorial_fx_step_id = step_id

        effect = self.tutorial_state.get("runner_effect")
        if effect == "skip_p2_setup":
            self._tutorial_skip_p2_setup()
        elif effect == "p1_tier2" and self.model is not None:
            self.model.apply_tutorial_preset("p1_tier2")
        elif effect == "p1_nuke_unlock" and self.model is not None:
            self.model.apply_tutorial_preset("p1_nuke_unlock")

        self._apply_tutorial_battle_posture(step_id)

    def _tutorial_ensure_game_started(self) -> None:
        if self.setup.phase == PHASE_GAME and self.model is not None:
            return

        if not self.setup.board_scan_ready:
            self.board_scan_ready = True
            self.setup.set_board_scan_ready(True)
        if self.setup.phase == PHASE_SCAN:
            self.setup.phase = PHASE_HQ_PLACEMENT
        if self.setup.first_player_side is None:
            self.setup.first_player_side = "old_mick"

        if not self.setup.hq_confirmed.get("p1"):
            self.setup.activate_hq_setup_side("p1")
            self.setup.hq_candidates["p1"] = _TUTORIAL_P1_HQ_CELL
            self.setup.lock_hq("p1")

        if not self.setup.hq_confirmed.get("p2"):
            self.setup.activate_hq_setup_side("p2")
            col, row = _demo_hq_cell("p2", self.terrain)
            self.setup.hq_candidates["p2"] = (col, row)
            self.setup.lock_hq("p2")

        self._ensure_model_started()

    def _tutorial_skip_p2_setup(self) -> None:
        self._tutorial_ensure_game_started()

    def _apply_tutorial_battle_posture(self, step_id: str | None) -> None:
        if self.setup.phase != PHASE_GAME or step_id not in _TUTORIAL_P1_BATTLE_STEPS:
            return
        self.battle_active_side = "p1"
        self.battle_waiting_for_side = None
        self.turn = 1

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

        positioning_side = self._tutorial_positioning_side()
        if positioning_side in PLAYERS:
            marker_id = 10 if positioning_side == "p1" else 20
            confirm_id = 4
            nuke_marker_id = 19 if positioning_side == "p1" else 29
            return {
                "active_side": positioning_side,
                "waiting_for_side": None,
                "status_code": "positioning",
                "status_message": f"{positioning_side.upper()} positioning active. Arrange that side's tokens, then scan ID{confirm_id} to attack.",
                "turn_marker_id": marker_id,
                "confirm_marker_id": confirm_id,
                "nuke_marker_id": nuke_marker_id,
                "pending_nuke": self._pending_nuke_payload(positioning_side),
            }

        waiting_side = self.battle_waiting_for_side
        if waiting_side in PLAYERS:
            marker_id = 10 if waiting_side == "p1" else 20
            side_name = "Old Mick" if waiting_side == "p1" else "The Mob"
            if waiting_side == "p1":
                status_message = "Hide Your HQ. Let P1 scan ID10 to start their turn."
            else:
                status_message = f"Hide Your HQ. Let P2 scan ID20 to start their turn."
            return {
                "active_side": None,
                "waiting_for_side": waiting_side,
                "status_code": "waiting_for_turn_marker",
                "status_message": f"Hide your HQ. Scan ID{marker_id} to begin {side_name}'s turn.",
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
                self.tutorial_state = self.tutorial_ctrl.snapshot()
                self._sync_tutorial_runner_effects()
                if self.tutorial_ctrl.finished:
                    self._finish_tutorial_mode()
            return errors

        if action_name == "tutorial_undo":
            if self.tutorial_ctrl is not None:
                self.tutorial_ctrl.undo(
                    confirm_present=self._tutorial_last_confirm,
                    current_turn=self._tutorial_last_turn,
                )
                self.tutorial_state = self.tutorial_ctrl.snapshot()
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

        if self._tutorial_is_battle_visual_step():
            self._tutorial_ensure_game_started()
            self._apply_tutorial_battle_posture(self._tutorial_step_id())

        active_side = None
        if self.setup.phase == PHASE_GAME:
            if not self._tutorial_suppress_battle_confirm():
                self._update_marker_driven_battle_flow(turn, confirm_present)
            active_side = self.battle_active_side
            if self._tutorial_forces_p1_tokens():
                active_side = "p1"

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
        self._tutorial_last_confirm = confirm_present
        self._tutorial_last_turn = self.turn
        if self.tutorial_ctrl is not None:
            self.tutorial_state = self.tutorial_ctrl.tick(
                self.accepted_p1,
                self.accepted_p2,
                self.turn,
                self.hq_markers,
                confirm_present,
                nuke_cells=dict(self._pending_nuke_cell),
            )
            self._sync_tutorial_runner_effects()
            if self.tutorial_ctrl.finished:
                self._finish_tutorial_mode()
        return errors

    def _update_marker_driven_nukes(self, nuke_markers: list[dict]) -> None:
        if self.setup.phase != PHASE_GAME or self.model is None:
            return

        active_side = self._tutorial_positioning_side()
        if active_side not in PLAYERS:
            return

        pending_set = False
        for marker in nuke_markers:
            marker_id = int(marker.get("id", -1))
            side = NUKE_BY_MARKER_ID.get(marker_id)
            if side is None or side != active_side:
                continue
            position = marker.get("position") if isinstance(marker.get("position"), dict) else None
            if position is None:
                continue
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

    def game_events(self) -> list[dict]:
        events = self.pending_events
        self.pending_events = []
        return events

    def payload(self, *, corners_found: int, turn_angle: float | None, errors: list[dict], events: list[dict]) -> dict:
        payload = {
            "phase": PHASE_MODE_SELECT if self.selected_mode is None else self.setup.phase,
            "mode": self.selected_mode,
            "corners_found": corners_found,
            "turn": self.turn,
            "turn_angle": turn_angle,
            "p1": self.accepted_p1,
            "p2": self.accepted_p2,
            "hq_markers": self.hq_markers,
            "terrain": self.terrain,
            "map_seed": self.seed,
            "game": self.model.snapshot() if self.model is not None else {},
            "events": events,
            "setup": self.setup.public_payload(),
            "battle": self._battle_payload(),
            "help_visible": self.help_visible,
            "errors": dedupe_errors(errors),
        }
        if self.tutorial_state is not None and self.selected_mode == MODE_TUTORIAL:
            payload["tutorial"] = self.tutorial_state
        return payload

    def _observe_turn_side(self, turn: int | None) -> str | None:
        """Debounced turn side from the camera; keeps the last debounced side when the marker leaves frame."""
        side = "p1" if turn == 1 else "p2" if turn == 2 else None
        if side is None:
            return self._debounced_turn_side

        now = time.monotonic()
        if side != self._observed_turn_side:
            self._observed_turn_side = side
            self._observed_turn_since = now
            return self._debounced_turn_side

        if now - self._observed_turn_since >= SETUP_MARKER_STABLE_SECONDS:
            self._debounced_turn_side = side
        return self._debounced_turn_side

    def _clear_turn_observation(self) -> None:
        self._observed_turn_side = None
        self._observed_turn_since = 0.0
        self._debounced_turn_side = None

    def _stable_hq_cell(self, side: str, marker_state: dict) -> tuple[int, int] | None:
        col = marker_state.get("col")
        row = marker_state.get("row")
        cell = None
        if not marker_state.get("stale") and isinstance(col, int) and isinstance(row, int):
            cell = (col, row)

        now = time.monotonic()
        if cell != self._observed_hq_cells[side]:
            self._observed_hq_cells[side] = cell
            self._observed_hq_cell_since[side] = now
            return self._stable_hq_cells[side]

        if cell is not None and now - self._observed_hq_cell_since[side] >= SETUP_MARKER_STABLE_SECONDS:
            self._stable_hq_cells[side] = cell
        return self._stable_hq_cells[side]

    def _stable_confirm_marker_present(self, confirm_present: bool) -> bool:
        now = time.monotonic()
        if confirm_present != self._observed_confirm_present:
            self._observed_confirm_present = confirm_present
            self._observed_confirm_since = now
            if not confirm_present:
                self._stable_confirm_present = False
                self._confirm_consumed = False
            return self._stable_confirm_present

        if confirm_present and now - self._observed_confirm_since >= SETUP_MARKER_STABLE_SECONDS:
            self._stable_confirm_present = True
        return self._stable_confirm_present

    def _update_marker_driven_hq_setup(self, turn: int | None, hq_markers: dict, confirm_present: bool) -> None:
        debounced_turn_side = self._observe_turn_side(turn)
        stable_confirm_present = self._stable_confirm_marker_present(confirm_present)

        if debounced_turn_side in PLAYERS and self.setup.active_setup_side is None:
            self.setup.activate_hq_setup_side(debounced_turn_side)

        active_side = self.setup.active_setup_side
        stable_hq_cells = {side: None for side in PLAYERS}
        for side in PLAYERS:
            if side != active_side:
                self._observed_hq_cells[side] = None
                self._observed_hq_cell_since[side] = 0.0
                self._stable_hq_cells[side] = None
                continue
            stable_hq_cells[side] = self._stable_hq_cell(side, hq_markers.get(side) or {})

        if active_side not in PLAYERS or self.setup.hq_confirmed.get(active_side):
            return

        stable_cell = stable_hq_cells.get(active_side)
        if stable_cell is not None:
            position = {"x": stable_cell[0], "y": stable_cell[1]}
            if is_valid_hq_position(active_side, position, self.terrain):
                if self.setup.hq_candidates.get(active_side) != stable_cell:
                    self.setup.set_hq_candidate(active_side, position, self.terrain)
            else:
                self.setup.clear_hq_candidate(active_side)
                self.setup.set_hq_candidate(active_side, position, self.terrain)

        if not stable_confirm_present or self._confirm_consumed:
            return
        if self.setup.hq_candidates.get(active_side) is None:
            return

        game_ready, _ = self.setup.lock_hq(active_side)
        self._confirm_consumed = True
        self._clear_turn_observation()
        if game_ready:
            self._ensure_model_started()
            return

    def _update_marker_driven_battle_flow(self, turn: int | None, confirm_present: bool) -> None:
        debounced_turn_side = self._observe_turn_side(turn)
        stable_confirm_present = self._stable_confirm_marker_present(confirm_present)

        if self.battle_active_side not in PLAYERS:
            if debounced_turn_side not in PLAYERS:
                return
            if self.battle_waiting_for_side in PLAYERS and debounced_turn_side != self.battle_waiting_for_side:
                return
            self.battle_active_side = debounced_turn_side
            return

        if not stable_confirm_present or self._confirm_consumed:
            return
        if self.model is None:
            return

        attacker = self.battle_active_side
        events = self.model.resolve_side_attack(attacker, self.accepted_p1, self.accepted_p2)
        pending_nuke = self._pending_nuke_cell.get(attacker)
        if pending_nuke is not None:
            nuke_events = self.model.trigger_nuke(attacker, pending_nuke)
            if nuke_events:
                events.extend(nuke_events)
                print(f"[NUKE] ID{19 if attacker == 'p1' else 29} triggered on confirm by {attacker} at cell={pending_nuke}")
        self._pending_nuke_cell[attacker] = None
        self.pending_events.extend(events)
        self.battle_waiting_for_side = _opponent_side(attacker)
        self.battle_active_side = None
        self._confirm_consumed = True
        self._clear_turn_observation()

    def _ensure_model_started(self) -> None:
        if self.model is not None:
            return
        hidden_hq_positions = self.setup.hidden_hq_positions()
        if hidden_hq_positions is None:
            return
        hq_p1, hq_p2 = hidden_hq_positions
        self.model = game_model.new_game(self.terrain, seed=self.seed, hq_p1=hq_p1, hq_p2=hq_p2)
        self._reset_battle_tracking()
        self.battle_waiting_for_side = FIRST_PLAYER_SIDE_TO_PLAYER.get(self.setup.first_player_side)
        print("[MAP] HQ setup complete. Hidden HQs locked in.")


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
            tick_started = time.perf_counter()
            ret, frame = await asyncio.to_thread(cap.read)
            if not ret:
                print("[Camera] WARNING: Frame read failed - retrying...")
                await asyncio.sleep(0.1)
                continue

            snapshot_for_ui, last_visible_snapshot, last_calibrated_snapshot = await asyncio.to_thread(
                _process_camera_frame,
                frame,
                detector,
                last_visible_snapshot,
                last_calibrated_snapshot,
            )
            board_scan_ready = bool(snapshot_for_ui.get("calibration_ready"))
            turn_angle = _turn_angle(snapshot_for_ui)

            session.sync_scan_state(board_scan_ready)
            raw_p1, raw_p2, turn, hq_markers, confirm_present, help_present = _build_token_state(snapshot_for_ui)
            nuke_markers = _nuke_markers(snapshot_for_ui)

            frame_errors: list[dict] = []
            if not board_scan_ready:
                frame_errors.append(
                    make_error("board_not_scanned")
                    if session.setup.phase == PHASE_GAME
                    else make_error("marker_map_scan_failed")
                )

            for command in await drain_actions():
                frame_errors.extend(session.apply_command(command, board_scan_ready=board_scan_ready))

            frame_errors.extend(session.update_tokens(raw_p1, raw_p2, turn, hq_markers, confirm_present, help_present, nuke_markers))

            events = session.game_events()
            payload = session.payload(
                corners_found=len(snapshot_for_ui.get("board_corners", [])),
                turn_angle=turn_angle,
                errors=frame_errors,
                events=events,
            )
            await broadcast(json.dumps(payload))

            if not HEADLESS:
                annotated = await asyncio.to_thread(annotate_tracker_preview, frame.copy(), snapshot_for_ui)
                cv2.imshow("Old Mick MVP - Camera View  [Q to quit]", annotated)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), ord("Q"), 27):
                    print("[Camera] Quit signal received.")
                    break

            elapsed = time.perf_counter() - tick_started
            if elapsed > interval * 0.85:
                print(
                    f"[Camera] Slow tick {elapsed * 1000:.0f}ms "
                    f"(budget {interval * 1000:.0f}ms) — WS heartbeat may lag"
                )

            await asyncio.sleep(interval)
    finally:
        release_camera(cap)
        if not HEADLESS:
            cv2.destroyAllWindows()
        print("[Camera] Released.")


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
    print("  HQ markers:")
    for marker in HQ_MARKERS:
        print(f"    ID {marker.id}=P{int(marker.player)} {marker.label}")
    print()
    print("  Confirm markers:")
    for marker in CONFIRM_MARKERS:
        print(f"    ID {marker.id}={marker.label}")
    print()
    print("  Help markers:")
    for marker in HELP_MARKERS:
        print(f"    ID {marker.id}={marker.label}")
    print()
    print("  Nuke markers:")
    for marker in NUKE_MARKERS:
        print(f"    ID {marker.id}=P{int(marker.player)} {marker.label}")
    print()
    print("  Turn markers:")
    for marker in TURN_MARKERS:
        print(f"    ID {marker.id}=P{int(marker.player)} {marker.label}")
    print()
    print("  Hidden HQ setup is marker-driven once board scan is ready.")
    print()
    print("[Server] Open the frontend via the HTTP URL above\n")

    if args.no_camera:
        publisher = functools.partial(publish_no_camera, args.send_fps)
    else:
        publisher = functools.partial(publish_live_tracker, args.camera_index, args.send_fps)

    await run_server(publisher, port=args.ws_port)


def main() -> int:
    asyncio.run(async_main(parse_args()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
