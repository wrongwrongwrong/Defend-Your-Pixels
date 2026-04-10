# Repo Structure

This file should help you distinguish between the folders that matter for the
current runtime and the folders that are only historical or experimental.

## Primary working set

- `runner/`: start here for real runtime entrypoints
- `python_tracker/`: camera, ArUco detection, calibration, board mapping
- `model_backend/`: authoritative game rules and serialization
- `bridge/`: adapters, schemas, WebSocket transport
- `react_frontend/`: Vite/React UI that consumes `board_state`

## Reference-only paths

- `main.cpp`: preserved C++ reference, not a runtime entrypoint
- `python_tracker/experiments/`: reference code, not primary runtime
- `game-logic/`: legacy prototype; current rules live in `model_backend/`
- `archive/`: historical material only
- `dyp/`: local environment artifacts, not source

## Top-level folders

- `python_tracker/`: Python tracking pipeline and experiments
- `bridge/`: transport layer from Python to frontend
- `model_backend/`: Python game-model / rules prototype
- `prototype_pygame/`: pygame prototype client for gameplay testing
- `react_frontend/`: Vite + React visualization client
- `runner/`: runtime entrypoints for tracker preview/live flows
- `docs/`: architecture and reference notes

## Internal layout

- `python_tracker/camera/`: camera runtime helpers
- `python_tracker/debug/`: basic camera and preview scripts
- `python_tracker/marker_detection/`: ArUco detection entry points
- `python_tracker/calibration/`: calibration and homography helpers
- `python_tracker/board_mapping/`: board-space mapping prototypes
- `python_tracker/state_output/`: tracker snapshot and preview helpers
- `python_tracker/markers/`: marker generation tools
- `python_tracker/experiments/`: reference-only and exploratory tracker code
- `bridge/schema/`: tracker frame contract
- `bridge/adapters/`: tracker snapshot to transport message conversion
- `bridge/transport/`: websocket transport runtime
- `model_backend/game/`: game state, board, unit, and rules logic
- `prototype_pygame/levels/`: ASCII map loaders and prototype scenarios
- `prototype_pygame/single_player_main.py`: single-player range/attack verification entrypoint
- `react_frontend/src/app/`: app-level container components
- `react_frontend/src/bridge/`: tracker translation helpers
- `react_frontend/src/components/board/`: board and zone rendering
- `react_frontend/src/components/entities/`: token and unit rendering
- `react_frontend/src/components/hud/`: HUD and status components
- `react_frontend/src/hooks/bridge/`: backend connection hooks
- `react_frontend/src/game/`: frontend-side game rules and constants

## Suggested cleanup structure

If you continue reorganizing for readability, this is the smallest clear target
structure that matches the current architecture without changing behavior:

```text
defend-your-pixels/
├─ runner/                 # runtime entrypoints only
├─ python_tracker/         # vision pipeline only
├─ model_backend/          # authoritative game model only
├─ bridge/                 # message adapters + websocket transport only
├─ react_frontend/         # UI only
├─ docs/                   # contracts, architecture, migration notes
├─ archive/                # old references kept out of runtime paths
└─ main.cpp                # preserved C++ reference
```

Within that structure, keep the rule that `runner/` assembles modules but does
not own business logic, and keep legacy/reference code out of new runtime work.

## Notes

- `main.cpp` stays at the repository root on purpose.
- It is retained as the original C++ reference that informed the Python conversion work.
- This is useful both for implementation traceability and for explaining the code origin during interviews.
