"""WebSocket transport layer for publishing tracker frames."""

import asyncio
import json
from websockets.server import serve

# ── Constants ────────────────────────────────────────────────────────────────

WS_HOST   = "localhost"
WS_PORT   = 8765

# ── Shared WebSocket state ────────────────────────────────────────────────────

connected_clients: set = set()
incoming_actions: asyncio.Queue = asyncio.Queue()


# ── WebSocket handlers ────────────────────────────────────────────────────────

async def ws_handler(websocket):
    """Accept a new client and keep the connection open."""
    connected_clients.add(websocket)
    addr = websocket.remote_address
    print(f"[WS] Client connected: {addr}  (total: {len(connected_clients)})")
    try:
        async for message in websocket:
            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                continue

            if payload.get("type") == "action" and payload.get("data") is not None:
                await incoming_actions.put(payload["data"])
    finally:
        connected_clients.discard(websocket)
        print(f"[WS] Client disconnected: {addr}  (total: {len(connected_clients)})")


async def broadcast(message: str):
    """Send a message to all connected clients, ignoring failures."""
    if not connected_clients:
        return
    await asyncio.gather(
        *[client.send(message) for client in connected_clients],
        return_exceptions=True,
    )


async def drain_actions() -> list[dict]:
    actions = []
    while not incoming_actions.empty():
        actions.append(await incoming_actions.get())
    return actions


async def run_server(publisher, host: str = WS_HOST, port: int = WS_PORT):
    print(f"[Server] Listening on ws://{host}:{port}")
    async with serve(ws_handler, host, port):
        await publisher()
