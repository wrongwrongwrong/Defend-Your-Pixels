# Runner

Purpose
- provide a single, clear way to start each runtime mode
- keep startup/orchestration separate from tracking and transport code
- avoid using `python_tracker/experiments/` as accidental runtime entrypoints

Naming convention
- `run_<mode>.py`
- `preview` means a debug-only visual check
- `live_tracker` means the integrated runtime used by the bridge/frontend flow

Entry points
- `run_camera_preview.py`: raw camera preview only
- `run_marker_preview.py`: marker detection preview only
- `run_live_tracker.py`: full live tracker + websocket transport
