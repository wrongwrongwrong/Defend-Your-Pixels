"""Browser-only manual runtime for Prototype 4 style board controls.

This runner serves the current frontend and enables `manual_controls` so browser
clicks can place/rotate tokens and submit turns. It uses the current shared
`live_rules.game_model` instead of Prototype 4's older rule model.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
for import_root in (ROOT_DIR, BACKEND_DIR):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from bridge.transport.websocket_transport import WS_HOST, WS_PORT, broadcast, drain_actions, run_server
from runner.frontend_static_server import start_frontend_http_server
from runner.port_check import ensure_ports_available
from runner.run_manual_play import (
    HTTP_PORT,
    FRONTEND_DIR,
    PLAYER_SET,
    SLOT_SET,
    ANGLE_BY_DIRECTION,
    _format_cell,
    Session as TerminalManualSession,
)
from runner.setup_flow import PLAYERS, dedupe_errors


SEND_FPS = 10


class BrowserManualSession(TerminalManualSession):
    def select_mode(self, mode: str) -> bool:
        selected = super().select_mode(mode)
        if selected:
            self._auto_start_game()
        return selected

    def _auto_start_game(self) -> None:
        self.setup.choose_side("old_mick")
        for side in PLAYERS:
            cell = self._first_resource_cell(side)
            position = {"x": cell[0], "y": cell[1]}
            self.setup.set_hq_candidate(side, position, self.terrain)
            self.setup.confirm_hq(side)
        self._ensure_model_started()
        print("[browser] Auto-started game with hidden HQs from terrain resources")

    def _first_resource_cell(self, side: str) -> tuple[int, int]:
        resources = self.terrain.get(f"{side}_resources", [])
        if not resources:
            raise RuntimeError(f"No resource cells available for {side}")
        first = resources[0]
        return int(first["col"]), int(first["row"])

    def apply_command(self, command: dict, *, source: str) -> tuple[list[dict], list[dict]]:
        action_name = command.get("action")
        if action_name == "place_token":
            return self._place_token(command, source=source)
        if action_name == "rotate_token":
            return self._rotate_token(command, source=source)
        if action_name == "end_turn":
            return self._end_turn(command, source=source)
        return super().apply_command(command, source=source)

    def _place_token(self, command: dict, *, source: str) -> tuple[list[dict], list[dict]]:
        side = command.get("side")
        role = command.get("role")
        if side not in PLAYER_SET or role not in SLOT_SET:
            return [], []
        target = self.raw_p1 if side == "p1" else self.raw_p2
        direction = command.get("direction")
        target[role] = {
            "col": command.get("col"),
            "row": command.get("row"),
            "angle": ANGLE_BY_DIRECTION.get(direction) if isinstance(direction, str) else None,
            "direction": direction,
            "stale": False,
        }
        print(f"[{source}] {side}.{role} -> {_format_cell(command.get('col'), command.get('row'))} {direction or ''}".rstrip())
        return [], self._sync_tokens()

    def _rotate_token(self, command: dict, *, source: str) -> tuple[list[dict], list[dict]]:
        side = command.get("side")
        role = command.get("role")
        direction = command.get("direction")
        if side not in PLAYER_SET or role not in {"atk_a", "atk_b"}:
            return [], []
        target = self.raw_p1 if side == "p1" else self.raw_p2
        token = target.get(role) or {}
        token["direction"] = direction
        token["angle"] = ANGLE_BY_DIRECTION.get(direction) if isinstance(direction, str) else None
        token["stale"] = False
        target[role] = token
        print(f"[{source}] {side}.{role} direction -> {direction}")
        return [], self._sync_tokens()

    def _end_turn(self, command: dict, *, source: str) -> tuple[list[dict], list[dict]]:
        if self.model is None or self.turn not in (1, 2):
            return [], []
        player = command.get("player")
        active_turn = self.turn
        if player not in (active_turn, f"p{active_turn}"):
            return [], []
        errors = self._sync_tokens()
        attacker = "p1" if active_turn == 1 else "p2"
        events = self.model.resolve_side_attack(attacker, self.accepted_p1, self.accepted_p2)
        self.turn = 2 if active_turn == 1 else 1
        print(f"[{source}] End turn -> P{self.turn}")
        return events, errors

    def payload(self, *, errors: list[dict], events: list[dict]) -> dict:
        payload = super().payload(errors=errors, events=events)
        payload["manual_controls"] = self.selected_mode is not None and self.setup.phase == "game"
        if payload["manual_controls"]:
            payload["battle"]["status_message"] = "Browser manual mode: click your side to place tokens, click attack tokens to rotate, then END TURN."
        return payload


async def publish_browser_manual(send_fps: int = SEND_FPS) -> None:
    session = BrowserManualSession()
    interval = 1.0 / send_fps
    print("[Browser Manual] Use the browser mode select, then click the board to play")
    while True:
        frame_events: list[dict] = []
        frame_errors: list[dict] = []
        for command in await drain_actions():
            events, errors = session.apply_command(command, source="browser")
            frame_events.extend(events)
            frame_errors.extend(errors)
        await broadcast(json.dumps(session.payload(errors=dedupe_errors(frame_errors), events=frame_events)))
        await asyncio.sleep(interval)


async def async_main() -> None:
    if not FRONTEND_DIR.is_dir():
        raise RuntimeError(f"Missing frontend directory: {FRONTEND_DIR}")
    ensure_ports_available(
        http_port=HTTP_PORT,
        ws_port=WS_PORT,
        ws_host=WS_HOST,
        runtime_name="Browser manual play",
    )
    start_frontend_http_server(HTTP_PORT, FRONTEND_DIR, ROOT_DIR / "protocol")
    print("=" * 55)
    print("  Defend Your Pixels Browser Manual Play")
    print(f"  ws://{WS_HOST}:{WS_PORT}")
    print(f"  http://localhost:{HTTP_PORT}")
    print("=" * 55)
    await run_server(publish_browser_manual)


def main() -> int:
    asyncio.run(async_main())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
