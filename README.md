# Old Mick and the Emus

Old Mick and the Emus is a hybrid AR board game prototype.

The physical game uses printed ArUco markers on a board. A Python tracker reads the camera feed, converts marker positions into board state, applies authoritative game rules, and streams the live match to a browser frontend over WebSocket.

`camera -> tracker -> live rules -> bridge -> HTTP/WebSocket -> frontend`

## Who This Repository Is For

- Players or demo operators who want to set up and run the prototype
- Developers working on the tracker, live rules, browser UI, or transport layer
- Reviewers who need a clear overview of the architecture and documentation set

## Requirements

- Python `3.10+`
- A modern desktop browser
- A working camera for the live tracker path
- Printed board markers from `markers/`
- A local Python virtual environment in `.venv/`

Notes:

- No Node, Vite, or separate frontend dev server is required for the main runtime.
- The frontend is served directly by the Python runner.

## First-Time Setup

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

### Windows Command Prompt

```cmd
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -e .
```

### macOS

Recommended:

```bash
chmod +x setup.sh
./setup.sh
```

Manual setup:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m pip install -e .
```

Why `pip install -e .` matters:

- It installs the backend packages in editable mode.
- It lets modules such as `python_tracker`, `bridge`, `live_rules`, and `runner` import correctly from the project root and runtime entrypoints.

## Launch The Main Game

### Windows

Recommended:

- Double-click `launch_live_demo.cmd`

Alternative:

```powershell
powershell -ExecutionPolicy Bypass -File .\launch_live_demo.ps1
```

### macOS

Recommended:

```bash
chmod +x launch_live_demo.command
./launch_live_demo.command
```

### Direct Python Launch

With `.venv` active, from the repository root:

```bash
python -m runner.run_live_tracker
```

Then open:

```text
http://localhost:8080
```

What this starts:

- the Python live tracker
- the authoritative live rules session
- the built-in HTTP server for `frontend/`
- the WebSocket server used by the browser UI

## Main Runtime Modes (outside of using launch command)

### Supported live runtime

- `runner.run_live_tracker`
- Uses the camera, tracker, live rules, and browser frontend together
- This is the main path for demos and real board play

### Supported no-camera runtime

- `runner.run_manual_play`
- Keeps the same browser frontend and authoritative rules
- Replaces camera-driven input with terminal commands
- Useful for local frontend and rules testing

Additional runner details are in `runner/README.md`.

## Physical Board And Marker Setup

This project has two layers that must stay aligned:

- digital layer: browser UI and authoritative game state
- physical layer: board, tokens, and printed markers seen by the camera

### Marker Inventory

| ID | Side | Role | Used during | Purpose |
|----|------|------|-------------|---------|
| `0` | Shared | `BOARD CORNER` | Scan, setup, gameplay | Top-left calibration corner |
| `1` | Shared | `BOARD CORNER` | Scan, setup, gameplay | Top-right calibration corner |
| `2` | Shared | `BOARD CORNER` | Scan, setup, gameplay | Bottom-left calibration corner |
| `3` | Shared | `BOARD CORNER` | Scan, setup, gameplay | Bottom-right calibration corner |
| `4` | Shared | `CONFIRM` | Setup, gameplay | Confirms HQ setup and submits battle turns |
| `5` | Shared | `HELP` | Setup, gameplay | Shows the help overlay while visible |
| `10` | P1 | `TURN` | Setup, gameplay | Opens P1 setup or positioning |
| `11` | P1 | `HQ` | Setup | Sets P1 HQ candidate |
| `12` | P1 | `ATK A` | Gameplay | P1 attacker A |
| `13` | P1 | `ATK B` | Gameplay | P1 attacker B |
| `14` | P1 | `DEF` | Gameplay | P1 defender |
| `19` | P1 | `NUKE` | Gameplay | P1 nuke targeting marker |
| `20` | P2 | `TURN` | Setup, gameplay | Opens P2 setup or positioning |
| `21` | P2 | `HQ` | Setup | Sets P2 HQ candidate |
| `22` | P2 | `ATK A` | Gameplay | P2 attacker A |
| `23` | P2 | `ATK B` | Gameplay | P2 attacker B |
| `24` | P2 | `DEF` | Gameplay | P2 defender |
| `29` | P2 | `NUKE` | Gameplay | P2 nuke targeting marker |

### Board Setup Summary

1. Place the board flat on a stable surface.
2. Place board-corner markers `0`, `1`, `2`, and `3` in the correct corners.
3. Position the camera so the full board and all four corners are visible together.
4. Keep lighting even and reduce glare, shadowing, and heavy occlusion.
5. Keep printed markers flat, readable, and facing the camera.
6. Avoid moving the board or corner markers once scan and play begin.

Detailed setup flow documentation is in `docs/setup_flow_backend_v1.md`.

### Gameplay
Please refer to the game_design_documentation and the markers folder for gameplay explanation.


_______________________________________________________
###### Developer Navigation

Start here if you are new to the codebase:

1. `README.md`
2. `docs/README.md`
3. `docs/architecture.md`
4. `README_PROJECT_MAP.md`
5. `runner/README.md`

Key implementation areas:

- `backend/python_tracker/`: camera, marker detection, calibration, tracker snapshot
- `backend/live_rules/`: authoritative game logic and terrain generation
- `backend/bridge/`: WebSocket transport and message flow
- `frontend/src/`: Phaser scenes, HUD, audio, and browser interaction
- `protocol/`: shared browser protocol helper and transport notes
- `runner/`: runtime entrypoints and orchestration

## Canonical Documentation

- `docs/README.md`: documentation index and status guide
- `docs/architecture.md`: system architecture and component responsibilities
- `docs/dependencies_and_licenses.md`: external dependencies and known licensing data
- `README_PROJECT_MAP.md`: repository structure and "where to edit what"
- `CONTRIBUTING.md`: naming, commenting, and documentation conventions

## Notes For Reviewers

- The browser reconnects to the current backend session after refresh; it does not automatically start a new match.
- The `Play Again` flow returns the UI to mode selection only; it does not reset the session until the replay action is sent.
- Some older design and planning materials remain in the repository but are not the canonical documentation path. `docs/README.md` identifies which documents are current, reference-only, or archival.
