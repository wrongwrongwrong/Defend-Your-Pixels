# yu_test2 — frontend visual rebuild (macOS dev environment)

Goal: combine the **prototype3 cinematic frontend** (Boot → Intro → Game scene flow,
typewriter story, side-selection cards, prototype3 colour palette) with the
**yu_test1 / FW2 backend** (resource scoring, tier system, hidden HQ, attrition).

This folder runs entirely on macOS via `python3 server.py` — no Windows-only
dependencies. The same frontend talks to the FW2 backend without changes.

## Run

```bash
cd yu_test2

# Full (camera + UI)
python3 server.py

# UI only — no webcam (great for visual iteration)
python3 server.py --no-camera

# Other flags
python3 server.py --camera-index 1 --show-window
python3 server.py --ws-port 8765 --http-port 8080
```

Then open http://localhost:8080

## What runs where

| Component        | Process              | Port  |
|------------------|----------------------|-------|
| WebSocket        | `server.py`          | 8765  |
| Static HTTP      | `server.py` (thread) | 8080  |
| Camera + ArUco   | `server.py`          | —     |
| Frontend (ES)    | Browser              | —     |

A single Python command brings up everything.

## Files

```
yu_test2/
├── server.py        ← WS + HTTP + camera (Mac/webcam)
├── tracker.py       ← ArUco detection + grid mapping + token cache
├── terrain_gen.py   ← (copied from yu_test1) random resource map
├── game_model.py    ← (copied from yu_test1) tiers, HQ, attrition
└── frontend/
    ├── index.html
    └── src/
        ├── main.js          (Phaser scene config)
        ├── constants.js     (board layout + prototype3 palette)
        ├── WSClient.js      (raw-state WS → synthetic events)
        └── scenes/
            ├── BootScene.js   (loading screen + WS handshake)
            ├── IntroScene.js  (story slides + side selection)
            └── GameScene.js   (board + HUD — gameplay layer pending)
```

## Status

- [x] Folder + backend logic copied from yu_test1
- [x] Mac dev `server.py` (WS + HTTP + optional webcam)
- [x] Phaser scene shell (Boot → Intro → Game)
- [x] BootScene + IntroScene fully ported from prototype3
- [x] GameScene visual baseline (board + HUD)
- [ ] Tokens, rays, damage overlays in GameScene
- [ ] Win banner, tier/nuke UI
- [ ] Audio polish

## Switching to FW2 backend

The frontend has no hard-coded server. Stop `server.py` and run the FW2
runtime instead — anything that publishes the same raw-state WS payload
on port 8765 will work.
