"""
yu_test2 dev server (macOS friendly).

A single command spins up:
  - WebSocket server on  ws://localhost:8765   (game state broadcast)
  - HTTP static server on http://localhost:8080  (serves frontend/)

Usage:
    python3 server.py                       # webcam + frontend
    python3 server.py --no-camera           # frontend only (UI testing)
    python3 server.py --camera-index 1      # alt webcam
    python3 server.py --ws-port 8765 --http-port 8080

Designed to keep the same WS message shape that the FW2 backend emits, so
the frontend works against either source.
"""

import argparse
import asyncio
import functools
import http.server
import json
import os
import socketserver
import threading
import time
from pathlib import Path

import websockets

import tracker
from live_rules import terrain_gen, game_model

HERE = Path(__file__).resolve().parent
FRONTEND_DIR = HERE / "frontend"

WS_HOST = "localhost"


# ─── Game session ─────────────────────────────────────────────────────────────

class Session:
    def __init__(self):
        self.reset()

    def reset(self):
        self.seed    = int(time.time() * 1000) % (2 ** 31)
        self.terrain = terrain_gen.generate(seed=self.seed)
        self.model   = game_model.new_game(self.terrain, seed=self.seed)
        print(f"[MAP] New game (seed={self.seed}) "
              f"HQ p1={self.model.hq_p1} p2={self.model.hq_p2}")


# ─── HTTP static server (background thread) ───────────────────────────────────

def start_http_server(port: int, root: Path):
    """Serve the frontend folder over plain HTTP so ES modules load correctly."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(root))
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"[HTTP] Serving {root} at http://localhost:{port}")


# ─── WebSocket clients registry ───────────────────────────────────────────────

connected: set = set()


async def ws_handler(websocket, *, session: Session):
    connected.add(websocket)
    print(f"[WS] Client connected ({len(connected)} total)")
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                t = data.get("type")
                if t == "new_map":
                    session.reset()
                elif t == "tier":
                    p, d = int(data["player"]), int(data["delta"])
                    if p == 1:
                        session.model.tier_p1 = max(0, min(4, session.model.tier_p1 + d))
                    else:
                        session.model.tier_p2 = max(0, min(4, session.model.tier_p2 + d))
            except (json.JSONDecodeError, KeyError, ValueError):
                pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected.discard(websocket)
        print(f"[WS] Client disconnected ({len(connected)} total)")


async def broadcast(payload: dict):
    if not connected:
        return
    msg = json.dumps(payload)
    await asyncio.gather(*[c.send(msg) for c in connected],
                         return_exceptions=True)


# ─── Camera loop (or idle loop when --no-camera) ──────────────────────────────

def open_camera(index: int):
    import cv2
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open camera index {index}")
        return None
    print(f"[OK] Camera opened (index={index})")
    return cap


async def camera_loop(session: Session, camera_index: int, show_window: bool):
    import cv2
    cap = open_camera(camera_index)
    if cap is None:
        return

    detector, aruco_dict, params, api_mode = tracker.build_detector()
    print(f"[OK] ArUco detector ready ({api_mode} API)\n")
    token_cache = tracker.TokenCache()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] Failed to read frame — check camera.")
                break

            cc, p1_live, p2_live, turn_angle, raw = tracker.detect_frame(
                frame, detector, aruco_dict, params, api_mode
            )
            H = tracker.compute_homography(cc)

            p1 = token_cache.resolve_side("p1", p1_live, H)
            p2 = token_cache.resolve_side("p2", p2_live, H)
            turn = tracker.turn_from_angle(turn_angle)
            events = session.model.on_turn_change(turn, p1, p2) if turn else []

            await broadcast(_build_state(session, cc, p1, p2, turn, turn_angle, events))

            if show_window:
                # Draw bounding boxes + labels around every detected marker
                tracker.annotate_frame(frame, raw)

                # Status line summary in the corner
                corners_ok = len(cc) == 4
                cv2.putText(frame, f"Corners: {len(cc)}/4", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                            (0, 255, 0) if corners_ok else (0, 100, 255), 2)
                if turn is not None:
                    cv2.putText(frame, f"Turn: P{turn}", (10, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 220, 0), 2)

                # Per-token detection status (helps debug "why no attack?")
                y = 90
                for label, side_dict in (("P1", p1), ("P2", p2)):
                    for role in ("atk_a", "atk_b", "def"):
                        tok = side_dict.get(role) or {}
                        seen = tok.get("col") is not None and not tok.get("stale", True)
                        cached = tok.get("col") is not None and tok.get("stale", False)
                        status = "LIVE" if seen else ("cache" if cached else "----")
                        col = ((0, 255, 100) if seen
                               else (0, 200, 200) if cached
                               else (80, 80, 80))
                        cv2.putText(frame, f"{label}.{role}: {status}", (10, y),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1)
                        y += 18
                    y += 6

                cv2.imshow("yu_test2 tracker (press q to quit)", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            await asyncio.sleep(0.01)
    finally:
        cap.release()
        if show_window:
            cv2.destroyAllWindows()


async def idle_loop(session: Session):
    """No-camera mode: still broadcast state so the UI can render."""
    print("[OK] Running in --no-camera mode. UI will render but markers are inactive.")
    empty_token = {"col": None, "row": None, "angle": None,
                   "direction": None, "stale": True}
    p_empty = {role: empty_token.copy() for role in ("atk_a", "atk_b", "def")}
    while True:
        await broadcast(_build_state(session, {}, p_empty, p_empty, None, None, []))
        await asyncio.sleep(0.1)  # 10 fps is plenty for static UI


def _build_state(session, cc, p1, p2, turn, turn_angle, events):
    return {
        "phase":         "game",
        "corners_found": len(cc),
        "turn":          turn,
        "turn_angle":    round(turn_angle, 1) if turn_angle is not None else None,
        "p1":            p1,
        "p2":            p2,
        "terrain":       session.terrain,
        "map_seed":      session.seed,
        "game":          session.model.snapshot(),
        "events":        events,
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="yu_test2 dev server")
    p.add_argument("--no-camera",   action="store_true",
                   help="Skip camera; just run frontend + idle WS broadcasts.")
    p.add_argument("--camera-index", type=int, default=1,
                   help="Webcam device index (default 1).")
    p.add_argument("--no-window",    action="store_true",
                   help="Hide the OpenCV preview window (default: shown).")
    p.add_argument("--ws-port",      type=int, default=8765)
    p.add_argument("--http-port",    type=int, default=8080)
    return p.parse_args()


async def main():
    args = parse_args()

    if not FRONTEND_DIR.is_dir():
        print(f"[ERROR] Frontend dir missing: {FRONTEND_DIR}")
        return

    session = Session()
    start_http_server(args.http_port, FRONTEND_DIR)

    print(f"[WS] Game state on  ws://localhost:{args.ws_port}")
    print(f"[UI] Open browser → http://localhost:{args.http_port}\n")

    handler = functools.partial(ws_handler, session=session)
    async with websockets.serve(handler, WS_HOST, args.ws_port):
        if args.no_camera:
            await idle_loop(session)
        else:
            await camera_loop(session, args.camera_index, show_window=not args.no_window)


if __name__ == "__main__":
    print("=== yu_test2 dev server ===")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[bye]")
