# Board State v1

This document describes the current authoritative runtime payload broadcast from Python to the browser frontend.

Python is the authoritative source of truth. The browser consumes the payload and renders UI state from it.

## Transport Summary

- The WebSocket server broadcasts a full JSON state object.
- The payload is not wrapped in a `{ "type", "data" }` envelope.
- If `events` is present and non-empty, the browser treats it as a companion event batch for animation and audio.

For transport details, also see `protocol/websocket/contract.md`.

## Top-Level Payload Shape

The current runtime payload is centered on session state rather than the older `players[]` / `units[]` example shape.

Typical top-level fields:

```json
{
  "phase": "game",
  "mode": "normal",
  "corners_found": 4,
  "turn": 1,
  "turn_angle": 0.0,
  "p1": {},
  "p2": {},
  "hq_markers": {},
  "terrain": {},
  "map_seed": 123456,
  "game": {},
  "events": [],
  "setup": {},
  "battle": {},
  "help_visible": false,
  "errors": []
}
```

Optional fields include:

- `tutorial`
- `manual_controls`

## Phase Values

The current public payload may expose:

- `mode_select`
- `scan`
- `hq_placement`
- `game`

Meaning:

- `mode_select`: no mode has been locked yet; show the intro mode buttons
- `scan`: waiting for a valid board scan in the live tracker path
- `hq_placement`: hidden HQ setup is active
- `game`: battle runtime is active

## Core Top-Level Fields

| Field | Meaning |
|------|---------|
| `phase` | Current public runtime phase |
| `mode` | `null`, `normal`, or `tutorial` |
| `corners_found` | Number of visible board corners in the current snapshot |
| `turn` | Public turn indicator where used by the current runtime |
| `turn_angle` | Turn-marker angle if available |
| `p1`, `p2` | Accepted token state for each side |
| `hq_markers` | Live HQ marker preview state during setup |
| `terrain` | Generated terrain/resources for the current map |
| `map_seed` | Terrain seed for the current session |
| `game` | Authoritative game model snapshot |
| `events` | One-tick event batch used for frontend animation/audio |
| `setup` | Safe setup metadata |
| `battle` | Public battle-flow state |
| `help_visible` | Whether the help overlay should be shown |
| `errors` | Recoverable runtime or validation issues |

## Side Token State

`p1` and `p2` each contain token slots:

- `atk_a`
- `atk_b`
- `def`

Each token slot is typically shaped like:

```json
{
  "col": 3,
  "row": 5,
  "angle": 45.0,
  "direction": "SE",
  "stale": false
}
```

`null`-like values are used when a token is not currently placed or visible.

## Setup Metadata

`setup` exposes safe progress state only. Confirmed hidden HQ coordinates must not be exposed during normal play.

Important fields:

- `board_scan_ready`
- `side_selection_complete`
- `first_player_side`
- `active_setup_side`
- `hq.p1.has_candidate`
- `hq.p1.confirmed`
- `hq.p2.has_candidate`
- `hq.p2.confirmed`
- `status_code`
- `status_message`

During `mode_select`, the runtime still includes `setup`, but its message should be treated as mode-selection guidance rather than active setup instructions.

## Battle Metadata

`battle` describes the public state of turn submission and nuke targeting.

Important fields:

- `active_side`
- `waiting_for_side`
- `status_code`
- `status_message`
- `turn_marker_id`
- `confirm_marker_id`
- `nuke_marker_id`
- `pending_nuke`

`pending_nuke` is either `null` or:

```json
{
  "side": "p1",
  "col": 8,
  "row": 6,
  "marker_id": 19
}
```

## Game Snapshot

`game` is the authoritative state exported from `backend/live_rules/game_model.py`.

Important fields include:

- `destroyed`
- `damage`
- `hard_damage`
- `hard_gone`
- `soft_damage`
- `soft_gone`
- `score_p1_destroyed`
- `score_p2_destroyed`
- `score_p1_remaining_cells`
- `score_p2_remaining_cells`
- `tier_p1`
- `tier_p2`
- `atk_destroyed_counts`
- `atk_tiers`
- `def_tier_p1`
- `def_tier_p2`
- `nuke_available_p1`
- `nuke_available_p2`
- `nuke_used_p1`
- `nuke_used_p2`
- `winner`
- `win_reason`
- `hq_revealed`
- `def_anchor_cells`
- `def_consumed_cells`

## Events

`events` is a transient batch used mainly for frontend animation and audio.

Examples include:

- `ray_complete`
- `cell_damaged`
- `cell_destroyed`
- `hard_hit`
- `hard_destroyed`
- `soft_hit`
- `soft_destroyed`
- `hq_destroyed`
- `attrition_win`
- `nuke_triggered`
- `attack_result`

These events complement the state payload; they do not replace authoritative state.

## Errors

`errors` contains stable objects shaped like:

```json
{
  "code": "board_not_scanned",
  "message": "Waiting for a valid board scan."
}
```

Use `errors` for recoverable validation or tracker issues rather than as a substitute for state.

## Optional Tutorial And Manual Fields

- `tutorial`: present when tutorial mode exposes tutorial-step data to the frontend
- `manual_controls`: present in manual/browser-manual runtimes to enable browser token interaction affordances

## Hidden Information Rule

- HQ coordinates are selected during setup.
- Confirmed HQ coordinates remain hidden during normal play.
- `game.hq_revealed` is the public path for HQ coordinates only after gameplay reveals them.

## Historical Note

Older documents in this repository reference a more abstract `players[]`, `resource_tiles[]`, and `units[]` shape. Those examples are no longer the canonical runtime payload for the current browser frontend and should be treated as historical or reference-only material.
