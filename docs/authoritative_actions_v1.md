# Authoritative Actions v1

This document defines the action messages sent from the browser frontend, tracker, or bridge to the authoritative Python model.

## Current status

- The currently implemented authoritative gameplay actions are `end_turn`, `move_unit`, and `attack_in_direction`.
- The live Old Mick setup flow also accepts `choose_side`, `set_hq_candidate`, `confirm_hq`, and the optional setup reset aliases `reset_setup` and `cancel_hq`.
- The live path is primarily marker-driven during setup and battle.
- `upgrade_unit` is out of scope for the current integration prototype.
- `move_unit` intents may currently come from either the tracker flow or the browser frontend.

## WebSocket message

```json
{
  "type": "action",
  "data": {
    "action": "end_turn"
  }
}
```

## Implemented actions

### `choose_side`

Purpose: choose which faction places its HQ first once the board scan is ready.

```json
{
  "action": "choose_side",
  "first_player_side": "old_mick"
}
```

Python behavior:

- Accepted only after the board scan is ready and before the runtime reaches `game`.
- Stores `first_player_side`.
- Records the first player and maintains or enters `hq_placement`.

The `yu_test3` mainline frontend can send this action from its side-selection flow.

### `set_hq_candidate`

Purpose: submit an HQ candidate for the currently active setup side.

```json
{
  "action": "set_hq_candidate",
  "side": "p1",
  "position": { "x": 3, "y": 4 }
}
```

Python behavior:

- Validates that the HQ is on the correct side and not on the fence.
- Stores the candidate in backend session state when valid.
- Exposes only `has_candidate` and `confirmed` through the public payload.

This action is mainly kept for fallback or debug paths. In the live marker flow, `ID11` and `ID21` update the active side's HQ candidate automatically, and the frontend does not show exact HQ coordinates in the side panel.

### `confirm_hq`

Purpose: confirm the current side's HQ candidate.

```json
{
  "action": "confirm_hq",
  "side": "p1"
}
```

Python behavior:

- Locks the HQ if that side already has a candidate.
- Transfers setup control to the other side after the first confirmation.
- Emits `hq_setup_complete` and enters `game` after both HQs are confirmed.
- Keeps confirmed HQ coordinates hidden from normal gameplay payloads.

This action is mainly kept for fallback or debug paths. In the live marker flow, `ID4` performs the equivalent confirmation when the active side has a valid HQ candidate.

### `reset_setup`

Purpose: reset the current pre-game HQ setup.

```json
{
  "action": "reset_setup"
}
```

The live frontend may expose this through fallback or debug setup controls during `hq_placement`.

### `cancel_hq`

Purpose: compatibility alias for `reset_setup`.

```json
{
  "action": "cancel_hq"
}
```

### `end_turn`

Purpose: request authoritative turn progression and broadcast the latest `board_state`.

```json
{
  "action": "end_turn"
}
```

Expected result:

- Python performs authoritative turn progression.
- `turn`, `active_player`, `move_countdown`, and related state are updated in Python.
- The new `board_state` is broadcast to the browser frontend.

### `move_unit`

Purpose: submit a unit destination and let Python validate and apply the move.

```json
{
  "action": "move_unit",
  "unit_id": "u0",
  "position": { "x": 4, "y": 3 }
}
```

Current status:

- Implemented in the Python backend.
- May be produced by tracker-derived move intent.
- May also be sent directly by the browser frontend.

Python behavior:

- Validates `unit_id` and `position`.
- Calls `GameState.move_unit_to(...)`.
- Broadcasts an updated `board_state` on success.
- Updates `last_action` on failure.

### `attack_in_direction`

Purpose: perform a straight-line attack in one of eight directions, letting Python resolve the first valid target and hard-terrain blocking.

```json
{
  "action": "attack_in_direction",
  "unit_id": "u0",
  "direction": "up_right"
}
```

Python behavior:

- Validates `unit_id` and `direction`.
- Calls `GameState.attack_in_direction(...)`.
- Searches for the first valid enemy target along the chosen direction.
- Fails if hard terrain blocks the line first.
- Updates HQ or resource-tile state and `last_action` on success.

## Actions excluded from v1

### `upgrade_unit`

Reason:

- The current prototype is focused on completing the authoritative integration path first.
- Upgrade rules are intentionally deferred.

Current policy:

- The UI does not expose upgrade in the backend-driven path.
- Python does not currently implement upgrade rules.

## Tracker relationship

The tracker should produce gameplay intent, not directly overwrite authoritative state.

Target flow:

1. `tracker snapshot`
2. derive `move_unit` or other action intent
3. Python validates and applies the action
4. Python emits a new `board_state`

## Live marker battle flow

The current live battle path does not primarily use browser-sent `end_turn` actions.

- `ID10` and `ID20` open positioning for `p1` or `p2`.
- The active side's token-marker positions and rotations become that turn's candidate state.
- `ID4` submits the active side and triggers authoritative attack resolution immediately.
- After resolution, the runtime waits for the opposing side's `ID10` or `ID20`.

In other words, the live marker path is currently marker-driven rather than explicit action-driven for turn submission.

## Setup flow note

Pre-game setup and the live tracker flow currently use a backend-first session state machine:

- `scan`
- `side_selection` for fallback or debug paths
- `hq_placement`
- `game`

During `game`, inactive-side token movement is ignored and surfaced as `inactive_side_token_changed` rather than mutating the authoritative state.
