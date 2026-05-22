# Authoritative Actions v1

This document describes the commands currently accepted by the live Python runtime.

The current system uses two command styles:

- top-level transport/debug commands
- action-envelope commands sent as `{ "type": "action", "data": { ... } }`

## Current Status

- The main live path is marker-driven for setup and battle submission.
- Browser and manual runtimes still send explicit commands for mode selection, manual controls, tutorial flow, replay, and optional debug/testing actions.
- Older `move_unit` and `attack_in_direction` examples are not part of the current browser/runtime flow and should be treated as historical integration ideas rather than active commands.

## Action Envelope Shape

```json
{
  "type": "action",
  "data": {
    "action": "select_mode",
    "mode": "normal"
  }
}
```

## Current Action Commands

### `select_mode`

Purpose: lock the runtime into `normal` or `tutorial` mode.

```json
{
  "action": "select_mode",
  "mode": "normal"
}
```

Behavior:

- accepted when the session is still at `mode_select`
- starts a fresh session in the selected mode

### `return_to_mode_select`

Purpose: reset the session back to the mode-selection screen.

```json
{
  "action": "return_to_mode_select"
}
```

Behavior:

- clears the currently selected mode
- resets setup, game, and tutorial session state
- returns the public payload to `phase: "mode_select"`

### `trigger_nuke`

Purpose: submit a one-use nuke target for the active side.

```json
{
  "action": "trigger_nuke",
  "side": "p1",
  "position": { "x": 8, "y": 6 }
}
```

Behavior:

- accepted only during `game`
- accepted only for the current active side
- target must be inside enemy territory
- in live tracker mode, marker-driven nuke targeting is still the primary path

### `tutorial_dismiss`

Purpose: advance or dismiss the current tutorial step when allowed.

```json
{
  "action": "tutorial_dismiss"
}
```

### `tutorial_undo`

Purpose: move the tutorial backward when the current tutorial state allows undo.

```json
{
  "action": "tutorial_undo"
}
```

## Manual-Only Or Browser-Manual Commands

These are meaningful in no-camera manual runtimes and are not part of the main marker-driven live tracker flow.

### `place_token`

Purpose: place or clear a token in browser-manual mode.

```json
{
  "action": "place_token",
  "side": "p1",
  "role": "atk_a",
  "col": 3,
  "row": 5,
  "direction": "E"
}
```

### `rotate_token`

Purpose: rotate an attacker token in browser-manual mode.

```json
{
  "action": "rotate_token",
  "side": "p1",
  "role": "atk_a",
  "direction": "SE"
}
```

### `end_turn`

Purpose: resolve the active side and hand control to the other side in manual/browser-manual play.

```json
{
  "action": "end_turn",
  "player": 1
}
```

## Fallback Or Debug Setup Commands

These commands exist mainly for fallback flows or manual testing.

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

```json
{
  "action": "reset_setup"
}
```

### `cancel_hq`

Compatibility alias for `reset_setup`.

```json
{
  "action": "cancel_hq"
}
```

## Top-Level Transport Commands

These commands are not wrapped in the action envelope.

### `new_map`

```json
{ "type": "new_map" }
```

Purpose:

- regenerate terrain and reset session state within the current mode

### `tier`

```json
{ "type": "tier", "player": 1, "delta": 1 }
```

Purpose:

- development/testing helper for tier changes

### `demo_next`

```json
{ "type": "demo_next" }
```

Purpose:

- demo/experimental progression helper where supported

## Runtime-Specific Notes

### Live tracker path

- setup is primarily driven by markers `ID10`, `ID11`, `ID20`, `ID21`, and `ID4`
- battle positioning is opened by `ID10` or `ID20`
- battle resolution is confirmed by `ID4`
- browser-side setup actions are largely ignored in this path

### Manual path

- terminal commands drive setup and turn progression
- browser commands mainly support UI helpers and browser-manual placement

## Historical Note

Earlier contract notes referenced `move_unit` and `attack_in_direction` as active authoritative gameplay commands. They are not part of the current live browser/runtime command surface and should not be treated as canonical for this repository version.
