from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import websockets


WS_URL = "ws://localhost:8765"


def _now() -> str:
    return time.strftime("%H:%M:%S")


def _summarize_board_state(data: dict[str, Any]) -> str:
    turn = data.get("turn")
    active = data.get("active_player")
    game_over = data.get("game_over")
    winner = data.get("winner")
    last_action = data.get("last_action")
    units = data.get("units", [])
    return (
        f"turn={turn} active_player={active} game_over={game_over} winner={winner} "
        f"units={len(units)} last_action={last_action!r}"
    )


async def _recv_board_state(ws) -> dict[str, Any]:
    while True:
        raw = await ws.recv()
        msg = json.loads(raw)
        if msg.get("type") != "board_state":
            continue
        data = msg.get("data")
        if not isinstance(data, dict):
            continue
        return data


async def _send_action(ws, action: dict[str, Any]) -> None:
    envelope = {"type": "action", "data": action}
    await ws.send(json.dumps(envelope))


async def main() -> int:
    print(f"[{_now()}] Connecting to {WS_URL} ...")
    async with websockets.connect(WS_URL) as ws:
        state = await _recv_board_state(ws)
        print(f"[{_now()}] board_state: {_summarize_board_state(state)}")

        # 1) Try an attack (Step 5 action flow, even if it misses).
        # In the react_integration_level, P1 attacker is typically u1.
        print(f"[{_now()}] Sending action: attack_in_direction(u1, up)")
        await _send_action(ws, {"action": "attack_in_direction", "unit_id": "u1", "direction": "up"})
        state = await _recv_board_state(ws)
        print(f"[{_now()}] board_state: {_summarize_board_state(state)}")

        # 2) End turn (Step 14 / Step 2 action -> state).
        print(f"[{_now()}] Sending action: end_turn")
        await _send_action(ws, {"action": "end_turn"})
        state = await _recv_board_state(ws)
        print(f"[{_now()}] board_state: {_summarize_board_state(state)}")

        # 3) Move a unit (Step 14 move flow). P2 attacker is typically u0 at (6,0).
        print(f"[{_now()}] Sending action: move_unit(u0 -> (6, 1))")
        await _send_action(ws, {"action": "move_unit", "unit_id": "u0", "position": {"x": 6, "y": 1}})
        state = await _recv_board_state(ws)
        print(f"[{_now()}] board_state: {_summarize_board_state(state)}")

        # 4) Demonstrate move countdown is authoritative and can auto-end the turn.
        print(f"[{_now()}] Waiting 11 seconds for move countdown auto end-turn ...")
        deadline = time.monotonic() + 12.0
        while time.monotonic() < deadline:
            state = await _recv_board_state(ws)
            print(f"[{_now()}] board_state: {_summarize_board_state(state)}")
            if "move timer expired" in str(state.get("last_action", "")).lower():
                break

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

