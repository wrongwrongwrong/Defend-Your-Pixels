"""Live runtime entrypoint: camera -> tracker -> yu_test1 rules -> WebSocket UI.

This runtime keeps the current `python_tracker` camera/grid-mapping pipeline, but the
authoritative gameplay loop and browser payload now follow `yu_test1`.
"""

from __future__ import annotations

import asyncio
import json
import os
import time

import cv2

from bridge.transport.websocket_transport import WS_HOST, WS_PORT, broadcast, drain_actions, run_server
from python_tracker.camera.camera_runtime import configure_camera, open_camera, release_camera
from python_tracker.marker_detection.aruco_detector import create_detector
from python_tracker.state_output.tracker_snapshot import annotate_tracker_preview, apply_calibration_fallback, build_tracker_preview
from python_tracker.tracked_markers import TOKEN_MARKERS, TURN_MARKER_ID
from yu_test1 import game_model, terrain_gen


CAMERA_ID = 1
SEND_FPS = 10
HEADLESS = os.environ.get("DYP_HEADLESS", "").strip().lower() in ("1", "true", "yes", "on")

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
        return current_snapshot

    merged_markers: dict[int, dict] = {
        int(marker["id"]): marker
        for marker in cached_snapshot.get("markers", [])
        if isinstance(marker, dict) and isinstance(marker.get("id"), int)
    }
    for marker in current_snapshot.get("markers", []):
        if isinstance(marker, dict) and isinstance(marker.get("id"), int):
            merged_markers[int(marker["id"])] = marker

    return {
        **cached_snapshot,
        **current_snapshot,
        "markers": list(merged_markers.values()),
        "turn_marker": current_snapshot.get("turn_marker") or cached_snapshot.get("turn_marker"),
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


def _empty_token() -> dict:
    return {
        "col": None,
        "row": None,
        "angle": None,
        "direction": None,
        "stale": True,
    }


class Session:
    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.seed = int(time.time() * 1000) % (2 ** 31)
        self.terrain = terrain_gen.generate(seed=self.seed)
        self.model = game_model.new_game(self.terrain, seed=self.seed)
        print(f"[MAP] New game (seed={self.seed}) HQ p1={self.model.hq_p1} p2={self.model.hq_p2}")

    def apply_command(self, command: dict) -> None:
        command_type = command.get("type")
        if command_type == "new_map":
            self.reset()
            return
        if command_type != "tier":
            return

        try:
            player = int(command.get("player"))
            delta = int(command.get("delta"))
        except (TypeError, ValueError):
            return

        if player == 1:
            self.model.tier_p1 = max(1, min(4, self.model.tier_p1 + delta))
        elif player == 2:
            self.model.tier_p2 = max(1, min(4, self.model.tier_p2 + delta))


def _build_token_state(snapshot: dict) -> tuple[dict, dict, int | None]:
    p1 = {"atk_a": _empty_token(), "atk_b": _empty_token(), "def": _empty_token()}
    p2 = {"atk_a": _empty_token(), "atk_b": _empty_token(), "def": _empty_token()}

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
            "stale": False,
        }

    turn_marker = snapshot.get("turn_marker") if isinstance(snapshot.get("turn_marker"), dict) else None
    turn_rotation = turn_marker.get("rotation") if turn_marker else None
    turn = _turn_from_rotation(float(turn_rotation)) if isinstance(turn_rotation, (int, float)) else None
    return p1, p2, turn


async def publish_live_tracker(camera_id: int = CAMERA_ID, send_fps: int = SEND_FPS):
    cap = open_camera(camera_id)
    if cap is None:
        print(f"[Camera] ERROR: Cannot open camera (index {camera_id})")
        return

    session = Session()
    configure_camera(cap)
    detector = create_detector()
    interval = 1.0 / send_fps
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

            for command in await drain_actions():
                session.apply_command(command)

            snapshot, _ = build_tracker_preview(frame, detector)
            if snapshot.get("calibration_ready"):
                last_calibrated_snapshot = snapshot
            effective_snapshot = apply_calibration_fallback(snapshot, last_calibrated_snapshot)

            if _snapshot_has_detected_markers(effective_snapshot):
                last_visible_snapshot = _merge_visible_snapshot(last_visible_snapshot, effective_snapshot)

            snapshot_for_ui = last_visible_snapshot or effective_snapshot
            p1, p2, turn = _build_token_state(snapshot_for_ui)
            events = session.model.on_turn_change(turn, p1, p2) if turn else []
            payload = {
                "phase": "game",
                "corners_found": len(snapshot_for_ui.get("board_corners", [])),
                "turn": turn,
                "turn_angle": snapshot_for_ui.get("turn_marker", {}).get("rotation") if isinstance(snapshot_for_ui.get("turn_marker"), dict) else None,
                "p1": p1,
                "p2": p2,
                "terrain": session.terrain,
                "map_seed": session.seed,
                "game": session.model.snapshot(),
                "events": events,
            }

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
    asyncio.run(async_main())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
