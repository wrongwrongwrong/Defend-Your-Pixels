# Repository Project Map

This document explains where the current responsibilities live in the repository.

Use it after reading the root `README.md` and `docs/architecture.md`.

## Recommended Reading Order

1. `README.md`
2. `docs/README.md`
3. `docs/architecture.md`
4. `README_PROJECT_MAP.md`
5. `runner/README.md`

## Top-Level Structure

### `backend/python_tracker/`

Responsibility:

- camera access
- ArUco marker detection
- board calibration and coordinate mapping
- tracker snapshot generation

Work here when changing physical-board detection or calibration behavior.

### `backend/live_rules/`

Responsibility:

- authoritative game rules
- terrain generation
- win conditions
- damage, HQ, DEF, and nuke resolution

Key files:

- `game_model.py`
- `terrain_gen.py`
- `tutorial.py`

This folder owns gameplay truth.

### `backend/bridge/`

Responsibility:

- WebSocket transport
- client connection handling
- inbound action queueing
- outbound state broadcasting

Key files:

- `transport/websocket_transport.py`

This folder should stay transport-focused.

### `frontend/`

Responsibility:

- browser entrypoint
- Phaser scenes
- HUD and DOM-driven status UI
- frontend audio and overlays
- browser asset loading

Key files:

- `index.html`
- `src/main.js`
- `src/scenes/IntroScene.js`
- `src/scenes/GameScene.js`
- `src/ui.js`
- `src/audio.js`

### `protocol/`

Responsibility:

- browser-side WebSocket helper
- transport contract notes shared across frontend work

Key files:

- `websocket/browser_client.js`
- `websocket/contract.md`

### `runner/`

Responsibility:

- supported runtime entrypoints
- orchestration between tracker, rules, setup flow, and frontend serving

Key files:

- `run_live_tracker.py`
- `run_manual_play.py`
- `run_browser_manual_play.py`
- `setup_flow.py`
- `frontend_static_server.py`

### `docs/`

Responsibility:

- canonical technical documentation
- contracts and architecture notes
- developer onboarding references

Start at `docs/README.md` to find the current source-of-truth documents.

### `markers/`

Responsibility:

- printable board and role marker assets used by the physical game

### Launch Scripts

Files:

- `launch_live_demo.cmd`
- `launch_live_demo.ps1`
- `launch_live_demo.command`
- `setup.sh`

These are operator/developer convenience scripts for bootstrapping or launching the supported runtime.

## Supported Entry Points

### Primary

- `python -m runner.run_live_tracker`

### Secondary but supported

- `python -m runner.run_manual_play`

### Optional testing flow

- `python -m runner.run_browser_manual_play`

## Source-Of-Truth Guide

If you need to know:

- setup instructions: `README.md`
- architecture and boundaries: `docs/architecture.md`
- current payload shape: `docs/board_state_v1.md`
- current accepted actions: `docs/authoritative_actions_v1.md`
- marker-driven setup flow: `docs/setup_flow_backend_v1.md`
- runner differences: `runner/README.md`
- naming and comment conventions: `CONTRIBUTING.md`

## Editing Guide

If a task involves:

- camera/tracker behavior: edit `backend/python_tracker/`
- game rules: edit `backend/live_rules/`
- WebSocket flow: edit `backend/bridge/` and `protocol/`
- runtime composition: edit `runner/`
- browser UI: edit `frontend/src/`
- documentation: edit `docs/`, `README.md`, or `CONTRIBUTING.md`

## Notes On Historical Material

Some older planning, GDD, and archive assets still exist in the repository. They are not the primary documentation path for the current runtime. Use `docs/README.md` to distinguish canonical documents from reference-only or historical materials.
