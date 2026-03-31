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

Install
- `./setup.sh`

Run
- `source .venv/bin/activate`
- `python3 python_tracker/experiments/main.py`
- `python3 python_tracker/detection/detect_aruco.py`
- `python3 bridge/websocket_server.py`

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
