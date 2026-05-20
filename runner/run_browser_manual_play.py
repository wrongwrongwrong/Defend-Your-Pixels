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
from runner.run_manual_play import (
    HTTP_PORT,
    FRONTEND_DIR,
    Session as TerminalManualSession,
)
from runner.setup_flow import PLAYERS, dedupe_errors


SEND_FPS = 10


class BrowserManualSession(TerminalManualSession):
    def _auto_start_game(self) -> None:
        active_side = self.setup.active_setup_side
        if active_side not in PLAYERS:
            return
        self.turn = 1 if self.setup.first_player_side == "old_mick" else 2
        ordered_sides = [active_side, "p2" if active_side == "p1" else "p1"]
        for side in ordered_sides:
            cell = self._first_resource_cell(side)
            position = {"x": cell[0], "y": cell[1]}
            self.setup.set_hq_candidate(side, position, self.terrain)
            self.setup.confirm_hq(side)
        self._ensure_model_started()
        print("[browser] Auto-started HQ setup from the chosen side and entered game")

    def _first_resource_cell(self, side: str) -> tuple[int, int]:
        resources = self.terrain.get(f"{side}_resources", [])
        if not resources:
            raise RuntimeError(f"No resource cells available for {side}")
        first = resources[0]
        return int(first["col"]), int(first["row"])

    def apply_command(self, command: dict, *, source: str) -> tuple[list[dict], list[dict]]:
        action_name = command.get("action")
        first_player_side_before = self.setup.first_player_side
        events, errors = super().apply_command(command, source=source)
        if (
            action_name == "choose_side"
            and first_player_side_before is None
            and self.setup.first_player_side is not None
            and self.model is None
        ):
            self._auto_start_game()
        return events, errors

    def payload(self, *, errors: list[dict], events: list[dict]) -> dict:
        payload = super().payload(errors=errors, events=events)
        if payload.get("manual_controls"):
            payload["battle"]["status_message"] = "Browser manual mode: click your side to place tokens, click attack tokens to rotate, then END TURN."
        return payload


async def publish_browser_manual(send_fps: int = SEND_FPS) -> None:
    session = BrowserManualSession()
    interval = 1.0 / send_fps
    print("[Browser Manual] Use browser mode select, pick a side, then click the board to play")
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
