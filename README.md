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

### Recommended: start frontend + live tracker together

From the repo root:

Recommended on Windows: use `launch_live_demo.cmd` by double-clicking it in File Explorer.

```powershell
powershell -ExecutionPolicy Bypass -File .\launch_live_demo.ps1
```

This starts:
- the Python live tracker
- `yu_test1/index.html` in your default browser

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
- starts the live camera + WebSocket stack in a new PowerShell window
- opens `yu_test1/index.html` automatically in your default browser

Notes:
- If PowerShell execution policy blocks scripts, use `launch_live_demo.cmd` instead of running the `.ps1` file directly.
- Close the tracker by focusing the camera preview window and pressing `Q`, or by closing the spawned PowerShell window.
- `yu_test1/index.html` is opened as a local file. No `npm install`, Vite, or frontend dev server is required.

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

### Start separately

Run both commands from the repo root.

Browser:

```bash
start yu_test1\index.html
```

Terminal 2, from `D:\Defend-Your-Pixels`:

```bash
.venv\Scripts\python -m runner.run_live_tracker
```

Notes:
- You can open the browser before or after starting Python. The page will retry the WebSocket connection automatically.
- `start yu_test1\index.html` is a Windows Command Prompt / PowerShell command.
- If you are already inside the repo root in PowerShell, `ii .\yu_test1\index.html` also works.

## Supported runner entrypoints

The project currently keeps only two runner entrypoints:

- `runner.run_live_tracker`: full runtime for camera -> tracker -> yu_test1 rules -> websocket -> `yu_test1/index.html`
- `runner.run_old_mick_core_smoke`: fast rules-validation smoke test for the Old Mick MVP
