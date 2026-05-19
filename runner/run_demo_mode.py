"""Scripted browser demo runtime: frontend + WebSocket states advanced by N.

This runner is intentionally separate from the live tracker. It serves the current
frontend and broadcasts a small set of representative payloads. The frontend's
`keydown-N` sends `demo_next`, which advances the scripted state.
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
from live_rules import game_model, terrain_gen
from runner.frontend_static_server import start_frontend_http_server
from runner.port_check import DEFAULT_HTTP_PORT, ensure_ports_available


HTTP_PORT = DEFAULT_HTTP_PORT
FRONTEND_DIR = ROOT_DIR / "frontend"
SEND_FPS = 10


def _empty_side(stale: bool = True) -> dict:
    return {
        role: {"col": None, "row": None, "angle": None, "direction": None, "stale": stale}
        for role in ("atk_a", "atk_b", "def")
    }


def _tok(col: int, row: int, direction: str | None = None) -> dict:
    return {"col": col, "row": row, "angle": None, "direction": direction, "stale": False}


class DemoSession:
    def __init__(self) -> None:
        self.index = 0
        self.seed = 42
        self.terrain = terrain_gen.generate(seed=self.seed)
        self.model = game_model.new_game(self.terrain, seed=self.seed, hq_p1=(2, 8), hq_p2=(9, 3))
        self.states = self._build_states()

    def _state(
        self,
        *,
        phase: str,
        active_side: str | None,
        p1: dict | None = None,
        p2: dict | None = None,
        hq_markers: dict | None = None,
        errors: list[dict] | None = None,
        events: list[dict] | None = None,
        setup_message: str = "Demo state.",
    ) -> dict:
        return {
            "phase": phase,
            "mode": "normal",
            "demo_mode": True,
            "corners_found": 4 if phase != "scan" else 2,
            "turn": 1 if active_side == "p1" else 2 if active_side == "p2" else None,
            "turn_angle": 0.0 if active_side == "p1" else 180.0 if active_side == "p2" else None,
            "battle": {
                "active_side": active_side,
                "waiting_for_side": None,
                "status_code": "demo",
                "status_message": "Press N to advance the scripted demo.",
            },
            "setup": {
                "board_scan_ready": phase != "scan",
                "side_selection_complete": True,
                "first_player_side": "old_mick",
                "active_setup_side": None,
                "hq": {
                    "p1": {"confirmed": phase == "game", "has_candidate": phase != "scan"},
                    "p2": {"confirmed": phase == "game", "has_candidate": phase != "scan"},
                },
                "status_code": "demo",
                "status_message": setup_message,
            },
            "p1": p1 or _empty_side(),
            "p2": p2 or _empty_side(),
            "hq_markers": hq_markers or {
                "p1": {"col": None, "row": None, "stale": True},
                "p2": {"col": None, "row": None, "stale": True},
            },
            "terrain": self.terrain,
            "map_seed": self.seed,
            "game": self.model.snapshot(),
            "events": events or [],
            "errors": errors or [],
            "help_visible": False,
        }

    def _build_states(self) -> list[dict]:
        p1 = {"atk_a": _tok(3, 7, "E"), "atk_b": _tok(4, 6, "SE"), "def": _tok(1, 8)}
        p2 = {"atk_a": _tok(8, 4, "W"), "atk_b": _tok(9, 3, "NW"), "def": _tok(10, 2)}
        hqs = {
            "p1": {"col": 2, "row": 8, "stale": False},
            "p2": {"col": 9, "row": 3, "stale": False},
        }
        return [
            self._state(
                phase="scan",
                active_side=None,
                setup_message="Demo: board scan is incomplete.",
                errors=[{"code": "marker_map_scan_failed", "message": "Demo: align all 4 corner markers."}],
            ),
            self._state(phase="hq_placement", active_side=None, hq_markers=hqs, setup_message="Demo: hidden HQ markers are being confirmed."),
            self._state(phase="game", active_side="p1", p1=p1, p2=p2, hq_markers=hqs, setup_message="Demo: Old Mick is positioning."),
            self._state(phase="game", active_side="p2", p1=p1, p2=p2, hq_markers=hqs, setup_message="Demo: The Mob is positioning."),
        ]

    def current(self) -> dict:
        return self.states[self.index]

    def advance(self) -> None:
        self.index = (self.index + 1) % len(self.states)


async def publish_demo(send_fps: int = SEND_FPS) -> None:
    session = DemoSession()
    interval = 1.0 / send_fps
    print("[Demo] Press N in the browser to send demo_next")
    while True:
        for command in await drain_actions():
            if command.get("type") == "demo_next":
                session.advance()
        await broadcast(json.dumps(session.current()))
        await asyncio.sleep(interval)


async def async_main() -> None:
    ensure_ports_available(
        http_port=HTTP_PORT,
        ws_port=WS_PORT,
        ws_host=WS_HOST,
        runtime_name="Demo mode",
    )
    start_frontend_http_server(HTTP_PORT, FRONTEND_DIR, ROOT_DIR / "protocol")
    print("=" * 55)
    print("  Defend Your Pixels Demo Mode")
    print(f"  ws://{WS_HOST}:{WS_PORT}")
    print(f"  http://localhost:{HTTP_PORT}")
    print("=" * 55)
    await run_server(publish_demo)


def main() -> int:
    asyncio.run(async_main())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
