# Python Tracker

Purpose
- camera input and debug tools
- ArUco marker detection
- board calibration and coordinate mapping

Structure
- `camera/`: camera open/configure/release helpers
- `debug/`: debug-only camera preview scripts
- `marker_detection/`: marker detection logic and marker preview entrypoints
- `token_detection/`: token-specific detection logic and future rotation helpers
- `calibration/`: homography-based pixel-to-grid mapping helpers
- `state_output/`: tracker snapshot builders and preview payload helpers
- `markers/`: marker generation tools

Runtime model
- `python_tracker/` owns camera, marker, calibration, and tracker snapshot logic.
- `bridge/` owns schema and transport.
- `runner/` owns system startup.
