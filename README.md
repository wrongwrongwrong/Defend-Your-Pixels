# Defend Your Pixels

AR tabletop prototype: **camera / marker tracking**, a **Python game prototype**, optional **WebSocket bridge**, and **React** or **Pygame** clients for visualization and playtesting.

---

## Setup — use the section for **your** OS

Jump to the instructions that match your machine:

| System | Section |
|--------|---------|
| **macOS** or **Linux** | [Setup: macOS and Linux](#setup-macos-and-linux) |
| **Windows** (PowerShell or Command Prompt) | [Setup: Windows](#setup-windows) |
| **Windows** but you already use **Git Bash** or **WSL** | [Setup: Git Bash or WSL](#setup-git-bash-or-wsl) (same shell commands as macOS/Linux) |

---

### Setup: macOS and Linux

From a terminal **at the repo root** (adjust the path):

```bash
cd "/path/to/Defend-Your-Pixels"  # replace with your clone path
chmod +x setup.sh    # first time only
./setup.sh           # creates .venv, installs requirements.txt, pip install -e .
source .venv/bin/activate
```

If double-clicking `setup.sh` opens it in an editor on macOS, run the commands above in Terminal instead.

---

### Setup: Windows

Use **Command Prompt** or **PowerShell** at the repo root. Example path — change to where you cloned the project:

**Command Prompt (`cmd.exe`):**

```bat
cd C:\path\to\Defend-Your-Pixels
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

**PowerShell:**

```powershell
cd C:\path\to\Defend-Your-Pixels
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

If `Activate.ps1` is blocked by execution policy, either run the **Command Prompt** block above, or (one-time, current user):

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Use `py -3 -m venv .venv` instead of `python -m venv .venv` if the `python` command is missing but the Python launcher is installed.

---

### Setup: Git Bash or WSL

From the repo root, you can use the Bash script:

```bash
cd "/c/path/to/Defend-Your-Pixels"  # Git Bash: replace with your clone path
chmod +x setup.sh
./setup.sh
source .venv/bin/activate
```

On **WSL**, paths look like `/mnt/c/Users/.../Defend-Your-Pixels`.

---

## Quick start — React UI

Same on **macOS**, **Linux**, and **Windows** after [Node.js](https://nodejs.org/) is installed:

```bash
cd react_frontend
npm install
npm run dev
```

Open the URL Vite prints (usually `http://localhost:5173`).

- **Windows path example:** `cd C:\path\to\Defend-Your-Pixels\react_frontend`
- **macOS path example:** `cd ~/Downloads/Defend-Your-Pixels/react_frontend`

---

## What lives where

| Path | Role |
|------|------|
| **`model_backend/`** | Rules engine: `game/` (state, board, units, pixels, win conditions). Imports as `model_backend`. |
| **`prototype_pygame/`** | **Playable Pygame client** using the same model; ASCII levels in `levels/`. Good for local PVP/solo testing. |
| **`python_tracker/`** | Camera, ArUco detection, homography, board mapping, tracker snapshot output. |
| **`bridge/`** | Schemas, adapters, WebSocket transport between tracker/model and clients. |
| **`runner/`** | Small **`run_*.py`** entrypoints (camera preview, marker preview, live tracker). |
| **`react_frontend/`** | Vite + React board/HUD; consumes tracker/bridge messages via `src/bridge/`. |
| **`docs/`** | Architecture notes, integration checkpoints, board-state docs; includes **`testing marker.pdf`** (print test sheet). |
| **`docs/Reference/`** | **`main.cpp`** — original C++ reference for the Python port. |
| **`assets/`** | **`Board.jpg`** — photo of the physical board (reference). |
| **`markers/`** | Generated / reference marker images for print and detection. |
| **`archive/`** | Older UI reference copy; not required for normal development. |

**Editable install:** `pip install -e .` (after the setup steps above) exposes `model_backend`, `prototype_pygame`, `python_tracker`, and `bridge` as packages (`pyproject.toml`).

More detail: [`docs/repo_structure.md`](docs/repo_structure.md).

---

## Run commands (with venv **activated**)

Use **`python`** on Windows; **`python3`** is common on macOS/Linux (either works if they point to the same venv).

### Pygame prototypes (recommended for gameplay)

| Command | Purpose |
|---------|---------|
| `python -m prototype_pygame.main` | PVP-style prototype (loads `prototype_pygame/levels/level1.txt`). |
| `python -m prototype_pygame.single_player_main` | Solo range / interaction check. |

You can also run `prototype_pygame/main.py` directly; it adjusts `sys.path` so imports work.

### Rules-only demo (no UI)

| Command | Purpose |
|---------|---------|
| `python -m model_backend.run_model_demo` | Tiny scripted sequence against `GameState`. |

### Tracker & live pipeline

| Command | Purpose |
|---------|---------|
| `python runner/run_camera_preview.py` | Raw camera preview. |
| `python runner/run_marker_preview.py` | Marker detection preview. |
| `python -m runner.run_live_tracker` | Live tracker + embedded WebSocket server (see below). |

See [`runner/README.md`](runner/README.md) for naming conventions.

### Full live stack — **one terminal** (optional)

From **`react_frontend/`**, you can run **Vite + live tracker** together (uses [concurrently](https://www.npmjs.com/package/concurrently)). You still need **Python venv** at the repo root (with `cv2`, editable install, etc.) and **`npm install`** in `react_frontend` once.

```bash
cd "/path/to/Defend-Your-Pixels/react_frontend"   # replace with your clone path (Windows example: D:\Defend-Your-Pixels\react_frontend)
npm install
npm run dev:live
```

- **Stop both:** press `Ctrl+C` once (processes are tied; `-k` stops the other if one exits).
- The helper **`scripts/run-live-tracker.cjs`** (repo root) picks **`.venv`**’s Python when it exists, so you do not need to `activate` the venv for this command.

### Full live stack — **two terminals** (manual)

Same stack as above, split across two shells if you prefer. `run_live_tracker` starts the WebSocket server **inside the same process** as the camera loop—you do **not** run a separate `websocket_server` for this flow.

| Terminal | OS example `cd` | Command |
|----------|------------------|---------|
| **A — React UI** | macOS/Linux (example): `cd ~/Downloads/Defend-Your-Pixels/react_frontend`<br>macOS/Linux (placeholder): `cd /path/to/Defend-Your-Pixels/react_frontend` (replace with your clone path)<br>Windows: `cd D:\Defend-Your-Pixels\react_frontend` | `npm install` (once), then `npm run dev` |
| **B — Live tracker** | macOS/Linux (example): `cd ~/Downloads/Defend-Your-Pixels`<br>macOS/Linux (placeholder): `cd /path/to/Defend-Your-Pixels` (replace with your clone path)<br>Windows: `cd D:\Defend-Your-Pixels` | Activate venv, then `python -m runner.run_live_tracker` |

Then open the URL Vite prints (e.g. `http://localhost:5173`). The tracker prints the WebSocket URL (default `ws://localhost:8765`).

**Windows (Cmd), terminal B:**

```bat
cd D:\Defend-Your-Pixels
.venv\Scripts\activate.bat
python -m runner.run_live_tracker
```

**macOS/Linux, terminal B:**

```bash
cd "/path/to/Defend-Your-Pixels"  # replace with your clone path
source .venv/bin/activate
python -m runner.run_live_tracker
```

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'prototype_pygame'`**  
Run from the **repo root** with `python -m prototype_pygame.main`, and ensure `pip install -e .` completed inside the venv.

**`ModuleNotFoundError: No module named 'cv2'`**  
Confirm the venv: `python -c "import sys; print(sys.executable)"`, then `python -m pip install -r requirements.txt`.

**Camera / permissions**

- **macOS:** Grant camera to Terminal / Cursor; if needed: `tccutil reset Camera`.
- **Windows:** Allow camera access for Python / your terminal in **Settings → Privacy → Camera**.

**`npm run dev` fails**  
Run `npm install` inside `react_frontend` first. Check paths: backslashes on Windows (`\`), forward slashes on macOS/Linux (`/`).
