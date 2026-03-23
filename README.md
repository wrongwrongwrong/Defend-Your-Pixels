# Defend-Your-Pixels
technical feasibility test

Setup
- This project uses `./.venv/`.

Install
- `./setup.sh`

Run
- `source .venv/bin/activate`
- `python3 pixel_defense_tracker/main.py`
- `python3 pixel_defense_tracker/detect_aruco.py`

If you see `ModuleNotFoundError: No module named 'cv2'`
- Check interpreter:
  `python -c "import sys; print(sys.executable)"`
- Reinstall in this env:
  `python -m pip install -r requirements.txt`

If OpenCV says camera access is denied (macOS)
- Enable Camera for the app launching Python (Terminal/Cursor).
- If needed: `tccutil reset Camera`
