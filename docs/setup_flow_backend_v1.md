# Setup Flow Backend v1

This document defines the backend-first pre-game setup flow for the live Old Mick runtime.

## Phases

The runtime now moves through four explicit backend phases:

1. `scan`
2. `side_selection`
3. `hq_placement`
4. `game`

The backend remains authoritative for phase transitions.

## Phase transitions

1. Stay in `scan` until the camera is available and the board marker scan is usable.
2. Move to `side_selection` once the board scan is ready.
3. Move to `hq_placement` once `choose_side` is stored.
4. Move to `game` only after both HQ locations are confirmed.

## Setup actions

### `choose_side`

Choose which faction places its HQ first.

```json
{
  "action": "choose_side",
  "first_player_side": "old_mick"
}
```

### `set_hq_candidate`

Submit a candidate HQ cell for the currently active setup side.

```json
{
  "action": "set_hq_candidate",
  "side": "p1",
  "position": { "x": 3, "y": 4 }
}
```

### `confirm_hq`

Confirm the currently stored HQ candidate for that side.

```json
{
  "action": "confirm_hq",
  "side": "p1"
}
```

### Optional setup reset actions

```json
{ "action": "reset_setup" }
```

```json
{ "action": "cancel_hq" }
```

## Hidden HQ rule

HQ locations are selected during setup but remain hidden after confirmation.
The backend stores the true HQ coordinates internally.
The live payload must not expose confirmed HQ coordinates during normal play.
HQ positions are only revealed when destroyed through the existing `hq_revealed` output.

## Setup payload

The runtime payload includes safe setup metadata only:

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
    "status_code": "waiting_for_hq_confirmation",
    "status_message": "The Mob must choose and confirm an HQ location."
  },
  "errors": []
}
```

## Frontend placeholder rendering

`yu_test1/index.html` now renders a visual-only setup placeholder whenever `phase` is not `game`.

- `scan`: shows a setup status card and scan-waiting messaging
- `side_selection`: shows the setup card plus a board overlay for both territories and the fence line
- `hq_placement`: shows the setup card plus highlighted valid HQ territory, active setup side emphasis, and fence invalidation

The frontend currently consumes only safe setup metadata:

- `phase`
- `setup.status_message`
- `setup.board_scan_ready`
- `setup.side_selection_complete`
- `setup.first_player_side`
- `setup.active_setup_side`
- `setup.hq.*.has_candidate`
- `setup.hq.*.confirmed`

The placeholder does not expose confirmed HQ coordinates. It explicitly treats confirmed HQs as hidden until they are later revealed through gameplay.

The live browser frontend now also drives the setup flow:

- during `side_selection`, panel controls send `choose_side`
- during `hq_placement`, clicking a board cell sends `set_hq_candidate` for the active setup side
- during `hq_placement`, a confirm button sends `confirm_hq`
- during `hq_placement`, a restart button sends `reset_setup`

The browser may show a transient local candidate preview ring for the active side before confirmation. This preview is frontend-only and is cleared once the HQ is confirmed or setup resets.

The live frontend also surfaces `errors[]` as a temporary warning layover:

- one warning is chosen at a time using a stable frontend priority order
- repeated identical errors do not flicker every frame; they cycle with a short quiet gap before reappearing
- `inactive_side_token_changed` is presented as a recoverable warning only
- the warning explains that opponent movement was ignored; it does not change authoritative state on the frontend
- `hq_setup_complete` is rendered as a success-style alert instead of a warning-style alert

## Validation rules

- `c + r < 11` => `p1`
- `c + r > 11` => `p2`
- `c + r == 11` => fence
- HQ must be on its own side and not on the fence.
- Old Mick tokens must stay on the Old Mick side and cannot be placed on the fence.
- Mob tokens must stay on the Mob side and cannot be placed on the fence.
- Old Mick attack directions: `E`, `SE`, `S`, `SW`
- Mob attack directions: `W`, `NW`, `N`, `NE`

## Active-turn token protection

During `game`, only the active side's tokens may change position or direction.
If the inactive side's physical markers move accidentally during the other side's turn:

- the backend ignores the change
- the previously accepted token state remains authoritative
- the backend emits `inactive_side_token_changed`

## Status and error codes

- `camera_unavailable`
- `marker_map_scan_failed`
- `token_detection_failed`
- `hq_wrong_side`
- `hq_setup_complete`
- `old_mick_token_invalid_zone`
- `mob_token_invalid_zone`
- `old_mick_attack_direction_invalid`
- `mob_attack_direction_invalid`
- `inactive_side_token_changed`
