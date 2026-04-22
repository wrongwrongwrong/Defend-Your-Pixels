"""Manual no-marker runtime: terminal commands -> yu_test1 rules -> WebSocket UI.

This add-only runner keeps the existing browser UI unchanged while replacing the
camera/marker input with simple terminal commands.
"""

from __future__ import annotations

import asyncio
import json
import queue
import threading
import time

from bridge.transport.websocket_transport import WS_HOST, WS_PORT, broadcast, drain_actions, run_server
from runner.setup_flow import PHASE_GAME, PHASE_HQ_PLACEMENT, PLAYERS, ATTACKER_SLOTS, SLOTS, SetupState, clone_side_state, new_side_state, sanitize_token_states
from yu_test1 import game_model, terrain_gen


SEND_FPS = 10
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
    print("  set p1 atk_b C4 NW")
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
        self.accepted_p1 = new_side_state(stale=False)
        self.accepted_p2 = new_side_state(stale=False)
        self.turn = 1
        self.quit_requested = False
        self.setup = SetupState()
        self.model: game_model.GameModel | None = None
        self.reset()

    def reset(self) -> None:
        self.seed = int(time.time() * 1000) % (2**31)
        self.terrain = terrain_gen.generate(seed=self.seed)
        self.model = None
        self.turn = 1
        self.setup.reset(board_scan_ready=True)
        print(f"[MAP] New game (seed={self.seed})")

    def side(self, player: str) -> dict:
        return self.accepted_p1 if player == "p1" else self.accepted_p2

    def apply_command(self, command: dict, *, source: str) -> tuple[list[dict], list[dict]]:
        events: list[dict] = []
        errors: list[dict] = []
        command_type = command.get("type")
        action_name = command.get("action")

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
                self.model.tier_p1 = max(1, min(4, self.model.tier_p1 + delta))
                print(f"[{source}] P1 tier -> {self.model.tier_p1}")
            elif player == 2:
                self.model.tier_p2 = max(1, min(4, self.model.tier_p2 + delta))
                print(f"[{source}] P2 tier -> {self.model.tier_p2}")
            else:
                print(f"[{source}] Ignored invalid tier player")
            return events, errors

        if action_name == "choose_side":
            first_player_side = command.get("first_player_side")
            if isinstance(first_player_side, str) and self.setup.choose_side(first_player_side):
                print(f"[{source}] First setup side -> {first_player_side}")
            return events, errors

        if action_name == "set_hq_candidate":
            side = command.get("side")
            position = command.get("position") if isinstance(command.get("position"), dict) else None
            if side in PLAYER_SET:
                error = self.setup.set_hq_candidate(side, position)
                expected_position = (position.get("x"), position.get("y")) if position is not None else None
                if error is None and position is not None and self.setup.hq_candidates.get(side) == expected_position:
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
                if game_ready:
                    self._ensure_model_started()
                    print(f"[{source}] HQ setup complete")
                elif self.setup.hq_confirmed.get(side):
                    print(f"[{source}] Confirmed {side} HQ")
                elif setup_event is not None:
                    print(f"[{source}] {setup_event['message']}")
                    errors.append(setup_event)
            return events, errors

        if action_name in {"reset_setup", "cancel_hq"}:
            self.model = None
            self.setup.reset_hq_setup()
            print(f"[{source}] Reset HQ setup")
            return events, errors

        if command_type == "set":
            player = command["player"]
            slot = command["slot"]
            col = int(command["col"])
            row = int(command["row"])
            direction = command.get("direction")
            raw_p1 = clone_side_state(self.accepted_p1)
            raw_p2 = clone_side_state(self.accepted_p2)
            token = raw_p1[slot] if player == "p1" else raw_p2[slot]
            token["col"] = col
            token["row"] = row
            token["stale"] = False
            if slot in ATTACKER_SLOT_SET:
                token["direction"] = direction
                token["angle"] = ANGLE_BY_DIRECTION[direction]
                print(f"[{source}] Set {player} {slot} -> {_format_cell(col, row)} {direction}")
            else:
                token["direction"] = None
                token["angle"] = None
                print(f"[{source}] Set {player} {slot} -> {_format_cell(col, row)}")
            errors.extend(self._apply_candidate_tokens(raw_p1, raw_p2))
            return events, errors

        if command_type == "clear":
            player = command["player"]
            slot = command["slot"]
            raw_p1 = clone_side_state(self.accepted_p1)
            raw_p2 = clone_side_state(self.accepted_p2)
            if player == "p1":
                raw_p1[slot] = {"col": None, "row": None, "angle": None, "direction": None, "stale": False}
            else:
                raw_p2[slot] = {"col": None, "row": None, "angle": None, "direction": None, "stale": False}
            errors.extend(self._apply_candidate_tokens(raw_p1, raw_p2))
            print(f"[{source}] Cleared {player} {slot}")
            return events, errors

        if command_type == "turn":
            new_turn = int(command["turn"])
            if new_turn not in (1, 2):
                print(f"[{source}] Ignored invalid turn")
                return events, errors
            if new_turn == self.turn:
                print(f"[{source}] Turn already {new_turn}")
                return events, errors
            self.turn = new_turn
            print(f"[{source}] Turn -> {self.turn}")
            events.extend(self._maybe_resolve_turn())
            return events, errors

        if command_type == "flip":
            self.turn = 2 if self.turn == 1 else 1
            print(f"[{source}] Turn -> {self.turn}")
            events.extend(self._maybe_resolve_turn())
            return events, errors

        if command_type == "quit":
            self.quit_requested = True
            print(f"[{source}] Quitting manual play")
            return events, errors

        print(f"[{source}] Ignored unsupported command: {command_type}")
        return events, errors

    def _apply_candidate_tokens(self, raw_p1: dict, raw_p2: dict) -> list[dict]:
        active_side = None
        if self.setup.phase == PHASE_GAME and self.turn in (1, 2):
            active_side = "p1" if self.turn == 1 else "p2"

        self.accepted_p1, self.accepted_p2, errors = sanitize_token_states(
            raw_p1,
            raw_p2,
            self.accepted_p1,
            self.accepted_p2,
            active_side=active_side,
            require_full_detection=self.setup.phase in {PHASE_HQ_PLACEMENT, PHASE_GAME},
        )
        return errors

    def _maybe_resolve_turn(self) -> list[dict]:
        if self.setup.phase != PHASE_GAME or self.model is None:
            return []
        return self.model.on_turn_change(self.turn, self.accepted_p1, self.accepted_p2)

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

    def print_summary(self) -> None:
        print("State:")
        print(f"  map_seed: {self.seed}")
        print(f"  phase: {self.setup.phase}")
        print(f"  turn: {self.turn}")
        print(f"  tiers: p1={self.model.tier_p1 if self.model else 1} p2={self.model.tier_p2 if self.model else 1}")
        print(f"  winner: {self.model.winner if self.model else None}")
        print(f"  win_reason: {self.model.win_reason if self.model else None}")
        print(f"  p1 atk_a: {_format_token(self.accepted_p1['atk_a'])}")
        print(f"  p1 atk_b: {_format_token(self.accepted_p1['atk_b'])}")
        print(f"  p1 def:   {_format_token(self.accepted_p1['def'])}")
        print(f"  p2 atk_a: {_format_token(self.accepted_p2['atk_a'])}")
        print(f"  p2 atk_b: {_format_token(self.accepted_p2['atk_b'])}")
        print(f"  p2 def:   {_format_token(self.accepted_p2['def'])}")
        self.print_setup_summary()

    def print_setup_summary(self) -> None:
        setup = self.setup.public_payload()
        print("Setup:")
        print(f"  board_scan_ready: {setup['board_scan_ready']}")
        print(f"  side_selection_complete: {setup['side_selection_complete']}")
        print(f"  first_player_side: {setup['first_player_side']}")
        print(f"  active_setup_side: {setup['active_setup_side']}")
        print(f"  p1 hq: candidate={setup['hq']['p1']['has_candidate']} confirmed={setup['hq']['p1']['confirmed']}")
        print(f"  p2 hq: candidate={setup['hq']['p2']['has_candidate']} confirmed={setup['hq']['p2']['confirmed']}")
        print(f"  status: {setup['status_code']} - {setup['status_message']}")

    def payload(self, events: list[dict], errors: list[dict]) -> dict:
        return {
            "phase": self.setup.phase,
            "corners_found": 4,
            "turn": self.turn,
            "turn_angle": TURN_ANGLE_BY_VALUE.get(self.turn),
            "p1": self.accepted_p1,
            "p2": self.accepted_p2,
            "terrain": self.terrain,
            "map_seed": self.seed,
            "game": self.model.snapshot() if self.model is not None else {},
            "events": events,
            "setup": self.setup.public_payload(),
            "errors": _dedupe_errors(errors),
        }


def _dedupe_errors(errors: list[dict]) -> list[dict]:
    deduped_errors: list[dict] = []
    seen_codes: set[str] = set()
    for error in errors:
        code = error.get("code")
        if not isinstance(code, str) or code in seen_codes:
            continue
        seen_codes.add(code)
        deduped_errors.append(error)
    return deduped_errors


def _print_startup_banner() -> None:
    print("=" * 55)
    print("  Old Mick Manual Play")
    print(f"  ws://{WS_HOST}:{WS_PORT}")
    print("=" * 55)
    print()
    print("  Browser UI: yu_test1/index.html")
    print("  Input mode: terminal commands (no markers required)")
    print()
    _print_help()
    print()


async def publish_manual_state(send_fps: int = SEND_FPS) -> None:
    session = Session()
    input_queue: queue.Queue[str] = queue.Queue()
    stop_event = threading.Event()
    input_thread = threading.Thread(
        target=_read_stdin_forever,
        args=(input_queue, stop_event),
        daemon=True,
        name="manual-play-stdin",
    )
    input_thread.start()

    interval = 1.0 / send_fps
    _print_startup_banner()
    session.print_summary()

    try:
        while not session.quit_requested:
            events: list[dict] = []
            errors: list[dict] = []

            for command in await drain_actions():
                command_events, command_errors = session.apply_command(command, source="web")
                events.extend(command_events)
                errors.extend(command_errors)

            while True:
                try:
                    line = input_queue.get_nowait()
                except queue.Empty:
                    break

                try:
                    command = _parse_terminal_command(line)
                except ValueError as exc:
                    print(f"[terminal] {exc}")
                    print("[terminal] Type 'help' to list commands")
                    continue

                if command is None:
                    continue

                command_type = command.get("type")
                if command_type == "help":
                    _print_help()
                    continue
                if command_type == "show":
                    session.print_summary()
                    continue
                if command_type == "show_setup":
                    session.print_setup_summary()
                    continue

                command_events, command_errors = session.apply_command(command, source="terminal")
                events.extend(command_events)
                errors.extend(command_errors)

            await broadcast(json.dumps(session.payload(events, errors)))
            await asyncio.sleep(interval)
    finally:
        stop_event.set()
        print("[Manual] Stopped.")


async def async_main() -> None:
    await run_server(publish_manual_state)


def main() -> int:
    asyncio.run(async_main())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
