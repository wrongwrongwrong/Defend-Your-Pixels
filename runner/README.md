# Runner

Purpose
- provide a minimal, clear set of runner entrypoints for the current project stage
- keep startup/orchestration separate from tracking and transport code

Naming convention
- `run_<mode>.py`
- `live_tracker` means the integrated runtime used by the bridge/frontend flow
- `old_mick_core_smoke` means a fast rules-validation smoke test for the MVP

Entry points
- `run_live_tracker.py`: full live runtime for `camera -> python_tracker -> yu_test1 rules -> websocket -> yu_test1/index.html`
- `run_old_mick_core_smoke.py`: authoritative backend smoke test for the Old Mick MVP ruleset

Notes
- `run_live_tracker.py` is the supported live entrypoint for the current game flow.
- The live browser UI is `yu_test1/index.html`.
- No Node, Vite, or frontend dev server is required for the live path.
