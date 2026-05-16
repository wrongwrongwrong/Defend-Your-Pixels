# Agents

## Project overview

AR board game: camera detects ArUco markers, Python tracker/model computes game state, bridge streams over WebSocket to the live frontend.

Data flow: `camera -> tracker -> bridge -> run_live_tracker HTTP/WS -> frontend/index.html`

Python is authoritative for game state. `backend/live_rules/game_model.py` owns the live rules. `backend/bridge` owns transport. `backend/python_tracker` owns vision. `runner/` assembles the live app. `backend/model_backend` remains in the repo for legacy/smoke-test paths.

## Setup

```bash
chmod +x setup.sh && ./setup.sh          # first time only
source .venv/bin/activate
pip install -e .                         # editable install — required so backend packages import from anywhere
```

The venv is `.venv/` (not `venv`). The editable install packages backend modules such as `python_tracker`, `bridge`, `live_rules`, and `model_backend`.

## Running

**Python (always from repo root, with `.venv` active):**
```bash
python3 runner/run_live_tracker.py            # live tracker + WS/HTTP server + cv2 preview
python3 runner/run_old_mick_core_smoke.py     # backend rules smoke test
```

**Frontend:**
```bash
open http://localhost:8080 in a browser
```

Windows notes:
- Double-click `launch_live_demo.cmd` from the repo root for the simplest local launch.
- `launch_live_demo.ps1` starts the tracker in a new PowerShell window and opens `http://localhost:8080` automatically.
- The frontend is served directly by `run_live_tracker.py`, so no Node/Vite frontend server is required.

## Architecture notes

- Python bridge naming: `*_schema.py` (contract), `*_adapter.py` (conversion), `*_transport.py` (network).
- The live frontend is `frontend/index.html`, served by `run_live_tracker.py`, and it consumes the flat live runtime payload directly.

## Type checking

Python: `pyright` (config in `pyrightconfig.json`, venv path `.venv`).

## Testing

No pytest/unittest framework is configured in this repository.

## Cameras / OpenCV

If `ModuleNotFoundError: No module named 'cv2'`, check `python -c "import sys; print(sys.executable)"` matches `.venv/bin/python`. Reinstall with `pip install -r requirements.txt`.

On macOS, if camera access is denied: enable Camera for the app launching Python (Terminal/Cursor), or run `tccutil reset Camera`.

## Key entry points

| File | Purpose |
|------|---------|
| `runner/run_live_tracker.py` | Full live system: camera -> tracker -> shared live rules -> WS/HTTP |
| `backend/python_tracker/state_output/tracker_snapshot.py` | Tracker snapshot, homography fallback, marker stability |
| `backend/bridge/transport/websocket_transport.py` | WebSocket server + inbound UI commands |
| `backend/live_rules/game_model.py` | Live game rules used by the browser UI |
| `frontend/index.html` | The primary live frontend |

## Existing instruction files

- `CONTRIBUTING.md` — naming conventions, file responsibility, PR checklist
- `docs/board_state_v1.md` — authoritative state contract (snake_case payload)
- `docs/authoritative_actions_v1.md` — action types and their Python-side behavior
- `README_PROJECT_MAP.md` — high-level data flow and folder purposes
