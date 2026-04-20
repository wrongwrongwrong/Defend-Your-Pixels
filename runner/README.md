# Runner

Purpose
- provide a minimal, clear set of runner entrypoints for the current project stage
- keep startup/orchestration separate from tracking and transport code

Naming convention
- `run_<mode>.py`
- `live_tracker` means the integrated runtime used by the bridge/frontend flow
- `old_mick_core_smoke` means a fast rules-validation smoke test for the MVP

Entry points
- `run_live_tracker.py`: full live tracker + websocket transport
- `run_old_mick_core_smoke.py`: authoritative backend smoke test for the Old Mick MVP ruleset
