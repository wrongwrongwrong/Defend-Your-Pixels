# Defend Your Pixels

## Start Up

### First-time setup

At the repo root:

```bash
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pip install -e .
```

Then install frontend dependencies:

```bash
cd react_frontend
npm install
```

### Recommended: start frontend + live tracker together

From `Defend-Your-Pixels\react_frontend`:

```bash
npm run dev:live
```

This starts:
- the React frontend
- the Python live tracker

### Windows demo launcher

From the repo root, you can also start the live demo with one double-click:

- `launch_live_demo.cmd` (recommended)

If you prefer PowerShell directly:

- `launch_live_demo.ps1`

Or run it from PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\launch_live_demo.ps1
```

This launcher:
- checks `.venv\Scripts\python.exe`
- checks `react_frontend\node_modules`
- starts the live UI + camera stack in a new PowerShell window
- opens `http://localhost:5173` automatically when the UI is ready

### Backend rules smoke test

From `D:\Defend-Your-Pixels`:

```bash
.venv\Scripts\python -m runner.run_old_mick_core_smoke
```

This validates the current Old Mick MVP core rules:
- directional line attack hits the first valid target
- hard terrain blocks attacks
- defender protection requires two hits on protected resource tiles
- destroying the enemy HQ ends the game immediately

### Two-screen mirrored UI

After `npm run dev:live`, open two browser windows:

- `http://localhost:5173/?view=p1`
- `http://localhost:5173/?view=p2`

Recommended setup:

- move the `?view=p1` window to Player 1's monitor
- move the `?view=p2` window to Player 2's monitor
- fullscreen both windows

`?view=p2` mirrors the board so Player 2 sees their own side as the local/home edge.

More detail:

- `docs/dual_screen_ui_setup.md`

### Start separately

Terminal 1, from `Defend-Your-Pixels\react_frontend`:

```bash
npm run dev
```

Terminal 2, from `D:\Defend-Your-Pixels`:

```bash
.venv\Scripts\python -m runner.run_live_tracker
```

## Supported runner entrypoints

The project currently keeps only two runner entrypoints:

- `runner.run_live_tracker`: full runtime for camera -> tracker -> backend -> websocket -> frontend
- `runner.run_old_mick_core_smoke`: fast rules-validation smoke test for the Old Mick MVP
