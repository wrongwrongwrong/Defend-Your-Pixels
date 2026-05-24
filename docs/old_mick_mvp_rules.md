# Old Mick Against the Mob MVP Rules

> Status: reference document.
>
> This file captures earlier MVP rule framing and background context. It is not the canonical description of the current live runtime. For current behavior, use `backend/live_rules/game_model.py`, `docs/board_state_v1.md`, and `docs/authoritative_actions_v1.md`.

This file defines the minimum playable ruleset for the first `Old Mick Against the Mob`
prototype. It is intentionally narrower than the full GDD. The goal is to lock the
core loop before expanding into upgrades, hidden information, and Phaser-specific UI.

## MVP scope

- 2-player turn-based board game.
- Farmers versus Emus.
- Hidden HQ setup is part of the live rules.
- No economy system yet.
- No upgrade system yet.
- No map art or 2D/3D presentation decisions in this file.

## Board and sides

- The board remains grid-based.
- Each side owns one half of the board.
- Exact map layout and terrain placement are implementation details for later steps.
- This MVP focuses on rules, not board presentation.

## Core pieces per side

Each side starts with:

- `ATK x2`
- `DEF x1`
- `HQ x1`

Theme mapping:

- Farmer ATK = `Riflemen`
- Farmer DEF = `Old Mick`
- Farmer HQ = `Homestead`
- Emu ATK = `Mob`
- Emu DEF = `Cassowary`
- Emu HQ = `Nest`

The model may continue using existing internal names at first, but gameplay behavior
must follow the rules below.

Current backend mapping layer:

- internal `Attacker` serializes as themed `Riflemen` for P1 and `Mob` for P2
- internal `Defender` serializes as themed `Old Mick` for P1 and `Cassowary` for P2
- internal `CommandTower` maps to `Homestead` for P1 and `Nest` for P2
- internal `Pixel` maps to `Wheat Paddock` for P1 and `Feeding Ground` for P2

This keeps the current engine stable while the team replaces the old rules in later steps.

## Primary win condition

- Destroy the enemy HQ to win immediately.
- Destroy all 24 enemy resource cells to win by attrition.
- The match ends as soon as either win condition is met.

Current live rules implementation:

- HQ destruction is still an immediate win.
- Attrition win now means full destruction of the enemy's resource grid, not a score threshold.

## Deferred systems

These are intentionally out of MVP scope:

- hidden HQ / hidden information
- economy / resource generation
- upgrades
- special attacks / nukes

## Attack rules

ATK tokens do not use the old "pick any target tile in range" rule.

Instead, the MVP attack flow is:

1. Select an ATK token.
2. Choose one of the 8 straight directions.
3. Trace a line outward from the attacker.
4. The attack hits the first valid enemy target found on that line.
5. If terrain blocks the line before any valid enemy target is found, the attack hits that terrain instead. Soft terrain clears after 2 hits; hard terrain clears after 5 hits.

Allowed attack directions:

- up
- down
- left
- right
- up-left
- up-right
- down-left
- down-right

Valid targets for this MVP:

- enemy HQ
- enemy destructible resource tile

Direct attacks on units can stay out of scope unless needed to preserve engine stability.

## Defender protection rules

Each side has one DEF token that acts as a defensive anchor.

- DEF provides a `3x3` protection zone centered on itself.
- Friendly destructible tiles inside that zone gain `+1 HP`.
- In practice, a tile that normally takes 1 hit now takes 2 hits.
- No stacking.
- No special exceptions.
- Current backend implementation treats the guard layer as per-cell protection tied to the current DEF anchor. The first hit against a protected cell consumes that cell's DEF layer. That cell is no longer protected while the DEF token remains at the same anchor.
- Moving the DEF token changes the anchor and resets the consumed protection cells for that side.

For the first MVP pass, DEF protection only needs to apply to friendly destructible
resource tiles. HQ protection can be added later if desired, but is not required for
the first playable version.

## Destructible resource tiles

The board should contain destructible non-HQ objectives so the game is not only an HQ rush.

Theme mapping:

- Farmer side resource tiles = `Wheat Paddocks`
- Emu side resource tiles = `Feeding Grounds`

Rules:

- Each side has exactly 24 destructible resource cells.
- Default HP = 1
- If protected by DEF, HP = 2
- They can be destroyed by ATK line attacks
- Each cell is worth 1 unit.
- The scoreboard counts down from 24 remaining cells.
- There are no hidden bonus-value cells.

Reserved cells:

- `A1`, `A2`, `B1`, `K12`, `L11`, and `L12` stay empty.
- Those cells cannot hold HQs, terrain, or destructible resource cells.

DEF progression:

- DEF starts with a `3x3` protection zone.
- When a side has 12 or fewer resource cells remaining, that side's DEF zone expands to `5x5`.
- The frontend draws the DEF area cell-by-cell. Consumed protection cells appear as holes with a broken-protection marker, while destroyed cells use the normal destroyed-cell treatment.

ATK progression:

- ATK A and ATK B track destroyed resource cells separately.
- Destroying 4 resource cells with one ATK token upgrades that token to ATK tier 1.
- Destroying 8 resource cells with one ATK token upgrades that token to ATK tier 2.
- ATK tier 1 randomly destroys 1 extra enemy resource cell in the `3x3` area around the primary target.
- ATK tier 2 randomly destroys up to 2 extra enemy resource cells in the `3x3` area around the primary target.
- Extra destroyed cells from this splash count toward that same ATK token's progression.
- Terrain, HQs, and nuke-destroyed resources do not count toward ATK progression.

Nuke progression:

- When a side has 8 or fewer resource cells remaining, that side's one-use nuke unlocks.
- P1 triggers nuke with marker `ID19`; P2 triggers nuke with marker `ID29`.
- The nuke marker only works during that side's active turn and must be placed in enemy territory.
- A valid marker creates a pending nuke target that is previewed on the frontend with the nuke icon and `3x3` area.
- The pending nuke resolves when `ID4` confirms the active side's turn.
- Nuke affects a `3x3` area centered on the marker.
- All terrain in the area is destroyed.
- Up to 5 resource cells in the area are randomly destroyed.
- HQs are not destroyed by nuke.

## MVP interaction assumptions

This file does not lock the final UI, but the gameplay assumes players must be able to:

- select an ATK token
- preview or choose an attack direction
- understand which line will be traced
- understand which tiles are protected by DEF
- understand whose turn it is
- understand when the game ends

## MVP checkpoint questions

Once the above is implemented, the team should test:

- Is line-based attack intuitive?
- Does hard terrain create meaningful blocking?
- Does the DEF zone create interesting positioning decisions?
- Do resource tiles reduce pure HQ rushing?
- Is the turn-to-turn decision space clear enough for first-time players?

Current executable gameplay smoke coverage lives in:

- `runner/run_manual_play.py`

## Implementation note

The live implementation lives in `backend/live_rules`.

Recommended early focus:

- authoritative win rule = HQ destroyed
- authoritative straight-line attack resolution
- authoritative DEF `3x3` protection
- authoritative destructible resource tiles

Current integration state:

- resource tiles are exposed as first-class `board_state.resource_tiles[]`
- frontend validation can display tile ownership and protection state

The browser frontend or any future presentation layer should consume these rules rather
than reimplementing them.

See also:

- `docs/board_state_v1.md`
- `docs/authoritative_actions_v1.md`
- `docs/interaction_flow_v1.md`
