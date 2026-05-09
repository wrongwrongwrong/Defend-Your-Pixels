"""
WebSocket server: bridges camera tracker to Phaser frontend.
Sends marker_update, board_state, preview_state, attack_result, game_over.
Receives: resolve_turn, reset_game, confirm_terrain, set_base, set_terrain_type.
"""

import asyncio
import json
import logging
import websockets
from typing import Set

from game_engine import (
    GameState, Phase, Token, TerrainCell, TerrainType,
    angle_to_direction, resolve_turn, get_preview, state_to_dict,
    generate_active_cells, generate_terrain, is_player_territory,
    GRID_SIZE, CORNER_CELLS
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ws_server")

HOST = "localhost"
PORT = 8765


class GameServer:
    def __init__(self, tracker=None, debug_frame_queue=None):
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.state = GameState()
        self.tracker = tracker
        self._resolve_cooldown = False
        self.debug_frame_queue = debug_frame_queue  # set by main.py for debug window
        self._init_tokens()

    def _init_tokens(self):
        for pid in [1, 2]:
            for role in ["attack_a", "attack_b", "defense"]:
                key = f"p{pid}_{role}"
                self.state.tokens[key] = Token(player=pid, role=role)
        self.state.active_cells = generate_active_cells()
        # Generate random terrain after active cells are placed
        self.state.terrain = generate_terrain(self.state.active_cells)

    async def broadcast(self, event: str, data: dict):
        if not self.clients:
            return
        msg = json.dumps({"event": event, "data": data})
        dead = set()
        for ws in self.clients:
            try:
                await ws.send(msg)
            except Exception:
                dead.add(ws)
        self.clients -= dead

    async def handler(self, ws):
        self.clients.add(ws)
        log.info(f"Client connected: {ws.remote_address}")
        # Send current state immediately
        await ws.send(json.dumps({"event": "board_state", "data": state_to_dict(self.state)}))
        try:
            async for raw in ws:
                await self._handle_message(ws, raw)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(ws)
            log.info("Client disconnected")

    async def _handle_message(self, ws, raw: str):
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return

        event = msg.get("event")
        data = msg.get("data", {})

        if event == "choose_side":
            side = data.get("side", "farmer")
            other = "emu" if side == "farmer" else "farmer"
            self.state.player_sides = {1: side, 2: other}
            self.state.phase = Phase.TUTORIAL
            await self.broadcast("board_state", state_to_dict(self.state))

        elif event == "tutorial_complete":
            if self.state.phase == Phase.TUTORIAL:
                # Move to HQ placement phase — P1 places first
                self.state.phase = Phase.HQ_PLACEMENT
                await self.broadcast("board_state", state_to_dict(self.state))

        elif event == "set_base":
            await self._handle_set_base(ws, data)

        elif event == "resolve_turn":
            await self._handle_resolve(data)

        elif event == "reset_game":
            self.state = GameState()
            self._init_tokens()
            await self.broadcast("board_state", state_to_dict(self.state))

        elif event == "confirm_terrain":
            player = data.get("player", 1)
            self.state.terrain_confirmed[player] = True
            if all(self.state.terrain_confirmed.values()):
                self.state.phase = Phase.PLANNING
            await self.broadcast("board_state", state_to_dict(self.state))

        elif event == "set_terrain":
            col = data.get("col")
            row = data.get("row")
            terrain_type = data.get("terrain_type", "soft")
            if col is not None and row is not None:
                t = TerrainType.HARD if terrain_type == "hard" else TerrainType.SOFT
                self.state.terrain[(col, row)] = TerrainCell(t)
                await self.broadcast("board_state", state_to_dict(self.state))

        elif event == "demo_token":
            # Demo/test client manually places a token
            pid      = data.get("player")
            role     = data.get("role")
            col      = data.get("col")
            row      = data.get("row")
            angle    = data.get("angle", 0)
            key = f"p{pid}_{role}"
            token = self.state.tokens.get(key)
            if token and col is not None and row is not None:
                # Attack tokens cannot be placed on terrain cells
                if role in ("attack_a", "attack_b") and (col, row) in self.state.terrain:
                    await ws.send(json.dumps({
                        "event": "token_placement_error",
                        "data": {
                            "message": "Attack tokens cannot be placed on terrain.",
                            "key": key
                        }
                    }))
                    return
                token.col = col
                token.row = row
                token.direction = angle_to_direction(angle)
            await self.broadcast("board_state", state_to_dict(self.state))
            if self.state.phase == Phase.PLANNING:
                preview = get_preview(self.state, self.state.current_player)
                await self.broadcast("preview_state", preview)

        elif event == "request_state":
            await ws.send(json.dumps({"event": "board_state", "data": state_to_dict(self.state)}))

        elif event == "request_preview":
            player = data.get("player", self.state.current_player)
            preview = get_preview(self.state, player)
            await ws.send(json.dumps({"event": "preview_state", "data": preview}))

    async def _handle_set_base(self, ws, data: dict):
        """Handle HQ placement for a player. Validates corners and territory."""
        player = data.get("player")
        col = data.get("col")
        row = data.get("row")

        if player is None or col is None or row is None:
            return
        if self.state.phase != Phase.HQ_PLACEMENT:
            return

        # Reject corner cells
        if (col, row) in CORNER_CELLS:
            await ws.send(json.dumps({
                "event": "set_base_error",
                "data": {
                    "player": player,
                    "message": "You can't place your HQ on a corner cell."
                }
            }))
            return

        # Reject cells outside player's own territory
        if not is_player_territory(player, col, row):
            await ws.send(json.dumps({
                "event": "set_base_error",
                "data": {
                    "player": player,
                    "message": "HQ must be placed within your own territory."
                }
            }))
            return

        # Place the base
        self.state.hidden_bases[player] = (col, row)
        self.state.hq_locked[player] = True

        await ws.send(json.dumps({
            "event": "base_confirmed",
            "data": {"player": player}
        }))

        # When both players have set their HQ, move to PLANNING
        if (self.state.hidden_bases[1] is not None and
                self.state.hidden_bases[2] is not None):
            self.state.phase = Phase.PLANNING
            await self.broadcast("board_state", state_to_dict(self.state))
        else:
            # Broadcast updated state so frontend knows P1 is done
            await self.broadcast("board_state", state_to_dict(self.state))

    async def _handle_resolve(self, data: dict):
        if self.state.phase != Phase.PLANNING:
            return

        attacking_player = self.state.current_player

        # Validate BOTH players have all 3 tokens placed before first attack
        missing_all = []
        for pid in [1, 2]:
            for role in ["attack_a", "attack_b", "defense"]:
                t = self.state.tokens.get(f"p{pid}_{role}")
                if not t or t.col < 0 or t.row < 0:
                    missing_all.append(f"P{pid} {role.replace('_', ' ')}")
        if missing_all:
            await self.broadcast("resolve_error", {
                "message": f"All tokens must be placed before attacking. Missing: {', '.join(missing_all)}."
            })
            return

        self.state = resolve_turn(self.state, attacking_player)
        await self.broadcast("attack_result", {
            "results": self.state.last_attack_results,
            "attacking_player": attacking_player,
        })
        if self.state.phase == Phase.GAME_OVER:
            await self.broadcast("game_over", {
                "winner": self.state.winner,
                "reason": self.state.win_reason,
            })
        else:
            self.state.current_player = 3 - attacking_player
            self.state.phase = Phase.PLANNING
        await self.broadcast("board_state", state_to_dict(self.state))

    async def apply_marker_update(self, markers: dict):
        """Called from camera loop — update token positions/directions."""
        changed = False
        from game_engine import angle_to_direction, Direction

        for mid, data in markers.items():
            role = data.get("role")
            if role == "terrain":
                if self.state.phase == Phase.TERRAIN_PLACEMENT:
                    col, row = data["col"], data["row"]
                    ttype = TerrainType.HARD if data.get("terrain_type") == "hard" else TerrainType.SOFT
                    if (col, row) not in self.state.terrain:
                        self.state.terrain[(col, row)] = TerrainCell(ttype)
                        changed = True
                continue
            if role == "side_selection":
                if self.state.phase == Phase.SIDE_SELECTION:
                    side = data.get("side")
                    if side in ("farmer", "emu"):
                        other = "emu" if side == "farmer" else "farmer"
                        self.state.player_sides = {1: side, 2: other}
                        self.state.phase = Phase.TERRAIN_PLACEMENT
                        await self.broadcast("board_state", state_to_dict(self.state))
                continue
            if role == "control":
                action = data.get("action")
                if action == "resolve" and self.state.phase == Phase.PLANNING:
                    if not self._resolve_cooldown:
                        self._resolve_cooldown = True
                        await self._handle_resolve({})
                        asyncio.get_running_loop().call_later(
                            3.0, setattr, self, "_resolve_cooldown", False)
                continue
            if role == "turn_cube":
                pid = data.get("player")
                if pid and self.state.current_player != pid:
                    self.state.current_player = pid
                    await self.broadcast("board_state", state_to_dict(self.state))
                continue
            if role == "hq":
                pid = data.get("player")
                col, row = data.get("col"), data.get("row")
                if (pid and col is not None and row is not None
                        and self.state.phase == Phase.HQ_PLACEMENT
                        and not self.state.hq_locked.get(pid)
                        and is_player_territory(pid, col, row)
                        and (col, row) not in CORNER_CELLS):
                    self.state.hidden_bases[pid] = (col, row)
                    self.state.hq_locked[pid] = True
                    await self.broadcast("hq_confirmed", {"player": pid})
                    changed = True
                continue

            pid = data.get("player")
            token_role = data.get("role")
            key = f"p{pid}_{token_role}"
            token = self.state.tokens.get(key)
            if not token:
                continue

            col, row = data["col"], data["row"]
            direction = angle_to_direction(data.get("angle", 0))

            if token.col != col or token.row != row or token.direction != direction:
                token.col = col
                token.row = row
                token.direction = direction
                changed = True

        return changed

    async def camera_loop(self):
        """Continuously read camera and broadcast marker updates."""
        if self.tracker is None:
            return
        while True:
            try:
                # Run blocking cap.read() in a thread so the event loop stays responsive
                frame_data = await asyncio.to_thread(self.tracker.read_frame)
            except Exception as e:
                log.error(f"camera read_frame error: {e}", exc_info=True)
                await asyncio.sleep(0.1)
                continue
            if frame_data:
                changed = await self.apply_marker_update(frame_data["markers"])
                if changed:
                    await self.broadcast("marker_update", {
                        "tokens": state_to_dict(self.state)["tokens"],
                        "terrain": state_to_dict(self.state)["terrain"],
                    })
                    if self.state.phase == Phase.PLANNING:
                        preview = get_preview(self.state, self.state.current_player)
                        await self.broadcast("preview_state", preview)
                if self.debug_frame_queue is not None:
                    try:
                        dbg = await asyncio.to_thread(self.tracker.draw_debug, frame_data)
                        if self.debug_frame_queue.full():
                            try:
                                self.debug_frame_queue.get_nowait()
                            except Exception:
                                pass
                        self.debug_frame_queue.put_nowait(dbg)
                    except Exception as e:
                        log.error(f"draw_debug error: {e}", exc_info=True)
            await asyncio.sleep(0.033)  # ~30fps

    async def serve(self):
        camera_task = asyncio.create_task(self.camera_loop())
        async with websockets.serve(self.handler, HOST, PORT,
                                    ping_interval=None, ping_timeout=None):
            log.info(f"WebSocket server running on ws://{HOST}:{PORT}")
            await asyncio.Future()  # run forever
