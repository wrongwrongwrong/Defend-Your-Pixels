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

### Launch live demo (Windows)

From the repo root:

Recommended on Windows: use `launch_live_demo.cmd` by double-clicking it in File Explorer.

```powershell
powershell -ExecutionPolicy Bypass -File .\launch_live_demo.ps1
```

This starts:
- the Python live tracker
- the built-in HTTP server for `frontend/`

### Launch live demo (macOS)

Recommended on macOS: use `launch_live_demo.command` (one-time: `chmod +x launch_live_demo.command`), then double-click it in Finder.

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
- starts the live camera + WebSocket + HTTP stack in a new PowerShell window
- opens `http://localhost:8080` in your default browser

Notes:
- If PowerShell execution policy blocks scripts, use `launch_live_demo.cmd` instead of running the `.ps1` file directly.
- Close the tracker by focusing the camera preview window and pressing `Q`, or by closing the spawned PowerShell window.
- `frontend/` is served directly by `run_live_tracker.py`. No `npm install`, Vite, or separate frontend dev server is required.

### Backend rules smoke test

From `D:\Defend-Your-Pixels`:

```bash
.venv\Scripts\python -m runner.run_old_mick_core_smoke
```

This validates the current Old Mick MVP core rules:
- directional line attack hits the first valid target
- terrain blocks attacks until destroyed: soft terrain takes 2 hits, hard terrain takes 5 hits
- defender protection requires two hits on protected resource tiles
- destroying the enemy HQ ends the game immediately

### Start separately

Run both commands from the repo root.

Browser:

```bash
start http://localhost:8080
```

Terminal 2, from `D:\Defend-Your-Pixels`:

```bash
.venv\Scripts\python -m runner.run_live_tracker
```

Notes:
- You can open the browser before or after starting Python. The page will retry the WebSocket connection automatically.
- `start http://localhost:8080` is a Windows Command Prompt / PowerShell command.

## Supported runner entrypoints

The primary runner entrypoints are:

- `runner.run_live_tracker`: full runtime for camera -> tracker -> shared live rules -> websocket -> HTTP -> `frontend/index.html`
- `runner.run_old_mick_core_smoke`: fast rules-validation smoke test for the Old Mick MVP

For a documented no-camera fallback, see `docs/manual_play.md` and `runner.run_manual_play`.
