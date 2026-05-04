# Defend Your Pixels - Project Map

This document explains the current repository in simple terms for new team members.

## What this project is

Defend Your Pixels is a hybrid vision-based AR board game.  
The system uses a camera to detect board markers and tokens, converts those detections into game positions, updates game logic, and sends the latest game state to a frontend.

## High-level data flow

1. Camera captures frames.
2. Vision module detects ArUco markers.
3. Tracker maps marker positions to board/grid coordinates.
4. Runtime game model updates authoritative state.
5. Bridge sends live state over WebSocket.
6. `yu_test3/frontend/index.html` receives messages and renders the game.

## Current top-level folders

### `python_tracker`
Purpose: computer vision pipeline.

Includes:
- Camera runtime
- Marker detection (ArUco)
- Board calibration and homography
- Tracker snapshot/state output

Use this when you need to work on camera input, marker detection, or coordinate mapping.

### `model_backend`
Purpose: legacy and smoke-test rules code.

Includes:
- Board state model
- Rule handling and actions
- Serialization of game state for transport

Use this when you need to change the older backend prototype or smoke tests.

### `bridge`
Purpose: connect tracker + runtime model + frontend.

Includes:
- WebSocket transport
- Inbound browser action handling
- Runtime broadcast helpers

Use this when you need to change real-time communication or message formats.

### `live_rules`
Purpose: authoritative live rules and terrain generation shared by the current runtimes.

Includes:
- `game_model.py` authoritative live rules
- `terrain_gen.py` shared live map generation

Use this when you need to change live gameplay rules or the shared terrain generator.

### `yu_test3`
Purpose: the primary live browser frontend.

Includes:
- `frontend/index.html` main browser entrypoint
- `frontend/src/` modular Phaser scenes, HUD, audio, and WS client

Use this when you need to change the shipped live UI or frontend flow.

### `runner`
Purpose: clean startup scripts for runtime modes.

Important scripts:
- `run_live_tracker.py`: integrated runtime path
- `run_old_mick_core_smoke.py`: fast backend rules smoke test

Use this folder first when running demos and checks.

### `docs`
Purpose: project documentation and integration notes.

Includes protocol documents and architecture references.

### `archive` (context)
- `archive`: older or reference material

This is not a primary runtime entrypoint for the current architecture.

## Recommended "where to start" order

1. Root `README.md`
2. `runner/README.md`
3. Run `runner/run_live_tracker.py` or `runner/run_old_mick_core_smoke.py`
4. Read `python_tracker` basics
5. Read `bridge` flow
6. Read `model_backend` state/actions
7. Read `yu_test3/frontend/src/`

## Quick glossary

- **Authoritative state**: the single source of truth for game state.
- **Tracker frame**: latest camera-derived board/token info.
- **Board state**: serialized game state sent to frontend.
- **Bridge**: transport and synchronization layer between modules.
