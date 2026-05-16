# Board State v1

This file is the current board-state payload reference for the live Python-to-browser flow.

It defines the shared meaning used by Python as the authoritative source, `bridge` as the transport layer, and the browser frontend as the renderer. The live Old Mick runtime also includes `phase`, `setup`, and `errors` alongside the core board payload. Tracker calibration details still follow the current snapshot and camera-preview path.

## WebSocket messages

| `type` | Meaning |
|--------|---------|
| `board_state` | Authoritative game snapshot. The browser frontend updates its UI state from this full snapshot. |
| `action` | Authoritative action from the browser frontend or tracker to Python. See [`authoritative_actions_v1.md`](authoritative_actions_v1.md). |
| `tracker_frame` | Marker-derived position and facing updates only, used by the current tracker path. |
| `game_state` | Legacy compatibility message with the same merge semantics as `tracker_frame`. |

## Authoritative JSON shape

Field names use `snake_case` and stay aligned with the live runtime payload. The frontend is responsible for mapping these fields into whatever UI-facing shape it needs. The authoritative payload keeps `units[]` as the source-of-truth board-unit list and does not emit frontend-specific derived shapes.

```json
{
  "turn": 1,
  "active_player": 1,
  "game_over": false,
  "winner": null,
  "last_action": "Ready",
  "players": [
    {
      "id": 1,
      "ether": 0,
      "income_per_turn": 0,
      "hq_name": "Homestead",
      "resource_name": "Wheat Paddock",
      "command_tower_position": { "x": 5, "y": 11 },
      "command_tower_hp": 20,
      "command_tower_max_hp": 20
    }
  ],
  "resource_tiles": [
    {
      "id": "px0",
      "owner": 1,
      "theme_name": "Wheat Paddock",
      "position": { "x": 4, "y": 10 },
      "protection_layers": 1
    }
  ],
  "units": [
    {
      "id": "A1",
      "owner": 1,
      "kind": "attacker",
      "position": { "x": 3, "y": 10 },
      "rotation_deg": 0,
      "hp": 3,
      "max_hp": 3
    }
  ]
}
```

- `winner`: `null` or a side/player winner value from the live runtime.
- `last_action`: optional HUD or debug text.
- `units[].id`: always a `string`.
- `units[].rotation_deg`: optional. If absent, the frontend may map to its default facing representation.
- `resource_tiles[]`: authoritative destructible objectives with owner, position, theme name, and protection layers.
- Tower data stays folded into `players[]` through `command_tower_position`, `command_tower_hp`, and `command_tower_max_hp`. There is no separate `towers[]` array in v1.
- `players[].hq_name` and `players[].resource_name` provide the themed display names.
- `players[].income_per_turn` is currently a placeholder field reserved for future economy work.

## Setup metadata

The live payload may additionally include:

- `phase`
- `setup`
- `battle`
- `errors`

`setup` carries safe setup progress only. Confirmed HQ coordinates must not be exposed during normal play.

Example:

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

- `phase`: the live path primarily uses `scan`, `hq_placement`, and `game`. `side_selection` remains available for fallback or debug paths.
- `errors[]`: stable `{ "code", "message" }` objects for recoverable validation or tracker issues.
- `setup.hq.*`: exposes candidate and confirmed flags only, never hidden HQ coordinates.
- `battle.active_side`: the side currently allowed to position and submit tokens. `null` means the runtime is waiting for the next `ID10` or `ID20`.
- `battle.waiting_for_side`: if present, indicates which side's turn marker must be scanned next.
- `help_visible`: `true` only while `ID5` is currently visible; the frontend uses it to show the help overlay.
- `game.hq_revealed`: the only public path for exposing an HQ coordinate after it has been destroyed.

## Current frontend usage

`frontend/index.html` currently consumes these fields as follows:

- When `phase !== "game"`, it shows setup state through the top bar, bottom warning bar, board overlays, and side panels.
- During `side_selection` and `hq_placement`, it overlays territory and fence guides on the board.
- It shows `setup.status_message` and safe HQ progress directly to players.
- It uses `setup.hq.*` only for `has_candidate` and `confirmed` state, never for exact HQ coordinates.
- `side_selection` remains a fallback or debug path. The live marker path chooses the active setup side through `ID10` and `ID20`.
- During `hq_placement`, `ID11` and `ID21` provide the live HQ candidate, and `ID4` confirms it.
- `ID5` drives a marker-presence help overlay without changing authoritative game state.
- The frontend may highlight the active setup side's current HQ candidate cell, but the side panel does not show exact coordinates and confirmed HQs are hidden immediately after confirmation.
- During `game`, the battle flow is primarily described by `battle.*`: `ID10` and `ID20` open positioning for one side, and `ID4` submits and resolves that side's attack.
- `errors[]` are rendered through the bottom warning bar and related board-side UI cues.
- `inactive_side_token_changed` is treated as a recoverable warning that explains the opponent movement was ignored.
- `hq_setup_complete` is rendered as a success-style alert instead of a warning.

## Legacy UI reference

The following shape is an older UI-facing reference that may still be useful when reading older frontend code:

| UI field | Meaning |
|----------|---------|
| `turn` | number |
| `activePlayer` | `1` \| `2` |
| `gameOver` | boolean |
| `players[]` | `id`, `color`, `zone`, `ether`, `incomePerTurn`, `hqName`, `resourceName`, `commandTowerPosition`, `commandTowerHp`, `commandTowerMaxHp`, `tokens[]` |
| `resourceTiles[]` | `id`, `owner`, `themeName`, `position`, `protectionLayers` |
| `players[].tokens[]` | `id`, `kind`, `hp`, `maxHp`, `position`, `rotation` |
| `units[]` | non-marker board units; often `[]` in older flows |

- `color` and `zone` are UI-only fields derived by the frontend from `player.id`. They are not emitted by the authoritative Python payload.

## Legacy adapter concept: `units` -> `players[].tokens[]`

| Authoritative | Legacy UI token field |
|---------------|-----------------------|
| `units[].id` | `id` |
| `units[].owner` | determines which `player` owns the token |
| `units[].kind` | `kind`: `attacker` or `defender` |
| `units[].position` | `position`: `{ x, y }` |
| `units[].rotation_deg` | `rotation`: mapped into a frontend-facing representation |
| `units[].hp` / `max_hp` | `hp` / `maxHp` |

The authoritative payload remains `units[]`. Older frontend code may still derive `players[].tokens[]` from it.

## HP scale strategy

| Source | Example |
|--------|---------|
| Live runtime unit | default `hp` / `max_hp` values are small integers such as `3` |
| older UI token display | values such as `30` or `40` used for presentation-only bars |

Recommended approach for the MVP:

1. Keep a single authoritative integer scale in Python and the contract.
2. Let the frontend render bar proportions from `hp / max_hp`.
3. Avoid introducing a second display-specific scale into the contract.

The current MVP uses this single-scale approach.

## Current integration alignment

- Older frontend mock rules such as `endTurn`, `trySpendEther`, and `phaseForTurn` are no longer part of the primary path.
- The current authoritative actions are `end_turn`, `move_unit`, and `attack_in_direction`. See [`authoritative_actions_v1.md`](authoritative_actions_v1.md).
- The tracker still uses `tracker_frame` and does not merge into `board_state` as a partial-position-only override path.

## Summary

- The live Old Mick runtime additionally emits `phase`, `setup`, and `errors`.
- `units[].id` remains a `string`.
- The authoritative payload stays centered on `units[]`, with any legacy `players[].tokens[]` shape derived later if needed.
- `players[]` does not include UI-only fields such as `color` or `zone`.
- Tower data stays folded into `players[]`.
