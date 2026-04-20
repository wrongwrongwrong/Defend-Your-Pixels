# Dual-Screen UI Setup

This document explains the recent board/UI changes for the live React frontend.

## What changed

The live React view now supports two important improvements:

1. Real player HQs are rendered on the board.
2. The frontend supports mirrored per-player views for a two-screen setup.

## Why this changed

Before this update:

- the React board only showed a neutral center marker
- HQ HP was only visible in the HUD
- there was no player-specific board orientation for two monitors

After this update:

- Python `board_state` includes each HQ position as authoritative data
- React renders each player's HQ on the board using that authoritative position
- `?view=p2` mirrors the board so Player 2 sees their side as the local/home edge

## New authoritative contract field

Each player entry in `board_state.players[]` now includes:

```json
{
  "command_tower_position": { "x": 5, "y": 11 }
}
```

This field is serialized by:

- `model_backend/serialization/board_state.py`

and adapted into React state by:

- `react_frontend/src/bridge/adaptBoardStateToUi.js`

## Board UI changes

### Real HQ rendering

The board now renders the actual player HQs using authoritative positions from Python.

Relevant files:

- `react_frontend/src/components/board/CommandTower.jsx`
- `react_frontend/src/components/board/Board.jsx`

### Midfield marker rename

The old board component named `HQ.jsx` was not a real HQ. It rendered a neutral center marker.

It has been renamed to:

- `react_frontend/src/components/board/MidfieldMarker.jsx`

This keeps the naming honest:

- `CommandTower.jsx` = real player HQ
- `MidfieldMarker.jsx` = neutral center board marker

### Mirrored board view

The frontend now supports two board orientations:

- `?view=p1` = Player 1 orientation
- `?view=p2` = Player 2 mirrored orientation

For the mirrored view, React flips:

- token positions
- HQ positions
- player zones
- click-to-cell mapping
- displayed facing directions
- displayed coordinate text in status strings

This logic lives in:

- `react_frontend/src/game/viewTransform.js`

## How to run the two-screen setup

### 1. Start the live app

From `react_frontend/`:

```bash
npm run dev:live
```

This starts:

- the Vite React frontend
- the Python live tracker/WebSocket runtime

### 2. Open one browser window per player

Open these URLs:

- `http://localhost:5173/?view=p1`
- `http://localhost:5173/?view=p2`

### 3. Move each window to its own monitor

Recommended:

- Monitor facing Player 1: `?view=p1`
- Monitor facing Player 2: `?view=p2`
- fullscreen both windows

## Current behavior notes

- Both windows connect to the same authoritative backend state.
- Both windows currently remain interactive.
- The mirrored effect is implemented in React display logic, not by rotating the entire page with CSS.

That means:

- text stays readable
- buttons stay upright
- board clicks still map back to authoritative coordinates correctly

## Setup note for the team

If someone opens the app without a query parameter, it defaults to:

- `?view=p1`

So for a proper two-monitor session, the team should always open both explicit URLs.

## Files changed for this UI update

Backend / contract:

- `model_backend/serialization/board_state.py`
- `docs/board_state_v1.md`
- `docs/frontend_backend_contract_v1.md`

Frontend state / rendering:

- `react_frontend/src/bridge/adaptBoardStateToUi.js`
- `react_frontend/src/game/turns.js`
- `react_frontend/src/game/viewTransform.js`
- `react_frontend/src/app/App.jsx`
- `react_frontend/src/components/board/Board.jsx`
- `react_frontend/src/components/board/CommandTower.jsx`
- `react_frontend/src/components/board/MidfieldMarker.jsx`
- `react_frontend/src/components/board/PlayerZone.jsx`
- `react_frontend/src/components/entities/Token.jsx`
- `react_frontend/src/components/entities/Unit.jsx`

Project docs:

- `README.md`
- `docs/dual_screen_ui_setup.md`

## Limitations still not solved by this change

- The React UI still does not draw a dedicated attack-line overlay.
- The React UI still does not draw a dedicated defender protection overlay.
- There is not yet a role-based lock that makes one screen display-only.
- Offline mock mode still has no authoritative HQ positions, so real HQs appear when backend state is connected.
