# Frontend-Backend Contract v1

This document defines the current integration contract between:

- `model_backend` as the authoritative game rules engine
- `bridge` as the transport/controller layer
- `react_frontend` as the temporary validation frontend
- future `Phaser` frontend as a replacement presentation/interaction layer

This contract is written for the `Old Mick Against the Mob` MVP.

## Purpose

The goal of this contract is to make the boundary explicit:

- what state the frontend receives
- what actions the frontend sends
- what logic must stay authoritative in Python
- what data is presentation-only and may be derived in the frontend

## Transport messages

Current WebSocket message types:

| Type | Direction | Purpose |
|------|-----------|---------|
| `board_state` | Python -> frontend | Full authoritative game snapshot |
| `action` | frontend / tracker -> Python | Authoritative player intent |
| `tracker_frame` | Python -> frontend | Non-authoritative marker telemetry |

## Frontend receives: authoritative state

Current authoritative `board_state` payload shape:

```json
{
  "turn": 1,
  "active_player": 1,
  "game_over": false,
  "winner": null,
  "last_action": "Player 1 turn started",
  "move_countdown": {
    "active": false,
    "seconds_remaining": 0,
    "duration_seconds": 10.0,
    "unit_id": null
  },
  "players": [
    {
      "id": 1,
      "ether": 10,
      "income_per_turn": 0,
      "hq_name": "Homestead",
      "resource_name": "Wheat Paddock",
      "command_tower_hp": 20,
      "command_tower_max_hp": 20
    },
    {
      "id": 2,
      "ether": 10,
      "income_per_turn": 0,
      "hq_name": "Nest",
      "resource_name": "Feeding Ground",
      "command_tower_hp": 20,
      "command_tower_max_hp": 20
    }
  ],
  "units": [
    {
      "id": "u0",
      "owner": 1,
      "kind": "attacker",
      "theme_name": "Riflemen",
      "position": { "x": 3, "y": 10 },
      "rotation_deg": 0,
      "hp": 3,
      "max_hp": 3
    }
  ]
}
```

## State field reference

### Top-level fields

| Field | Type | Authoritative | Notes |
|------|------|---------------|------|
| `turn` | number | yes | Current turn number |
| `active_player` | `1 \| 2` | yes | Which player may act now |
| `game_over` | boolean | yes | Match finished or not |
| `winner` | `1 \| 2 \| null` | yes | Winner or draw |
| `last_action` | string | yes | Human-readable latest backend status |
| `move_countdown` | object | yes | Auto-end-turn timer state |
| `players` | array | yes | Per-player authoritative summary |
| `units` | array | yes | All authoritative units on the board |

### `move_countdown`

| Field | Type | Authoritative | Notes |
|------|------|---------------|------|
| `active` | boolean | yes | Whether countdown is active |
| `seconds_remaining` | number | yes | Remaining seconds |
| `duration_seconds` | number | yes | Total countdown duration |
| `unit_id` | `string \| null` | yes | Unit that triggered countdown |

### `players[]`

| Field | Type | Authoritative | Notes |
|------|------|---------------|------|
| `id` | `1 \| 2` | yes | Player ID |
| `ether` | number | yes | Placeholder contract field for future economy/resource work |
| `income_per_turn` | number | yes | Placeholder contract field for future economy/resource work |
| `hq_name` | string | yes | Themed HQ label (`Homestead` / `Nest`) |
| `resource_name` | string | yes | Themed resource label (`Wheat Paddock` / `Feeding Ground`) |
| `command_tower_hp` | number | yes | Current HQ HP |
| `command_tower_max_hp` | number | yes | Max HQ HP |

### `units[]`

| Field | Type | Authoritative | Notes |
|------|------|---------------|------|
| `id` | string | yes | Stable unit ID |
| `owner` | `1 \| 2` | yes | Owning player |
| `kind` | `attacker \| defender` | yes | Internal unit role |
| `theme_name` | string | yes | Themed label (`Riflemen`, `Mob`, `Old Mick`, `Cassowary`) |
| `position` | `{ x, y }` | yes | Grid position |
| `rotation_deg` | number | yes if present | Tracker-derived metadata |
| `hp` | number | yes | Current HP |
| `max_hp` | number | yes | Max HP |

## State not yet included in v1

These are intentionally not in the current contract yet:

- resource tile list as a first-class payload
- terrain list as a first-class payload
- defender protection overlay as a dedicated payload
- hidden information / per-player filtered state
- upgrade state
- special attack state

These can be added in later contract revisions when the frontend needs them.

## Frontend sends: authoritative actions

Current supported action payloads:

### `end_turn`

```json
{
  "action": "end_turn"
}
```

### `move_unit`

```json
{
  "action": "move_unit",
  "unit_id": "u0",
  "position": { "x": 4, "y": 3 }
}
```

### `attack_in_direction`

```json
{
  "action": "attack_in_direction",
  "unit_id": "u0",
  "direction": "up_right"
}
```

Allowed `direction` values:

- `up`
- `down`
- `left`
- `right`
- `up_left`
- `up_right`
- `down_left`
- `down_right`

## Authoritative responsibilities

These rules must stay in Python backend:

- whose turn it is
- whether an action is legal
- movement legality
- line-attack tracing
- first-hit target resolution
- hard-terrain line blocking
- defender protection logic
- HQ damage and game-over resolution
- resource tile destruction / protection stripping
- final `last_action` status text

Frontend must not reimplement these rules as gameplay truth.

## Presentation-only responsibilities

These may be computed or decorated in the frontend:

- player `color`
- player `zone` (`top` / `bottom`)
- token selection state
- current control mode (`move` / `act`)
- attack direction derived from a click line
- highlight overlays
- tutorial text
- animation timing
- camera / board rendering style

These values may change between React and Phaser without requiring backend changes.

## React adapter responsibilities

Current React UI still uses an older prototype state shape. The adapter in:

- `react_frontend/src/bridge/adaptBoardStateToUi.js`

is responsible for converting authoritative payloads into UI shape.

Current adapter-derived UI-only fields include:

- `players[].color`
- `players[].zone`
- `players[].tokens[]`
- `rotation` converted from `rotation_deg`

This means the frontend should treat the adapter as the only place where backend state
is translated into React-specific structures.

## Tracker relationship

Tracker is not authoritative.

- tracker may propose `move_unit` intents
- backend validates and either accepts or rejects them
- frontend displays tracker telemetry separately from authoritative board state

Tracker must not directly overwrite backend state.

## Phaser handoff notes

This contract is intended to be reusable by Phaser later.

For Phaser, the expected model remains:

- Phaser sends action intents
- Python validates and returns authoritative state
- Phaser renders the latest returned state

Phaser should be treated as a presentation/interaction layer, not as the source of game rules.

## Related docs

- `docs/old_mick_mvp_rules.md`
- `docs/board_state_v1.md`
- `docs/authoritative_actions_v1.md`
- `docs/interaction_flow_v1.md`
- `docs/phaser_handoff_v1.md`
