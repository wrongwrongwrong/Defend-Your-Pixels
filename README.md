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

### Marker review only

From `D:\Defend-Your-Pixels`:

```bash
.venv\Scripts\python -m runner.run_marker_preview
```
