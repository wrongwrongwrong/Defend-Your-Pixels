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
