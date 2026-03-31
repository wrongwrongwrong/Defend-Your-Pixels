# Repo Structure

## Top-level folders

- `python_tracker/`: Python tracking pipeline and experiments
- `bridge/`: transport layer from Python to frontend
- `react_frontend/`: Vite + React visualization client
- `docs/`: architecture and reference notes

## Internal layout

- `python_tracker/debug/`: basic camera and preview scripts
- `python_tracker/detection/`: ArUco detection entry points
- `python_tracker/calibration/`: board mapping and coordinate conversion prototypes
- `python_tracker/markers/`: marker generation tools
- `python_tracker/experiments/`: reference and exploratory tracker code
- `react_frontend/src/app/`: app-level container components
- `react_frontend/src/components/board/`: board and zone rendering
- `react_frontend/src/components/entities/`: token and unit rendering
- `react_frontend/src/components/hud/`: HUD and status components
- `react_frontend/src/hooks/bridge/`: backend connection hooks
- `react_frontend/src/game/`: frontend-side game rules and constants

## Notes

- `main.cpp` stays at the repository root on purpose.
- It is retained as the original C++ reference that informed the Python conversion work.
- This is useful both for implementation traceability and for explaining the code origin during interviews.
