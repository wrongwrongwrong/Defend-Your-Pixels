"""
Demo/test client — simulates physical marker movement without a camera.
Run AFTER starting the backend server:
    python main.py --no-camera
    python demo_client.py        # in a second terminal

Commands (type and press Enter):
    p1a <col> <row> [h|v|d]     — move P1 Attack-A to col,row with direction
    p1b <col> <row> [h|v|d]     — move P1 Attack-B
    p1d <col> <row>             — move P1 Defense
    p2a / p2b / p2d             — same for Player 2
    base <player> <col> <row>   — set hidden base
    terrain <col> <row> [hard]  — place terrain (soft by default)
    side farmer|emu             — Player 1 chooses a side (other side goes to P2)
    confirm <player>            — confirm terrain for player
    resolve                     — fire resolve_turn
    reset                       — reset game
    preview                     — request preview state
    demo                        — run a scripted 5-move demo sequence
    quit / exit                 — exit
"""

import asyncio
import json
import sys
import websockets

WS_URL = "ws://localhost:8765"

TOKEN_KEYS = {
    "p1a": ("p1", "attack_a"), "p1b": ("p1", "attack_b"), "p1d": ("p1", "defense"),
    "p2a": ("p2", "attack_a"), "p2b": ("p2", "attack_b"), "p2d": ("p2", "defense"),
}
DIR_MAP = {"h": "horizontal", "v": "vertical", "d": "diagonal",
           "horizontal": "horizontal", "vertical": "vertical", "diagonal": "diagonal"}

# Quick angle that produces each direction when fed through angle_to_direction()
DIR_ANGLES = {"h": 0, "horizontal": 0, "v": 90, "vertical": 90, "d": 45, "diagonal": 45}


async def send(ws, event, data=None):
    await ws.send(json.dumps({"event": event, "data": data or {}}))
    print(f"  → sent {event}")


async def move_token(ws, token_key: str, col: int, row: int, direction: str = "horizontal"):
    """Simulate a marker_update for one token."""
    player_str, role = TOKEN_KEYS[token_key]
    pid = int(player_str[1])
    angle = DIR_ANGLES.get(direction, 0)

    await send(ws, "marker_update_single", {
        "player": pid,
        "role": role,
        "col": col,
        "row": row,
        "angle": angle,
        "direction": DIR_MAP.get(direction, direction),
    })


async def scripted_demo(ws):
    """A short scripted sequence to show the game working."""
    print("\n[DEMO] Running scripted sequence...\n")
    steps = [
        ("choose_side",      {"side": "farmer"}),
        ("confirm_terrain",  {"player": 1}),
        ("confirm_terrain",  {"player": 2}),
        ("set_base",         {"player": 1, "col": 0, "row": 11}),
        ("set_base",         {"player": 2, "col": 11, "row": 0}),
        ("set_terrain",      {"col": 5, "row": 3, "terrain_type": "soft"}),
        ("set_terrain",      {"col": 3, "row": 5, "terrain_type": "hard"}),
    ]
    for event, data in steps:
        await send(ws, event, data)
        await asyncio.sleep(0.3)

    # Move P1 tokens
    token_moves = [
        ("p1a", 2, 8, "d"),
        ("p1b", 3, 9, "h"),
        ("p1d", 2, 9, None),
        ("p2a", 9, 2, "d"),
        ("p2b", 8, 3, "v"),
        ("p2d", 9, 3, None),
    ]
    for key, col, row, direction in token_moves:
        player_str, role = TOKEN_KEYS[key]
        pid = int(player_str[1])
        angle = DIR_ANGLES.get(direction or "h", 0)
        dir_val = DIR_MAP.get(direction or "h", "horizontal")
        # Build a fake board_state update through the server's apply path
        await ws.send(json.dumps({
            "event": "demo_token",
            "data": {"player": pid, "role": role, "col": col, "row": row,
                     "angle": angle, "direction": dir_val}
        }))
        print(f"  → placed {key} at ({col},{row}) dir={dir_val}")
        await asyncio.sleep(0.4)

    await send(ws, "request_preview", {"player": 1})
    print("\n[DEMO] Done — type 'resolve' to fire attacks, or move tokens manually.\n")


async def repl(ws):
    print("Demo client connected. Type 'help' for commands.\n")
    loop = asyncio.get_event_loop()

    while True:
        try:
            raw = await loop.run_in_executor(None, input, "> ")
        except (EOFError, KeyboardInterrupt):
            break

        parts = raw.strip().split()
        if not parts:
            continue
        cmd = parts[0].lower()

        if cmd in ("quit", "exit"):
            break

        elif cmd == "help":
            print(__doc__)

        elif cmd == "demo":
            await scripted_demo(ws)

        elif cmd in ("side", "choose_side"):
            side = parts[1].lower() if len(parts) >= 2 else "farmer"
            if side not in ("farmer", "emu"):
                print("  Usage: side farmer  OR  side emu")
            else:
                await send(ws, "choose_side", {"side": side})

        elif cmd == "resolve":
            await send(ws, "resolve_turn", {})

        elif cmd == "reset":
            await send(ws, "reset_game", {})

        elif cmd == "preview":
            await send(ws, "request_preview", {})

        elif cmd == "confirm" and len(parts) >= 2:
            await send(ws, "confirm_terrain", {"player": int(parts[1])})

        elif cmd == "base" and len(parts) >= 4:
            await send(ws, "set_base", {"player": int(parts[1]), "col": int(parts[2]), "row": int(parts[3])})

        elif cmd == "terrain" and len(parts) >= 3:
            ttype = "hard" if len(parts) >= 4 and parts[3] == "hard" else "soft"
            await send(ws, "set_terrain", {"col": int(parts[1]), "row": int(parts[2]), "terrain_type": ttype})

        elif cmd in TOKEN_KEYS and len(parts) >= 3:
            col = int(parts[1])
            row = int(parts[2])
            direction = DIR_MAP.get(parts[3], "horizontal") if len(parts) >= 4 else "horizontal"
            player_str, role = TOKEN_KEYS[cmd]
            pid = int(player_str[1])
            await ws.send(json.dumps({
                "event": "demo_token",
                "data": {"player": pid, "role": role, "col": col, "row": row,
                         "angle": DIR_ANGLES.get(direction, 0), "direction": direction}
            }))
            print(f"  → moved {cmd} to ({col},{row}) [{direction}]")

        else:
            print(f"  Unknown command: {raw!r}. Type 'help' for usage.")


async def main():
    try:
        async with websockets.connect(WS_URL, ping_interval=None) as ws:
            await repl(ws)
    except ConnectionRefusedError:
        print(f"ERROR: Could not connect to {WS_URL}")
        print("Make sure the backend is running: python main.py --no-camera")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
