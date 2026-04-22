# Setup Flow Backend v1

## Purpose

This document defines the backend-first pre-game setup flow for the live Old Mick runtime.

The goal is to stop the match from starting immediately after board scan and require:

1. board scan readiness
2. side selection
3. sequential HQ placement with confirmation
4. transition into normal gameplay

## Phases

The runtime now uses explicit backend phases:

- `scan`
- `side_selection`
- `hq_placement`
- `game`

## Flow

### `scan`

The backend remains in `scan` until the board marker map is usable.

Requirements:

- camera opens successfully
- board corner markers are readable enough to build calibration

### `side_selection`

Once the board scan is ready, the session waits for a side choice.

The backend stores:

- whether the first setup player chose `old_mick` or `mob`
- which board side acts first during HQ setup

### `hq_placement`

After side selection, each side places an HQ in sequence.

Rules:

- only the active setup side may place or confirm an HQ
- HQ must be on that side's own territory
- HQ cannot be placed on the fence line
- HQ is not final until confirmation

### `game`

The runtime transitions to `game` only after both HQ locations are confirmed.

At that point:

- the authoritative `GameModel` is created with the chosen HQ locations
- the normal turn loop resumes
- the public payload still keeps HQ coordinates hidden

## Hidden HQ rule

HQ locations are selected during setup but remain hidden after confirmation.

The backend stores the true HQ coordinates internally.
The live payload must not expose confirmed HQ coordinates during normal play.
HQ positions are only revealed when destroyed through the existing `hq_revealed` output.

## Active-turn token protection

During `game`, only the active side's tokens may change position or direction.

If the inactive side's physical markers move accidentally during the other side's turn:

- the backend ignores the change
- the previously accepted token state remains authoritative
- the backend emits `inactive_side_token_changed`

## Territory and direction validation

Board ownership uses:

- `c + r < 11` => `p1`
- `c + r > 11` => `p2`
- `c + r == 11` => fence

Runtime validations:

- HQ must be placed on the correct side and not on the fence
- Old Mick tokens cannot be placed on the Mob side or on the fence
- Mob tokens cannot be placed on the Old Mick side or on the fence
- Old Mick attack tokens may only aim `E`, `SE`, `S`, `SW`
- Mob attack tokens may only aim `W`, `NW`, `N`, `NE`

## Payload additions

The runtime keeps the existing payload shape and adds:

- `phase`
- `setup`
- `errors`

Example safe setup payload:

```json
{
  "phase": "hq_placement",
  "setup": {
    "board_scan_ready": true,
    "side_selection_complete": true,
    "first_player_side": "old_mick",
    "active_setup_side": "p2",
    "hq": {
      "p1": { "has_candidate": true, "confirmed": true },
      "p2": { "has_candidate": false, "confirmed": false }
    },
    "status_code": "waiting_for_hq_candidate",
    "status_message": "The Mob must choose an HQ location."
  },
  "errors": []
}
```

## New setup actions

### `choose_side`

```json
{
  "action": "choose_side",
  "first_player_side": "old_mick"
}
```

### `set_hq_candidate`

```json
{
  "action": "set_hq_candidate",
  "side": "p1",
  "position": { "x": 3, "y": 4 }
}
```

### `confirm_hq`

```json
{
  "action": "confirm_hq",
  "side": "p1"
}
```

### `reset_setup`

Optional recovery action to restart HQ placement before or after a partially completed setup.

## Error and status catalog

### `camera_unavailable`

`Cannot detect the camera. Check the camera connection and configured camera index.`

### `marker_map_scan_failed`

`Cannot locate the board markers. Make sure all four board corner markers are visible and readable.`

### `token_detection_failed`

`Cannot detect one or more attack or defence tokens. Reposition the markers and try again.`

### `hq_wrong_side`

`HQ must be placed on that side's own territory and not on the fence.`

### `hq_setup_complete`

`Both HQ locations are confirmed. Starting the game.`

### `old_mick_token_invalid_zone`

`Old Mick tokens must stay on the Old Mick side and cannot be placed on the fence.`

### `mob_token_invalid_zone`

`Mob tokens must stay on the Mob side and cannot be placed on the fence.`

### `old_mick_attack_direction_invalid`

`Old Mick attack tokens can only aim East, South-East, South, or South-West.`

### `mob_attack_direction_invalid`

`Mob attack tokens can only aim West, North-West, North, or North-East.`

### `inactive_side_token_changed`

`Only the active player's tokens may move during this turn. The opponent token change was ignored.`
