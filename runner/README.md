# Runner Entry Points

This folder contains the runtime entrypoints that assemble the current application.

## Purpose

- keep runtime assembly separate from tracker, rules, transport, and frontend code
- expose the supported ways to launch the project
- hold session/setup orchestration that belongs above the core model layer

## Naming Convention

- entrypoints follow `run_<mode>.py`
- shared support modules keep `snake_case.py`

## Supported Entry Points

### `run_live_tracker.py`

Status: primary supported runtime

Use when:

- running the real camera-driven game
- validating the full end-to-end flow
- demonstrating the current board setup and live frontend

Responsibilities:

- consume tracker output
- manage setup and battle session state
- serve `frontend/` over HTTP
- host the WebSocket transport
- broadcast authoritative state to the browser

### `run_manual_play.py`

Status: supported no-camera runtime

Use when:

- testing the frontend without a camera
- testing rules or setup flow from the terminal
- validating state and event behavior without marker input

Responsibilities:

- replace tracker input with terminal commands
- keep the same authoritative rules and frontend payload shape

## Optional Testing Entry Point

### `run_browser_manual_play.py`

Status: optional testing helper

Use when:

- you want browser-click token placement quickly
- you want to bypass the full marker-driven setup path for UI testing

This runner is useful, but it is not the primary live play path.

## Support Modules

- `setup_flow.py`: pre-game setup state machine and token validation rules
- `frontend_static_server.py`: serves the frontend and protocol files over HTTP
- `port_check.py`: basic launch-time port validation

## Relationship To Other Folders

- `backend/python_tracker/` provides vision and board-state observations
- `backend/live_rules/` provides authoritative rules
- `backend/bridge/` provides WebSocket transport
- `frontend/` provides the browser UI that runners serve and feed

## Launch Guidance

For full setup and operator instructions, use `README.md`.

For manual/no-camera details, use `docs/manual_play.md`.
