# Phaser Handoff / Integration Spec v1

This document is the practical handoff spec for a future Phaser frontend replacing the
current React validation layer.

It is written for the `Old Mick Against the Mob` MVP and assumes:

- Python backend remains authoritative
- bridge remains the action dispatcher / transport boundary
- Phaser becomes the presentation and interaction layer

## Goal

Phaser should:

- render the latest authoritative state
- let the player express valid intents
- send those intents as action payloads
- react to returned state and status text

Phaser should **not** become a second rules engine.

## Integration model

Expected loop:

1. Python sends `board_state`
2. Phaser renders the snapshot
3. Player interacts with the board
4. Phaser sends an `action` intent
5. Python validates and applies the action
6. Python sends the next `board_state`
7. Phaser re-renders from authoritative data

## 1. Coordinate system

### Authoritative board coordinates

Grid coordinates are backend-defined and zero-indexed.

- top-left cell = `{ x: 0, y: 0 }`
- x increases to the right
- y increases downward

Example:

- `{ x: 3, y: 10 }` means column 4, row 11 in player-facing display terms

### Phaser rendering expectation

Phaser may choose any world-space layout, but it must preserve a deterministic mapping:

- one grid cell <-> one authoritative `{ x, y }`

Recommended Phaser rule:

- convert screen/world interactions back into `{ x, y }`
- never send floating-point world coordinates to backend

## 2. What one grid cell represents

In MVP, a grid cell may contain one of the following relevant authoritative entities:

- empty ground
- HQ
- unit
- resource tile
- hard terrain / obstacle

### Current backend reality

Current authoritative payload does **not yet** send resource tiles or terrain as first-class arrays.

So for v1 handoff:

- Phaser can fully render units and HQ summaries from existing payload
- resource tiles / terrain either:
  - remain temporary debug-only visuals, or
  - require a future contract extension before Phaser renders them properly

This is an important limitation of the current contract.

## 3. Naming rules

### Internal backend names

Backend still uses some older internal names:

- `Attacker`
- `Defender`
- `CommandTower`
- `Pixel`

### Themed names for frontend display

Use these themed labels in Phaser UI:

- P1 attacker -> `Riflemen`
- P2 attacker -> `Mob`
- P1 defender -> `Old Mick`
- P2 defender -> `Cassowary`
- P1 HQ -> `Homestead`
- P2 HQ -> `Nest`
- P1 resource tile -> `Wheat Paddock`
- P2 resource tile -> `Feeding Ground`

### Data source for names

Phaser should prefer:

- `units[].theme_name`
- `players[].hq_name`
- `players[].resource_name`

Do not hardcode old prototype names like `Command Tower` into the new MVP presentation.

## 4. Current authoritative state payload

Phaser will receive `board_state` messages shaped like this:

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

## 5. Minimum Phaser rendering requirements

Phaser MVP should at minimum render:

- board grid
- token positions
- token theme names or readable identity
- whose turn it is
- HQ HP summary per player
- latest backend status (`last_action`)
- game-over state
- selected token state
- current interaction mode (`move` / `act`)

## 6. Action payload examples

Phaser should send these actions under WebSocket messages of the form:

```json
{
  "type": "action",
  "data": {
    "action": "end_turn"
  }
}
```

### End turn

```json
{
  "action": "end_turn"
}
```

### Move unit

```json
{
  "action": "move_unit",
  "unit_id": "u0",
  "position": { "x": 4, "y": 3 }
}
```

### Directional attack

```json
{
  "action": "attack_in_direction",
  "unit_id": "u0",
  "direction": "up_right"
}
```

Allowed direction strings:

- `up`
- `down`
- `left`
- `right`
- `up_left`
- `up_right`
- `down_left`
- `down_right`

## 7. Turn flow

Phaser should assume this backend-driven turn flow:

1. backend declares `active_player`
2. player selects one of their own tokens
3. player chooses `move` or `act`
4. Phaser sends intent
5. backend either:
   - accepts and updates state, or
   - rejects and updates `last_action`
6. frontend refreshes from returned `board_state`
7. player may end turn, or backend may trigger move countdown behavior if applicable

Important:

- Phaser should never advance turn locally on its own
- Phaser should wait for updated authoritative state

## 8. Error / rejection handling

Current bridge behavior does not return a separate error object.

Instead, rejected actions are surfaced through authoritative state updates, especially:

- `last_action`

Examples:

- `Cannot end turn while move countdown is active`
- `Unknown unit: u99`
- `attack_in_direction missing direction`
- `u0 line attack blocked at (2, 2)`

### Phaser handling rule

If an action is rejected:

- do not invent a local correction
- display the returned `last_action`
- keep selection if useful
- let player try again

## 9. Interaction expectations for Phaser

Phaser interaction should match the MVP interaction flow:

- select token
- choose move or act mode
- for move: choose destination cell
- for act: choose a straight or diagonal line
- show enough feedback that player understands what intent will be sent

Recommended minimal Phaser feedback:

- selected token highlight
- current mode badge
- hover highlight for candidate destination cell
- hover or ghost line for attack direction
- visible status text area using `last_action`

## 10. What Phaser should not assume yet

Phaser should not assume these exist in v1 payload:

- resource tile array
- terrain array
- defender-zone overlay payload
- hidden-information filtering
- upgrade state

If Phaser needs any of those, the contract must be extended first.

## 11. Implementation split

### Backend owns

- rule validation
- movement legality
- attack legality
- line tracing
- blocking
- defender protection
- HQ damage and victory

### Phaser owns

- input handling
- selection state
- camera / layout / 2D or 3D presentation
- feedback overlays
- animation
- tutorial / hint presentation

## 12. Recommended first Phaser milestone

The first Phaser integration milestone should support only:

- render board
- render units
- show turn / active player / HQ HP / last action
- send `move_unit`
- send `attack_in_direction`
- send `end_turn`

Do not block initial integration on:

- fancy VFX
- hidden HQ
- upgrade UI
- resource tile rendering
- dedicated protection overlays

## Related docs

- `docs/frontend_backend_contract_v1.md`
- `docs/interaction_flow_v1.md`
- `docs/authoritative_actions_v1.md`
- `docs/old_mick_mvp_rules.md`
