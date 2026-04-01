# Defend-Your-Pixels
technical feasibility test

Current repo structure
- `python_tracker/`: camera, ArUco detection, board mapping, tracker experiments
- `bridge/`: Python to frontend transport layer
- `react_frontend/`: React visualization and test frontend
- `docs/`: architecture and code provenance notes
- `main.cpp`: preserved C++ reference implementation used during Python conversion

Setup
- This project uses `./.venv/`.

Install (from a terminal in the repo root — **do not rely on double‑clicking** `setup.sh`; macOS often opens it in an editor instead of running it)

```bash
cd /path/to/Defend-Your-Pixels
chmod +x setup.sh   # first time only
./setup.sh
```

This installs `requirements.txt`, then **editable** `pip install -e .` so `python_tracker`, `bridge`, and `model_backend` import from any working directory.

Run
- `source .venv/bin/activate`
- **Pygame PVP prototype:** `python3 -m prototype_pygame.main`
- **Pygame single-player range/attack test:** `python3 -m prototype_pygame.single_player_main`
- `python3 runner/run_camera_preview.py`
- `python3 runner/run_marker_preview.py`
- `python3 runner/run_live_tracker.py`

Frontend
- `cd react_frontend`
- `npm install`
- `npm run dev`

If you see `ModuleNotFoundError: No module named 'cv2'`
- Check interpreter:
  `python -c "import sys; print(sys.executable)"`
- Reinstall in this env:
  `python -m pip install -r requirements.txt`

If OpenCV says camera access is denied (macOS)
- Enable Camera for the app launching Python (Terminal/Cursor).
- If needed: `tccutil reset Camera`
