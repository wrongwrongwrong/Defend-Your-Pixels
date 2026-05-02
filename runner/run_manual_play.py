"""Manual runtime entrypoint: terminal/browser setup -> shared live rules -> WebSocket/HTTP UI.

This runner is the no-camera fallback for local UI testing. It keeps the same payload shape
as the live tracker path, but token/setup input comes from terminal commands and browser
actions instead of ArUco markers.
"""

from __future__ import annotations

import asyncio
import functools
import http.server
import json
from pathlib import Path
import queue
import socketserver
import sys
import threading
import time

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from bridge.transport.websocket_transport import WS_HOST, WS_PORT, broadcast, drain_actions, run_server
from runner.setup_flow import (
    ATTACKER_SLOTS,
    PHASE_GAME,
    PLAYERS,
    SLOTS,
    SetupState,
    clone_side_state,
    dedupe_errors,
    new_side_state,
    sanitize_token_states,
)
from live_rules import game_model, terrain_gen


SEND_FPS = 10
HTTP_PORT = 8080
FRONTEND_DIR = ROOT_DIR / "yu_test2" / "frontend"
PLAYER_SET = set(PLAYERS)
SLOT_SET = set(SLOTS)
ATTACKER_SLOT_SET = set(ATTACKER_SLOTS)
COMPASS_8 = ("E", "SE", "S", "SW", "W", "NW", "N", "NE")
TURN_ANGLE_BY_VALUE = {1: 0.0, 2: 180.0}
ANGLE_BY_DIRECTION = {
    "E": 0.0,
    "SE": 45.0,
    "S": 90.0,
    "SW": 135.0,
    "W": 180.0,
    "NW": 225.0,
    "N": 270.0,
    "NE": 315.0,
}


def start_http_server(port: int, root: Path):
    """Serve the yu_test2 frontend over plain HTTP for manual play."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"[HTTP] Serving {root} at http://localhost:{port}")
    return httpd


def _manual_empty_token() -> dict:
    return {
        "col": None,
        "row": None,
        "angle": None,
        "direction": None,
        "stale": False,
    }


def _parse_cell(cell_text: str) -> tuple[int, int]:
    cell = cell_text.strip().upper()
    if len(cell) < 2:
        raise ValueError("cell must look like A1 through L12")

    col_text = cell[0]
    row_text = cell[1:]
    if not ("A" <= col_text <= "L"):
        raise ValueError("column must be A through L")
    if not row_text.isdigit():
        raise ValueError("row must be 1 through 12")

    row_number = int(row_text)
    if not 1 <= row_number <= 12:
        raise ValueError("row must be 1 through 12")

    return ord(col_text) - ord("A"), row_number - 1


def _format_cell(col: int | None, row: int | None) -> str:
    if col is None or row is None:
        return "--"
    return f"{chr(ord('A') + col)}{row + 1}"


def _format_token(token: dict) -> str:
    cell = _format_cell(token.get("col"), token.get("row"))
    direction = token.get("direction")
    return f"{cell} {direction}" if direction else cell


def _print_help() -> None:
    print("Commands:")
    print("  help")
    print("  show")
    print("  show_setup")
    print("  choose_side old_mick")
    print("  choose_side mob")
    print("  set_hq p1 A3")
    print("  confirm_hq p1")
    print("  reset_setup")
    print("  set p1 atk_a A3 E")
    print("  set p1 atk_b C4 SW")
    print("  set p1 def D5")
    print("  set p2 atk_a J9 W")
    print("  clear p1 atk_a")
    print("  turn 1")
    print("  turn 2")
    print("  flip")
    print("  new_map")
    print("  tier 1 +1")
    print("  tier 2 -1")
    print("  quit")


def _read_stdin_forever(input_queue: queue.Queue[str], stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        try:
            line = input("manual> ")
        except EOFError:
            input_queue.put("quit")
            return
        input_queue.put(line)


def _parse_terminal_command(line: str) -> dict | None:
    parts = line.strip().split()
    if not parts:
        return None

    name = parts[0].lower()
    if name == "help":
        return {"type": "help"}
    if name == "show":
        return {"type": "show"}
    if name == "show_setup":
        return {"type": "show_setup"}
    if name in {"quit", "exit"}:
        return {"type": "quit"}
    if name == "flip":
        return {"type": "flip"}
    if name == "new_map":
        return {"type": "new_map"}
    if name == "reset_setup":
        return {"action": "reset_setup"}

    if name == "choose_side":
        if len(parts) != 2:
            raise ValueError("usage: choose_side old_mick|mob")
        first_player_side = parts[1].strip().lower()
        if first_player_side not in {"old_mick", "mob"}:
            raise ValueError("choose_side expects old_mick or mob")
        return {"action": "choose_side", "first_player_side": first_player_side}

    if name == "set_hq":
        if len(parts) != 3:
            raise ValueError("usage: set_hq p1 A3")
        side = parts[1].lower()
        if side not in PLAYER_SET:
            raise ValueError("side must be p1 or p2")
        col, row = _parse_cell(parts[2])
        return {"action": "set_hq_candidate", "side": side, "position": {"x": col, "y": row}}

    if name == "confirm_hq":
        if len(parts) != 2:
            raise ValueError("usage: confirm_hq p1")
        side = parts[1].lower()
        if side not in PLAYER_SET:
            raise ValueError("side must be p1 or p2")
        return {"action": "confirm_hq", "side": side}

    if name == "turn":
        if len(parts) != 2:
            raise ValueError("usage: turn 1|2")
        try:
            turn = int(parts[1])
        except ValueError as exc:
            raise ValueError("turn must be 1 or 2") from exc
        if turn not in (1, 2):
            raise ValueError("turn must be 1 or 2")
        return {"type": "turn", "turn": turn}

    if name == "tier":
        if len(parts) != 3:
            raise ValueError("usage: tier 1 +1")
        try:
            player = int(parts[1])
            delta = int(parts[2])
        except ValueError as exc:
            raise ValueError("tier expects an integer player and integer delta") from exc
        if player not in (1, 2):
            raise ValueError("tier player must be 1 or 2")
        return {"type": "tier", "player": player, "delta": delta}

    if name == "nuke":
        if len(parts) != 3:
            raise ValueError("usage: nuke p1 H9")
        side = parts[1].lower()
        if side not in PLAYER_SET:
            raise ValueError("side must be p1 or p2")
        col, row = _parse_cell(parts[2])
        return {"action": "trigger_nuke", "side": side, "position": {"x": col, "y": row}}

    if name == "clear":
        if len(parts) != 3:
            raise ValueError("usage: clear p1 atk_a")
        player = parts[1].lower()
        slot = parts[2].lower()
        if player not in PLAYER_SET:
            raise ValueError("player must be p1 or p2")
        if slot not in SLOT_SET:
            raise ValueError("slot must be atk_a, atk_b, or def")
        return {"type": "clear", "player": player, "slot": slot}

    if name == "set":
        if len(parts) not in (4, 5):
            raise ValueError("usage: set p1 atk_a A3 E  or  set p1 def D5")

        player = parts[1].lower()
        slot = parts[2].lower()
        if player not in PLAYER_SET:
            raise ValueError("player must be p1 or p2")
        if slot not in SLOT_SET:
            raise ValueError("slot must be atk_a, atk_b, or def")

        col, row = _parse_cell(parts[3])
        if slot in ATTACKER_SLOT_SET:
            if len(parts) != 5:
                raise ValueError("attackers need a direction, for example: set p1 atk_a A3 E")
            direction = parts[4].upper()
            if direction not in COMPASS_8:
                raise ValueError("direction must be one of E SE S SW W NW N NE")
            return {
                "type": "set",
                "player": player,
                "slot": slot,
                "col": col,
                "row": row,
                "direction": direction,
            }

        if len(parts) != 4:
            raise ValueError("defenders do not take a direction, for example: set p1 def D5")
        return {
            "type": "set",
            "player": player,
            "slot": slot,
            "col": col,
            "row": row,
            "direction": None,
        }

    raise ValueError(f"unknown command: {parts[0]}")


class Session:
    def __init__(self):
        self.setup = SetupState()
        self.quit_requested = False
        self.reset()

    def reset(self) -> None:
        self.seed = int(time.time() * 1000) % (2**31)
        self.terrain = terrain_gen.generate(seed=self.seed)
        self.raw_p1 = new_side_state(stale=False)
        self.raw_p2 = new_side_state(stale=False)
        self.accepted_p1 = new_side_state(stale=False)
        self.accepted_p2 = new_side_state(stale=False)
        self.turn = 1
        self.model: game_model.GameModel | None = None
        self.pending_events: list[dict] = []
        self.setup.reset(board_scan_ready=True)
        print(f"[MAP] New game (seed={self.seed})")

    def apply_command(self, command: dict, *, source: str) -> tuple[list[dict], list[dict]]:
        events: list[dict] = []
        errors: list[dict] = []
        command_type = command.get("type")
        action_name = command.get("action")

        if command_type == "help":
            _print_help()
            return events, errors

        if command_type == "show":
            self._print_state_summary()
            return events, errors

        if command_type == "show_setup":
            self._print_setup_summary()
            return events, errors

        if command_type == "quit":
            self.quit_requested = True
            print(f"[{source}] Quit requested")
            return events, errors

        if command_type == "new_map":
            self.reset()
            print(f"[{source}] Regenerated map")
            return events, errors

        if command_type == "tier":
            if self.model is None:
                print(f"[{source}] Ignored tier change until the game starts")
                return events, errors
            try:
                player = int(command.get("player"))
                delta = int(command.get("delta"))
            except (TypeError, ValueError):
                print(f"[{source}] Ignored invalid tier command")
                return events, errors

            if player == 1:
                self.model.tier_p1 = max(0, min(4, self.model.tier_p1 + delta))
                print(f"[{source}] P1 tier -> {self.model.tier_p1}")
            elif player == 2:
                self.model.tier_p2 = max(0, min(4, self.model.tier_p2 + delta))
                print(f"[{source}] P2 tier -> {self.model.tier_p2}")
            else:
                print(f"[{source}] Ignored invalid tier player")
            return events, errors

        if action_name == "choose_side":
            first_player_side = command.get("first_player_side")
            if isinstance(first_player_side, str) and self.setup.choose_side(first_player_side):
                print(f"[{source}] First setup side -> {first_player_side}")
            else:
                print(f"[{source}] {self.setup.status_message}")
            return events, errors

        if action_name == "set_hq_candidate":
            side = command.get("side")
            position = command.get("position") if isinstance(command.get("position"), dict) else None
            if side in PLAYER_SET:
                error = self.setup.set_hq_candidate(side, position, self.terrain)
                expected_position = None if position is None else (position.get("x"), position.get("y"))
                if error is None and expected_position == self.setup.hq_candidates.get(side):
                    print(f"[{source}] HQ candidate {side} -> {_format_cell(position.get('x'), position.get('y'))}")
                elif error is not None:
                    print(f"[{source}] {error['message']}")
                    errors.append(error)
                else:
                    print(f"[{source}] {self.setup.status_message}")
            return events, errors

        if action_name == "confirm_hq":
            side = command.get("side")
            if side in PLAYER_SET:
                game_ready, setup_event = self.setup.confirm_hq(side)
                if setup_event is not None:
                    print(f"[{source}] {setup_event['message']}")
                    errors.append(setup_event)
                else:
                    print(f"[{source}] {self.setup.status_message}")
                if game_ready:
                    self._ensure_model_started()
            return events, errors

        if action_name in {"reset_setup", "cancel_hq"}:
            self.model = None
            self.setup.reset_hq_setup()
            print(f"[{source}] Setup reset")
            return events, errors

        if action_name == "trigger_nuke":
            if self.model is None or self.turn not in (1, 2):
                print(f"[{source}] Ignored nuke command until the game starts")
                return events, errors
            side = command.get("side")
            position = command.get("position") if isinstance(command.get("position"), dict) else None
            active_side = "p1" if self.turn == 1 else "p2"
            if side != active_side or not isinstance(position, dict):
                print(f"[{source}] Nuke must be triggered by the active side")
                return events, errors
            nuke_events = self.model.trigger_nuke(active_side, (position.get("x"), position.get("y")))
            events.extend(nuke_events)
            print(f"[{source}] {active_side} nuke -> {_format_cell(position.get('x'), position.get('y'))}")
            return events, errors

        if command_type == "set":
            player = command.get("player")
            slot = command.get("slot")
            if player in PLAYER_SET and slot in SLOT_SET:
                target = self.raw_p1 if player == "p1" else self.raw_p2
                direction = command.get("direction")
                target[slot] = {
                    "col": command.get("col"),
                    "row": command.get("row"),
                    "angle": ANGLE_BY_DIRECTION.get(direction) if isinstance(direction, str) else None,
                    "direction": direction,
                    "stale": False,
                }
                print(f"[{source}] {player}.{slot} -> {_format_token(target[slot])}")
                errors.extend(self._sync_tokens())
            return events, errors

        if command_type == "clear":
            player = command.get("player")
            slot = command.get("slot")
            if player in PLAYER_SET and slot in SLOT_SET:
                target = self.raw_p1 if player == "p1" else self.raw_p2
                target[slot] = _manual_empty_token()
                print(f"[{source}] Cleared {player}.{slot}")
                errors.extend(self._sync_tokens())
            return events, errors

        if command_type == "turn":
            try:
                new_turn = int(command.get("turn"))
            except (TypeError, ValueError):
                return events, errors
            events.extend(self._set_turn(new_turn, source))
            errors.extend(self._sync_tokens())
            return events, errors

        if command_type == "flip":
            new_turn = 2 if self.turn == 1 else 1
            events.extend(self._set_turn(new_turn, source))
            errors.extend(self._sync_tokens())
            return events, errors

        return events, errors

    def payload(self, *, errors: list[dict], events: list[dict]) -> dict:
        return {
            "phase": self.setup.phase,
            "corners_found": 4 if self.setup.board_scan_ready else 0,
            "turn": self.turn,
            "turn_angle": TURN_ANGLE_BY_VALUE.get(self.turn),
            "p1": self.accepted_p1,
            "p2": self.accepted_p2,
            "terrain": self.terrain,
            "map_seed": self.seed,
            "game": self.model.snapshot() if self.model is not None else {},
            "events": events,
            "setup": self.setup.public_payload(),
            "errors": dedupe_errors(errors),
        }

    def _set_turn(self, new_turn: int, source: str) -> list[dict]:
        if new_turn not in (1, 2):
            print(f"[{source}] Ignored invalid turn value")
            return []

        self.turn = new_turn
        print(f"[{source}] Turn -> {self.turn}")
        if self.setup.phase != PHASE_GAME or self.model is None:
            return []
        return self.model.on_turn_change(self.turn, self.accepted_p1, self.accepted_p2)

    def _sync_tokens(self) -> list[dict]:
        active_side = None
        if self.setup.phase == PHASE_GAME and self.turn in (1, 2):
            active_side = "p1" if self.turn == 1 else "p2"

        self.accepted_p1, self.accepted_p2, errors = sanitize_token_states(
            self.raw_p1,
            self.raw_p2,
            self.accepted_p1,
            self.accepted_p2,
            active_side=active_side,
            require_full_detection=self.setup.phase == PHASE_GAME,
        )
        # Keep the manual raw state aligned to the accepted state so invalid moves do not spam
        # the same warning on every broadcast tick.
        self.raw_p1 = clone_side_state(self.accepted_p1)
        self.raw_p2 = clone_side_state(self.accepted_p2)

        for error in errors:
            print(f"[manual] {error['message']}")
        return errors

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

    def _print_state_summary(self) -> None:
        print("\nState summary")
        print(f"  phase: {self.setup.phase}")
        print(f"  turn: {self.turn}")
        print(f"  p1 atk_a: {_format_token(self.accepted_p1['atk_a'])}")
        print(f"  p1 atk_b: {_format_token(self.accepted_p1['atk_b'])}")
        print(f"  p1 def:   {_format_token(self.accepted_p1['def'])}")
        print(f"  p2 atk_a: {_format_token(self.accepted_p2['atk_a'])}")
        print(f"  p2 atk_b: {_format_token(self.accepted_p2['atk_b'])}")
        print(f"  p2 def:   {_format_token(self.accepted_p2['def'])}")
        if self.model is not None:
            snapshot = self.model.snapshot()
            print(f"  destroyed cells: {len(snapshot['destroyed'])}")
            print(f"  winner: {snapshot['winner']}")
        else:
            print("  game: not started")
        print()

    def _print_setup_summary(self) -> None:
        setup_payload = self.setup.public_payload()
        print("\nSetup summary")
        print(f"  phase: {self.setup.phase}")
        print(f"  board_scan_ready: {setup_payload['board_scan_ready']}")
        print(f"  side_selection_complete: {setup_payload['side_selection_complete']}")
        print(f"  first_player_side: {setup_payload['first_player_side']}")
        print(f"  active_setup_side: {setup_payload['active_setup_side']}")
        print(f"  p1 hq: {setup_payload['hq']['p1']}")
        print(f"  p2 hq: {setup_payload['hq']['p2']}")
        print(f"  status: {setup_payload['status_message']}")
        print()


async def publish_manual_play(send_fps: int = SEND_FPS) -> None:
    session = Session()
    interval = 1.0 / send_fps
    input_queue: queue.Queue[str] = queue.Queue()
    stop_event = threading.Event()
    input_thread = threading.Thread(target=_read_stdin_forever, args=(input_queue, stop_event), daemon=True)
    input_thread.start()

    print("[Manual] Type 'help' for commands")

    try:
        while not session.quit_requested:
            frame_events: list[dict] = []
            frame_errors: list[dict] = []

            while True:
                try:
                    line = input_queue.get_nowait()
                except queue.Empty:
                    break

                try:
                    command = _parse_terminal_command(line)
                except ValueError as exc:
                    print(f"[manual] {exc}")
                    continue

                if command is None:
                    continue
                events, errors = session.apply_command(command, source="manual")
                frame_events.extend(events)
                frame_errors.extend(errors)

            for command in await drain_actions():
                events, errors = session.apply_command(command, source="browser")
                frame_events.extend(events)
                frame_errors.extend(errors)

            payload = session.payload(errors=frame_errors, events=frame_events)
            await broadcast(json.dumps(payload))
            await asyncio.sleep(interval)
    finally:
        stop_event.set()


async def async_main() -> None:
    if not FRONTEND_DIR.is_dir():
        raise RuntimeError(f"Missing frontend directory: {FRONTEND_DIR}")

    start_http_server(HTTP_PORT, FRONTEND_DIR)

    print("=" * 55)
    print("  Old Mick Manual Play")
    print(f"  ws://{WS_HOST}:{WS_PORT}")
    print(f"  http://localhost:{HTTP_PORT}")
    print("=" * 55)
    print()
    print("  Browser: open http://localhost:8080")
    print("  Input: terminal commands and browser setup actions")
    print()

    await run_server(publish_manual_play)


def main() -> int:
    asyncio.run(async_main())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
