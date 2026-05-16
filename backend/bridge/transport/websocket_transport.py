"""WebSocket transport for bridge <-> frontend messages.

This module owns three responsibilities only:
- accept WebSocket clients
- queue incoming `action` messages from clients
- broadcast already-serialized messages to every connected client
"""

import asyncio
import json
from typing import Any

from websockets.server import serve

# Default local host/port for the live browser frontend.
WS_HOST = "localhost"
WS_PORT = 8765

ActionPayload = dict[str, Any]

# Global connection state.
# NOTE: This server is intentionally simple; it is designed for local dev and a single
# Python process hosting both the model and the transport.
connected_clients: set[Any] = set()

# Incoming actions queue:
# - producer: `ws_handler` (client -> server)
# - consumer: the game loop / runner (server drains actions each tick)
incoming_actions: asyncio.Queue[ActionPayload] = asyncio.Queue()


async def ws_handler(websocket: Any) -> None:
    """Accept a new client and keep the connection open."""
    # Track the client so `broadcast()` can fan out updates.
    connected_clients.add(websocket)
    addr = websocket.remote_address
    print(f"[WS] Client connected: {addr}  (total: {len(connected_clients)})")

    try:
        # Read messages until the client disconnects.
        async for message in websocket:
            # We only care about messages of the shape:
            #   {"type":"action","data":{...}}
            command = _extract_command(message)
            if command is None:
                continue

            # Push into the queue; game loop will validate and apply via dispatcher.
            await incoming_actions.put(command)
    finally:
        # Ensure we always remove the client, even if handler errors.
        connected_clients.discard(websocket)
        print(f"[WS] Client disconnected: {addr}  (total: {len(connected_clients)})")


def _extract_command(message: str) -> ActionPayload | None:
    # Parse JSON defensively; ignore malformed payloads.
    try:
        payload = json.loads(message)
    except json.JSONDecodeError:
        return None

    payload_type = payload.get("type")
    if payload_type == "action":
        action = payload.get("data")
        return action if isinstance(action, dict) else None
    if payload_type in {"new_map", "tier"}:
        return payload if isinstance(payload, dict) else None
    return None


async def broadcast(message: str) -> None:
    """Send a message to all connected clients, ignoring failures."""
    if not connected_clients:
        return

    # Gather send coroutines so one slow client doesn't block the others.
    await asyncio.gather(
        *[client.send(message) for client in connected_clients],
        return_exceptions=True,
    )


async def drain_actions() -> list[ActionPayload]:
    # Drain the queue into a list so the caller can apply actions in a deterministic batch.
    actions: list[ActionPayload] = []
    while not incoming_actions.empty():
        actions.append(await incoming_actions.get())
    return actions


async def run_server(publisher, host: str = WS_HOST, port: int = WS_PORT) -> None:
    # `publisher` is typically a long-running coroutine that:
    # - reads tracker frames
    # - runs the game loop
    # - broadcasts board_state / tracker_frame to clients
    print(f"[Server] Listening on ws://{host}:{port}")
    async with serve(ws_handler, host, port):
        await publisher()
