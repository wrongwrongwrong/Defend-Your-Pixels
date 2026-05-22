# Architecture Overview

## Purpose

This document describes the current system architecture for Old Mick and the Emus and explains the responsibilities and boundaries between the major components.

## System Summary

Old Mick and the Emus is a camera-assisted board game with a browser UI.

The Python side is authoritative for game state. The browser is a live renderer and control surface. Marker input and browser commands both feed into the same runtime session.

## High-Level Data Flow

```text
camera
  -> python_tracker
  -> runner session
  -> live_rules.game_model
  -> bridge.transport.websocket_transport
  -> run_live_tracker HTTP/WebSocket server
  -> frontend/index.html
```

No-camera paths reuse the same rules and browser frontend but replace camera input with terminal commands or browser-driven token placement.

## Component Responsibilities

### `backend/python_tracker`

Responsibility:

- camera access
- ArUco marker detection
- board corner scan and calibration
- snapshot/state extraction for the live runtime

This layer should not own game rules. It converts physical observations into structured runtime input.

### `backend/live_rules`

Responsibility:

- authoritative gameplay state
- turn resolution
- HQ hiding and reveal rules
- terrain generation
- win conditions and battle events

Canonical file:

- `backend/live_rules/game_model.py`

This is the primary source of truth for match state.

### `backend/bridge`

Responsibility:

- accept browser WebSocket connections
- queue inbound actions
- broadcast serialized state to connected clients

Canonical file:

- `backend/bridge/transport/websocket_transport.py`

This layer should not implement game rules or browser rendering logic.

### `runner`

Responsibility:

- assemble the current runtime mode
- own session lifecycle
- combine tracker input, rules, setup flow, tutorial flow, and transport
- expose supported entrypoints

Primary entrypoints:

- `runner/run_live_tracker.py`
- `runner/run_manual_play.py`

Optional testing entrypoint:

- `runner/run_browser_manual_play.py`

### `frontend`

Responsibility:

- render the live game state
- provide browser-side UI interactions
- display setup flow, board state, tutorial state, and result overlays
- send commands through the shared browser WebSocket client

Canonical files:

- `frontend/index.html`
- `frontend/src/main.js`
- `frontend/src/scenes/GameScene.js`
- `frontend/src/ui.js`

The frontend is not authoritative for game state.

### `protocol`

Responsibility:

- document the browser/server transport shape
- provide the shared browser client wrapper used by the frontend

Canonical files:

- `protocol/websocket/browser_client.js`
- `protocol/websocket/contract.md`

## Authoritative State Ownership

The runtime treats Python as the single source of truth.

That means:

- battle resolution happens in Python
- win state is decided in Python
- hidden HQ coordinates are stored in Python
- the browser reflects state and submits allowed commands

This architecture avoids frontend/backend drift and makes it easier to keep physical-marker input and browser input consistent.

## Runtime Modes

### Supported

- `run_live_tracker.py`
  - camera + tracker + authoritative rules + browser frontend
- `run_manual_play.py`
  - no camera, terminal-driven input, same browser frontend and rules model

### Optional or specialized

- `run_browser_manual_play.py`
  - browser-click testing path for manual controls
- `run_demo_mode.py`
  - limited or experimental/demo-oriented flow; not the primary documented runtime

## Phase Model

At the public payload level, the current runtime may expose:

- `mode_select`
- `scan`
- `hq_placement`
- `game`

The backend controls phase transitions. The frontend renders phase state but does not decide it.

## Software Engineering Considerations

### Separation of concerns

- tracker code is separate from rules code
- rules code is separate from transport code
- transport code is separate from browser rendering
- runners compose the system without owning core rules

### Clear authority boundaries

- Python decides match state
- browser code displays and requests actions
- tracker code reports observations, not final truth

### Reusable transport and frontend integration

- the browser talks through `protocol/websocket/browser_client.js`
- transport wrapping is centralized instead of duplicated across scenes

### Safe hidden information handling

- HQ coordinates stay hidden after setup
- only safe setup metadata is exposed publicly
- HQ positions are revealed only through explicit gameplay outcomes

### Support for multiple input sources

- live tracker mode: camera-driven positioning and confirm markers
- manual mode: terminal-driven input
- browser manual mode: browser-click token control

The rules model remains shared across these paths.

## Practical Edit Guide

If you need to change:

- camera or marker behavior: start in `backend/python_tracker/`
- setup or battle rules: start in `backend/live_rules/`
- WebSocket flow: start in `backend/bridge/` and `protocol/`
- runtime assembly: start in `runner/`
- UI behavior or overlays: start in `frontend/src/`

## Related Documents

- `docs/board_state_v1.md`
- `docs/authoritative_actions_v1.md`
- `docs/setup_flow_backend_v1.md`
- `docs/manual_play.md`
- `README_PROJECT_MAP.md`
