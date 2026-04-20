# Defend Your Pixels - Project Map

This document explains the current repository in simple terms for new team members.

## What this project is

Defend Your Pixels is a hybrid vision-based AR board game.  
The system uses a camera to detect board markers and tokens, converts those detections into game positions, updates game logic, and sends the latest game state to a frontend.

## High-level data flow

1. Camera captures frames.
2. Vision module detects ArUco markers.
3. Tracker maps marker positions to board/grid coordinates.
4. Backend game model applies actions and updates authoritative state.
5. Bridge sends tracker and board state over WebSocket.
6. Frontend receives messages and renders the game.

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
Purpose: game rules and authoritative state management.

Includes:
- Board state model
- Rule handling and actions
- Serialization of game state for transport

Use this when you need to change game logic (movement, turns, actions, captures).

### `bridge`
Purpose: connect tracker + model + frontend.

Includes:
- WebSocket transport
- Message schemas/contracts
- Adapters that convert tracker events into model actions

Use this when you need to change real-time communication or message formats.

### `react_frontend`
Purpose: user interface for the game.

Includes:
- React app and components
- WebSocket hook/client
- Board state adapters for UI rendering

Use this when you need to change what users see or how UI updates.

### `runner`
Purpose: clean startup scripts for runtime modes.

Important scripts:
- `run_live_tracker.py`: integrated runtime path
- `run_old_mick_core_smoke.py`: fast backend rules smoke test

Use this folder first when running demos and checks.

### `docs`
Purpose: project documentation and integration notes.

Includes protocol documents and architecture references.

### `archive` / `game-logic` / `dyp` (context)
- `archive`: older or reference material
- `game-logic`: legacy/experimental logic area
- `dyp`: local environment package directory

These are not primary runtime entrypoints for the current architecture.

## Recommended "where to start" order

1. Root `README.md`
2. `runner/README.md`
3. Run `runner/run_live_tracker.py` or `runner/run_old_mick_core_smoke.py`
4. Read `python_tracker` basics
5. Read `bridge` flow
6. Read `model_backend` state/actions
7. Read frontend socket hook and board adapter

## Quick glossary

- **Authoritative state**: the single source of truth for game state.
- **Tracker frame**: latest camera-derived board/token info.
- **Board state**: serialized game state sent to frontend.
- **Bridge**: transport and synchronization layer between modules.

