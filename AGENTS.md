# Agents

## Project overview

AR board game: camera detects ArUco markers, Python tracker/model computes game state, bridge streams over WebSocket to React frontend.

Data flow: `camera → tracker → bridge → react_frontend`

Python is authoritative for game state. `model_backend` owns rules. `bridge` owns transport. `python_tracker` owns vision. `runner/` assembles the live app.

## Setup

```bash
chmod +x setup.sh && ./setup.sh          # first time only
source .venv/bin/activate
pip install -e .                         # editable install — required so python_tracker, bridge, model_backend import from anywhere
```

The venv is `.venv/` (not `venv`). The editable install packages `python_tracker`, `bridge`, and `model_backend`.

## Running

**Python (always from repo root, with `.venv` active):**
```bash
python3 runner/run_live_tracker.py            # live tracker + WS server + cv2 preview
python3 runner/run_old_mick_core_smoke.py     # backend rules smoke test
```

**Frontend:**
```bash
cd react_frontend && npm install && npm run dev
```

## Architecture notes

- `main.cpp` at root is a preserved C++ reference — do not use as runtime entry.
- `game-logic/` is legacy; use `model_backend/` for game rules.
- `archive/` and `dyp/` are not primary runtime paths.
- Python bridge naming: `*_schema.py` (contract), `*_adapter.py` (conversion), `*_transport.py` (network).
- Authoritative payload uses `snake_case` (`units[]`, `hp`, `max_hp`); React adapter converts to UI `camelCase`.

## Type checking

Python: `pyright` (config in `pyrightconfig.json`, venv path `.venv`).
React: `npm run lint` in `react_frontend/`.

## Testing

No pytest/unittest framework is configured in this repository.

## Cameras / OpenCV

If `ModuleNotFoundError: No module named 'cv2'`, check `python -c "import sys; print(sys.executable)"` matches `.venv/bin/python`. Reinstall with `pip install -r requirements.txt`.

On macOS, if camera access is denied: enable Camera for the app launching Python (Terminal/Cursor), or run `tccutil reset Camera`.

## Key entry points

| File | Purpose |
|------|---------|
| `runner/run_live_tracker.py` | Full live system: camera → tracker → model → bridge → WS |
| `bridge/actions/model_action_dispatcher.py` | Routes `action` messages to model methods |
| `bridge/adapters/` | Tracker frame → WS message conversion |
| `model_backend/game/` | Game state, rules, actions |
| `react_frontend/src/bridge/adaptBoardStateToUi.js` | snake_case → UI shape adapter |
| `react_frontend/src/hooks/bridge/` | WS connection and board-state hooks |

## Existing instruction files

- `CONTRIBUTING.md` — naming conventions, file responsibility, PR checklist
- `docs/board_state_v1.md` — authoritative state contract (snake_case payload)
- `docs/authoritative_actions_v1.md` — action types and their Python-side behavior
- `MIGRATION_PLAN.md` — planned refactor toward `apps/` / `packages/` structure
- `README_PROJECT_MAP.md` — high-level data flow and folder purposes
