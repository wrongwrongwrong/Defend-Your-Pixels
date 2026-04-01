# Python Tracker

Purpose
- camera input and debug tools
- ArUco marker detection
- board calibration and coordinate mapping
- tracker-side experiments

Structure
- `camera/`: camera open/configure/release helpers
- `debug/`: debug-only camera preview scripts
- `marker_detection/`: marker detection logic and marker preview entrypoints
- `token_detection/`: token-specific detection logic and future rotation helpers
- `calibration/`: calibration notes and future homography helpers
- `board_mapping/`: camera-to-board coordinate conversion prototypes
- `state_output/`: tracker snapshot builders and preview payload helpers
- `markers/`: marker generation tools
- `experiments/`: older or exploratory scripts kept for reference only

Runtime model
- `python_tracker/` owns camera, marker, calibration, mapping, and tracker snapshot logic.
- `bridge/` owns schema and transport.
- `runner/` owns system startup.
