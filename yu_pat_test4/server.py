"""
yu_test3 dev server (macOS friendly).

A single command spins up:
  - WebSocket server on  ws://localhost:8765   (game state broadcast)
  - HTTP static server on http://localhost:8080  (serves frontend/)

Usage:
    python3 server.py                       # webcam + frontend
    python3 server.py --no-camera           # frontend only (UI testing)
    python3 server.py --camera-index 1      # alt webcam
    python3 server.py --ws-port 8765 --http-port 8080
    python3 server.py --tutorial            # run with guided tutorial

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
import sys
import threading
import time
from pathlib import Path

import websockets

# live_rules/ lives at the repo root (one level up from yu_test3/).
# Add it to sys.path so `from live_rules import ...` works when running
# server.py directly from inside the yu_test3/ folder.
HERE = Path(__file__).resolve().parent
# live_rules/ lives inside yu_pat_test4/ itself
sys.path.insert(0, str(HERE))

try:
    from live_rules import terrain_gen, game_model, tutorial
    _LIVE_RULES = True
except ImportError:
    _LIVE_RULES = False

FRONTEND_DIR = HERE / "frontend"

WS_HOST = "localhost"


# ─── Game session ─────────────────────────────────────────────────────────────

# ─── Demo mode data ───────────────────────────────────────────────────────────

_STALE_TOK = {"col": None, "row": None, "angle": None, "direction": None, "stale": True}
_STALE_HQ  = {"col": None, "row": None, "stale": True}


def _p_empty():
    return {r: dict(_STALE_TOK) for r in ("atk_a", "atk_b", "def")}


DEMO_TERRAIN = {
    "p1_resources": [
        {"col": 2, "row": 8, "hp": 2, "resource_type": "normal"},
        {"col": 1, "row": 9, "hp": 2, "resource_type": "normal"},
        {"col": 3, "row": 9, "hp": 2, "resource_type": "stronghold"},
        {"col": 0, "row": 10, "hp": 2, "resource_type": "normal"},
        {"col": 2, "row": 10, "hp": 2, "resource_type": "normal"},
    ],
    "p2_resources": [
        {"col": 9,  "row": 2, "hp": 2, "resource_type": "normal"},
        {"col": 10, "row": 1, "hp": 2, "resource_type": "normal"},
        {"col": 8,  "row": 3, "hp": 2, "resource_type": "stronghold"},
        {"col": 11, "row": 1, "hp": 2, "resource_type": "normal"},
        {"col": 9,  "row": 3, "hp": 2, "resource_type": "normal"},
    ],
    "p1_hard": [{"col": 4, "row": 7}],
    "p2_hard": [{"col": 7, "row": 4}],
    "p1_soft": [{"col": 3, "row": 8}],
    "p2_soft": [{"col": 8, "row": 4}],
}


def _game(tier1=0, tier2=0, score1=0, score2=0,
          destroyed=None, damage=None, soft_gone=None,
          hq_revealed=None, winner=None, win_reason=None):
    return {
        "tier_p1": tier1, "tier_p2": tier2,
        "score_p1_attrition": score1, "score_p2_attrition": score2,
        "attrition_threshold": 40,
        "winner": winner, "win_reason": win_reason,
        "hq_revealed": hq_revealed or {},
        "destroyed": destroyed or [],
        "damage": damage or {},
        "soft_gone": soft_gone or [],
    }


def _hq_setup(p1_confirmed=False, p1_cand=False, p2_confirmed=False, p2_cand=False):
    return {
        "board_scan_ready": True,
        "hq": {
            "p1": {"confirmed": p1_confirmed, "has_candidate": p1_cand},
            "p2": {"confirmed": p2_confirmed, "has_candidate": p2_cand},
        },
    }


def _tok(col, row, direction=None):
    return {"col": col, "row": row, "angle": 0, "direction": direction, "stale": False}


def build_demo_states():
    pe = _p_empty()

    p1_live = {
        "atk_a": _tok(4, 6, "NE"),
        "atk_b": _tok(3, 7, "E"),
        "def":   _tok(1, 9),
    }
    p2_live = {
        "atk_a": _tok(7, 5, "SW"),
        "atk_b": _tok(8, 4, "W"),
        "def":   _tok(10, 2),
    }

    hq1 = {"col": 2, "row": 9, "stale": False}
    hq2 = {"col": 10, "row": 1, "stale": False}
    hq1s = {**hq1, "stale": True}
    hq2s = {**hq2, "stale": True}

    def _s(phase, active, p1, p2, hq_p1, hq_p2, game_snap,
           corners=4, setup=None, errors=None, events=None):
        return {
            "phase": phase,
            "demo_mode": True,
            "corners_found": corners,
            "battle": {"active_side": active},
            "setup": setup or _hq_setup(True, True, True, True),
            "p1": p1, "p2": p2,
            "hq_markers": {
                "p1": hq_p1 if hq_p1 else dict(_STALE_HQ),
                "p2": hq_p2 if hq_p2 else dict(_STALE_HQ),
            },
            "terrain": DEMO_TERRAIN,
            "map_seed": 42,
            "game": game_snap,
            "errors": errors or [],
            "events": events or [],
        }

    return [
        # 0 — Board scanning
        _s("scan", None, _p_empty(), _p_empty(), None, None,
           _game(), corners=2,
           setup={"board_scan_ready": False, "hq": None},
           errors=[{"code": "marker_map_scan_failed",
                    "message": "Align all 4 corner markers to begin"}]),
        # 1 — Board ready, side selection
        _s("side_selection", None, _p_empty(), _p_empty(), None, None,
           _game(), corners=4,
           setup={"board_scan_ready": True,
                  "hq": {"p1": {"confirmed": False, "has_candidate": False},
                         "p2": {"confirmed": False, "has_candidate": False}}}),
        # 2 — HQ placement (P1 placed, P2 pending)
        _s("hq_placement", None, _p_empty(), _p_empty(), hq1, None,
           _game(), corners=4,
           setup=_hq_setup(p1_cand=True)),
        # 3 — Game start, P1's turn
        _s("game", "p1", p1_live, _p_empty(), hq1s, None,
           _game()),
        # 4 — P2's turn, damage on board
        _s("game", "p2", _p_empty(), p2_live, None, hq2s,
           _game(tier1=1, score1=8,
                 destroyed=[[10, 1]],
                 damage={"9,2": 1}),
           events=[{"type": "cell_destroyed"}]),
        # 5 — Tier upgrade moment (both sides upgraded)
        _s("game", "p1", p1_live, _p_empty(), None, None,
           _game(tier1=2, tier2=1, score1=18, score2=10,
                 destroyed=[[10, 1], [11, 1]],
                 damage={"9,2": 1, "8,3": 1})),
        # 6 — Enemy HQ revealed
        _s("game", "p2", _p_empty(), p2_live, None, hq2s,
           _game(tier1=2, tier2=2, score1=26, score2=18,
                 hq_revealed={"p2": [10, 1]},
                 destroyed=[[10, 1], [11, 1], [9, 2]],
                 damage={"8,3": 1})),
        # 7 — Victory
        _s("game", None, _p_empty(), _p_empty(), hq1s, hq2s,
           _game(tier1=3, tier2=2, score1=32, score2=20,
                 winner="p1", win_reason="nest_destroyed",
                 hq_revealed={"p1": [2, 9], "p2": [10, 1]},
                 destroyed=[[10, 1], [11, 1], [9, 2], [9, 3]])),
    ]


class DemoSession:
    """Cycles through scripted demo states; compatible with ws_handler."""
    def __init__(self):
        self.states = build_demo_states()
        self.index  = 0

    def current(self):
        return self.states[self.index]

    def advance(self):
        self.index = (self.index + 1) % len(self.states)
        return self.current()

    def reset(self):
        self.index = 0


# ─── Live game session ────────────────────────────────────────────────────────

class Session:
    def __init__(self, tutorial_mode: bool = False):
        if not _LIVE_RULES:
            raise RuntimeError("live_rules not available — use --demo mode instead")
        self.tutorial_mode = tutorial_mode
        self.tutorial_ctrl = tutorial.new_tutorial() if tutorial_mode else None
        self.reset()

    def reset(self):
        # Use fixed seed in tutorial mode for predictable terrain
        if self.tutorial_mode:
            self.seed = tutorial.TUTORIAL_SEED
        else:
            self.seed = int(time.time() * 1000) % (2 ** 31)
        self.terrain = terrain_gen.generate(seed=self.seed)
        self.model   = game_model.new_game(self.terrain, seed=self.seed)
        # Reset tutorial if in tutorial mode
        if self.tutorial_ctrl:
            self.tutorial_ctrl = tutorial.new_tutorial()
        print(f"[MAP] New game (seed={self.seed}) "
              f"HQ p1={self.model.hq_p1} p2={self.model.hq_p2}"
              f"{' [TUTORIAL]' if self.tutorial_mode else ''}")


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
                if t == "demo_next":
                    if isinstance(session, DemoSession):
                        session.advance()
                elif t == "new_map":
                    session.reset()
                elif t == "tier" and not isinstance(session, DemoSession):
                    p, d = int(data["player"]), int(data["delta"])
                    if p == 1:
                        session.model.tier_p1 = max(0, min(4, session.model.tier_p1 + d))
                    else:
                        session.model.tier_p2 = max(0, min(4, session.model.tier_p2 + d))
                elif t == "tutorial_dismiss" and not isinstance(session, DemoSession):
                    if session.tutorial_ctrl:
                        session.tutorial_ctrl.dismiss()
                elif t == "action" and not isinstance(session, DemoSession):
                    action_data = data.get("data", {})
                    action      = action_data.get("action", "")
                    if action:
                        session.model.apply_action(action, action_data)
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
    import tracker
    cap = open_camera(camera_index)
    if cap is None:
        return

    detector, aruco_dict, params, api_mode = tracker.build_detector()
    print(f"[OK] ArUco detector ready ({api_mode} API)\n")
    token_cache = tracker.TokenCache()
    hq_cache    = tracker.HqCache()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] Failed to read frame — check camera.")
                break

            cc, p1_live, p2_live, turn_angle, hq_raw, raw = tracker.detect_frame(
                frame, detector, aruco_dict, params, api_mode
            )
            H = tracker.compute_homography(cc)

            p1 = token_cache.resolve_side("p1", p1_live, H)
            p2 = token_cache.resolve_side("p2", p2_live, H)

            # Resolve HQ marker positions (with stale cache)
            hq_markers = {
                "p1": hq_cache.resolve("p1", hq_raw, H),
                "p2": hq_cache.resolve("p2", hq_raw, H),
            }

            # If a fresh HQ marker is visible, update the game model's HQ position
            # so the server's shot-resolution uses the physically placed HQ.
            for side, info in hq_markers.items():
                if not info["stale"] and info["col"] is not None:
                    if side == "p1":
                        session.model.hq_p1 = (info["col"], info["row"])
                    else:
                        session.model.hq_p2 = (info["col"], info["row"])

            turn = tracker.turn_from_angle(turn_angle)
            events = session.model.on_turn_change(turn, p1, p2) if turn else []

            await broadcast(_build_state(session, cc, p1, p2, turn, turn_angle,
                                         hq_markers, events))

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

                cv2.imshow("yu_test3 tracker (press q to quit)", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            await asyncio.sleep(0.01)
    finally:
        cap.release()
        if show_window:
            cv2.destroyAllWindows()


async def demo_loop(session: DemoSession):
    """Demo mode: cycle through scripted states, auto-advance every 6 s."""
    print("[DEMO] Running demo mode — press N in browser to step through states.")
    last_broadcast = 0
    while True:
        now = time.time()
        if now - last_broadcast >= 0.25:   # 4 fps is plenty
            await broadcast(session.current())
            last_broadcast = now
        await asyncio.sleep(0.1)


async def idle_loop(session: Session):
    """No-camera mode: broadcast state driven by action messages from the client."""
    print("[OK] Running in --no-camera mode. Token placement via UI actions.")
    hq_empty = {"p1": {"col": None, "row": None, "stale": True},
                "p2": {"col": None, "row": None, "stale": True}}
    while True:
        p1_raw, p2_raw = session.model.get_token_positions()
        events = list(session.model.last_events)
        session.model.last_events = []
        await broadcast(_build_state(
            session, {"_": 1, "__": 2, "___": 3, "____": 4},  # fake 4 corners
            p1_raw, p2_raw,
            session.model.current_turn, None,
            hq_empty, events,
        ))
        await asyncio.sleep(0.1)


def _build_state(session, cc, p1, p2, turn, turn_angle, hq_markers, events):
    # Augment raw token dicts with model-derived data (kills, upgrade, protecting…)
    aug_p1 = session.model.augment_tokens("p1", p1)
    aug_p2 = session.model.augment_tokens("p2", p2)

    state = {
        "phase":         "game",
        "corners_found": len(cc),
        "turn":          turn,
        "turn_angle":    round(turn_angle, 1) if turn_angle is not None else None,
        "battle":        {"active_side": f"p{turn}" if turn else None},
        "p1":            aug_p1,
        "p2":            aug_p2,
        "hq_markers":    hq_markers,
        "terrain":       session.terrain,
        "map_seed":      session.seed,
        "game":          session.model.snapshot(),
        "events":        events,
        "setup": {
            "board_scan_ready": len(cc) == 4,
            "hq": {
                "p1": {"confirmed": session.model.hq_p1 is not None, "has_candidate": False},
                "p2": {"confirmed": session.model.hq_p2 is not None, "has_candidate": False},
            },
        },
    }
    if session.tutorial_ctrl:
        state["tutorial"] = session.tutorial_ctrl.tick(p1, p2, turn, hq_markers)
    return state


# ─── Main ─────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="yu_test4 dev server")
    p.add_argument("--demo",         action="store_true",
                   help="Run scripted demo — no camera or live_rules needed.")
    p.add_argument("--no-camera",   action="store_true",
                   help="Skip camera; just run frontend + idle WS broadcasts.")
    p.add_argument("--camera-index", type=int, default=0,
                   help="Webcam device index (default 0).")
    p.add_argument("--no-window",    action="store_true",
                   help="Hide the OpenCV preview window (default: shown).")
    p.add_argument("--ws-port",      type=int, default=8765)
    p.add_argument("--http-port",    type=int, default=8080)
    p.add_argument("--tutorial",     action="store_true",
                   help="Run in tutorial mode with fixed seed and guided steps.")
    return p.parse_args()


async def main():
    args = parse_args()

    if not FRONTEND_DIR.is_dir():
        print(f"[ERROR] Frontend dir missing: {FRONTEND_DIR}")
        return

    start_http_server(args.http_port, FRONTEND_DIR)
    print(f"[UI] Open browser -> http://localhost:{args.http_port}")

    if args.demo:
        session = DemoSession()
        print(f"[WS] Demo mode on  ws://localhost:{args.ws_port}")
        print(f"[DEMO] {len(session.states)} stages — press N in browser to step, auto-cycles every 6 s\n")
        handler = functools.partial(ws_handler, session=session)
        async with websockets.serve(handler, WS_HOST, args.ws_port):
            await demo_loop(session)
        return

    if not _LIVE_RULES:
        print("[ERROR] live_rules not found. Run with --demo for UI testing without the game engine.")
        return

    session = Session(tutorial_mode=args.tutorial)
    mode_str = " [TUTORIAL MODE]" if args.tutorial else ""
    print(f"[WS] Game state on  ws://localhost:{args.ws_port}{mode_str}\n")

    handler = functools.partial(ws_handler, session=session)
    async with websockets.serve(handler, WS_HOST, args.ws_port):
        if args.no_camera:
            await idle_loop(session)
        else:
            await camera_loop(session, args.camera_index, show_window=not args.no_window)


if __name__ == "__main__":
    print("=== yu_test3 dev server ===")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[bye]")
