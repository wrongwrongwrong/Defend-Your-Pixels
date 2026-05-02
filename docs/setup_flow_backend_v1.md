# Setup Flow Backend v1

This document defines the marker-driven pre-game HQ setup flow for the live Old Mick runtime.

## Phases

The live runtime now primarily moves through three backend phases:

1. `scan`
2. `hq_placement`
3. `game`

The backend remains authoritative for phase transitions.

`side_selection` still exists in code as a fallback/debug path, but it is no longer the primary live HQ flow.

## Phase transitions

1. Stay in `scan` until the camera is available and the board marker scan is usable.
2. Move to `hq_placement` once the board scan is ready.
3. During `hq_placement`, the first stable visible turn marker decides which side hides an HQ first.
4. While one side is active, that side's HQ marker drives the live HQ candidate cell.
5. Scanning `ID4` locks the active side's valid HQ candidate.
6. Move to `game` only after both HQ locations are locked.

## Marker roles used by HQ setup

- Board corners:
  - `0` top-left
  - `1` top-right
  - `2` bottom-left
  - `3` bottom-right
- HQ setup markers:
  - `10` = `P1 TURN`
  - `11` = `P1 HQ`
  - `20` = `P2 TURN`
  - `21` = `P2 HQ`
  - `4` = shared `CONFIRM`

## Marker roles used by gameplay

- `10` = begin `P1` positioning during battle
- `20` = begin `P2` positioning during battle
- `12` / `13` / `14` = `P1 ATK A` / `ATK B` / `DEF`
- `22` / `23` / `24` = `P2 ATK A` / `ATK B` / `DEF`
- `4` = shared battle confirm; resolves the currently active side's attack and ends that side's turn

During battle, `ID10` / `ID20` only arm the side that is allowed to move. Attack resolution now happens when `ID4` is scanned, not when the turn marker changes.

The live runtime uses a short stability window before accepting turn-marker side changes or HQ candidate cells.

## Primary live setup flow

1. Wait for a valid 4-corner scan.
2. Show HQ setup instructions.
3. Show exactly one side turn marker on the board: `ID10` for `p1`, `ID20` for `p2`.
4. That turn marker decides which side is actively hiding an HQ.
5. The active side places its HQ marker on a valid cell in its own territory: `ID11` for `p1`, `ID21` for `p2`.
6. The frontend may highlight the live HQ marker cell, but the side panel does not show exact coordinates and confirmed HQ coordinates remain hidden.
7. Scan `ID4` to lock the active side's HQ if the candidate is valid.
8. Remove `ID4`, switch to the other side's turn marker, and repeat for the second side.
9. Enter `game` after both HQs are locked.

## Fallback / debug setup actions

The following browser/backend actions still exist as fallback or debug paths. They are no longer the primary live HQ workflow.

### `choose_side`

Fallback-only way to choose which faction places its HQ first.

```json
{
  "action": "choose_side",
  "first_player_side": "old_mick"
}
```

### `set_hq_candidate`

Fallback-only way to submit a candidate HQ cell for the currently active setup side.

```json
{
  "action": "set_hq_candidate",
  "side": "p1",
  "position": { "x": 3, "y": 4 }
}
```

### `confirm_hq`

Fallback-only way to lock the currently stored HQ candidate for that side.

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

Even though the live frontend can see the active HQ marker position during setup, the backend still hides the actual locked HQ coordinates from the public payload after setup completes.

## Setup payload

The runtime payload includes safe setup metadata only:

```json
{
  "phase": "hq_placement",
  "hq_markers": {
    "p1": { "col": 3, "row": 4, "stale": false },
    "p2": { "col": null, "row": null, "stale": true }
  },
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

`yu_test2/frontend/index.html` now renders a marker-guided setup placeholder whenever `phase` is not `game`.

- `scan`: shows a setup status card and scan-waiting messaging
- `side_selection`: fallback/debug state only
- `hq_placement`: shows the setup card plus highlighted valid HQ territory, active setup side emphasis, reserved-corner rejection, blocked-cell rejection, and fence invalidation

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

The live browser frontend now primarily reflects marker-driven setup state:

- during `hq_placement`, the active side's HQ marker controls the live candidate cell
- `ID4` locks the active side once a valid candidate exists
- the same `ID4` must be scanned again for the second side after it has been removed
- a restart button still sends `reset_setup`
- the old click/confirm controls are no longer the primary live path

The browser shows a live HQ marker preview ring for the active side. The side panel only shows status text such as detected/valid/invalid, and confirmed HQs become hidden immediately after they lock.

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
- HQ must not overlap blocked terrain (`p1_hard`, `p1_soft`, `p2_hard`, `p2_soft`).
- Reserved corner cells are invalid HQ cells:
  - `p1`: `A1`, `A2`, `B1`
  - `p2`: `L12`, `L11`, `K12`
- Old Mick tokens must stay on the Old Mick side and cannot be placed on the fence.
- Mob tokens must stay on the Mob side and cannot be placed on the fence.
- Old Mick attack directions: `E`, `SE`, `S`, `SW`
- Mob attack directions: `W`, `NW`, `N`, `NE`

## Marker-confirm HQ locking

During `hq_placement`:

- if both turn markers are visible at once, setup must not advance
- if the active side's turn marker is not visible, that side's HQ marker must not update the live candidate
- if no valid HQ marker is present for the active side, scanning `ID4` must not lock anything
- if a valid HQ candidate exists for the active side, scanning `ID4` locks it
- the same visible `ID4` must not lock both sides back-to-back without being removed first
- once both HQs are locked, the runtime enters `game`

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
