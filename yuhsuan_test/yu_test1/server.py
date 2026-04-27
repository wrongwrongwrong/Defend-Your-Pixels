"""
Old Mick Against the Mob — tracker server (thin orchestrator).

Responsibilities:
  - Open camera, detect markers each frame  (tracker.py)
  - Generate / regenerate random terrain      (terrain_gen.py)
  - Drive the authoritative game model        (game_model.py)
  - Broadcast merged state via WebSocket

Design: every module above is small and independently testable.
This file is only the glue.

WebSocket commands accepted from clients:
  { "type": "new_map" }                    reset terrain + game
  { "type": "tier",    player: 1|2, delta: ±1 }
"""

import asyncio
import json
import time
import cv2
import websockets

import tracker
import terrain_gen
import game_model

WS_HOST, WS_PORT = "localhost", 8765
USE_WEBCAM   = True
WEBCAM_INDEX = 0
PHONE_IP     = "172.16.11.211"
PHONE_PORT   = 4747


# ─── Game session (terrain + model) ────────────────────────────────────────────

class Session:
    def __init__(self):
        self.reset()

    def reset(self):
        self.seed    = int(time.time() * 1000) % (2 ** 31)
        self.terrain = terrain_gen.generate(seed=self.seed)
        self.model   = game_model.new_game(self.terrain, seed=self.seed)
        print(f"[MAP] New game (seed={self.seed}) "
              f"HQ p1={self.model.hq_p1} p2={self.model.hq_p2}")


session = Session()
token_cache = tracker.TokenCache()


# ─── Camera ────────────────────────────────────────────────────────────────────

def open_camera():
    source = WEBCAM_INDEX if USE_WEBCAM else f"http://{PHONE_IP}:{PHONE_PORT}/video"
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open camera: {source}")
        return None
    print(f"[OK] Camera opened: {source}")
    return cap


# ─── WebSocket ─────────────────────────────────────────────────────────────────

connected: set = set()


async def ws_handler(websocket):
    connected.add(websocket)
    print(f"[WS] Client connected  ({len(connected)} total)")
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
                        session.model.tier_p1 = max(1, min(4, session.model.tier_p1 + d))
                    else:
                        session.model.tier_p2 = max(1, min(4, session.model.tier_p2 + d))
            except (json.JSONDecodeError, KeyError, ValueError):
                pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected.discard(websocket)
        print(f"[WS] Client disconnected ({len(connected)} total)")


async def broadcast(data: dict):
    if not connected:
        return
    msg = json.dumps(data)
    await asyncio.gather(*[c.send(msg) for c in connected])


# ─── Main loop ─────────────────────────────────────────────────────────────────

async def camera_loop():
    cap = open_camera()
    if cap is None:
        return

    detector, aruco_dict, params, api_mode = tracker.build_detector()
    print(f"[OK] ArUco detector ready ({api_mode} API)\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Failed to read frame — check camera.")
            break

        cc, p1_live, p2_live, turn_angle, help_angle = tracker.detect_frame(
            frame, detector, aruco_dict, params, api_mode
        )
        H = tracker.compute_homography(cc)

        p1 = token_cache.resolve_side("p1", p1_live, H)
        p2 = token_cache.resolve_side("p2", p2_live, H)
        turn = tracker.turn_from_angle(turn_angle)
        help_page = tracker.help_page_from_angle(help_angle)

        # Turn transition → resolve attacks (authoritative game logic)
        events = session.model.on_turn_change(turn, p1, p2) if turn else []

        state = {
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
            "help":          {"active": help_page is not None,
                              "page":   help_page,
                              "angle":  round(help_angle, 1) if help_angle is not None else None},
        }
        await broadcast(state)

        # Camera overlay
        cv2.putText(frame, f"Corners: {len(cc)}/4", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (0, 255, 0) if len(cc) == 4 else (0, 100, 255), 2)
        if turn is not None:
            cv2.putText(frame, f"Turn: P{turn}", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 220, 0), 2)
        g = session.model
        cv2.putText(frame, f"Destroyed P1={g.snapshot()['score_p1_destroyed']} "
                           f"P2={g.snapshot()['score_p2_destroyed']}",
                    (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 180, 100), 1)
        if g.winner:
            cv2.putText(frame, f"WINNER: {g.winner.upper()} ({g.win_reason})",
                        (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        cv2.imshow("Old Mick Tracker", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
        await asyncio.sleep(0.01)

    cap.release()
    cv2.destroyAllWindows()


async def main():
    print("=== Old Mick Against the Mob — Tracker Server ===")
    print(f"WebSocket : ws://{WS_HOST}:{WS_PORT}")
    print(f"Camera    : {'webcam (index 0)' if USE_WEBCAM else f'{PHONE_IP}:{PHONE_PORT}'}")
    print(f"Attrition : {game_model.ATTRITION_THRESHOLD} cells to win\n")
    async with websockets.serve(ws_handler, WS_HOST, WS_PORT):
        await camera_loop()


if __name__ == "__main__":
    asyncio.run(main())
