# Runner

Purpose
- provide a minimal, clear set of runner entrypoints for the current project stage
- keep startup/orchestration separate from tracking and transport code

Naming convention
- `run_<mode>.py`
- `live_tracker` means the integrated runtime used by the bridge/frontend flow
- `manual_play` means the no-camera runtime for local frontend and rules testing

Entry points
- `run_live_tracker.py`: full live runtime for `camera -> python_tracker -> shared live rules -> websocket -> HTTP -> frontend/index.html`
- `run_manual_play.py`: no-camera manual runtime for local frontend and rules testing

Notes
- `run_live_tracker.py` is the supported live entrypoint for the current game flow.
- The live browser UI is served from `frontend/index.html` on `http://localhost:8080` by default.
- No Node, Vite, or separate frontend dev server is required for the live path.
