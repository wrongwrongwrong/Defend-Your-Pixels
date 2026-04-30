# Old Mick Against the Mob MVP Rules

This file defines the minimum playable ruleset for the first `Old Mick Against the Mob`
prototype. It is intentionally narrower than the full GDD. The goal is to lock the
core loop before expanding into upgrades, hidden information, and Phaser-specific UI.

## MVP scope

- 2-player turn-based board game.
- Farmers versus Emus.
- No hidden HQ yet.
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
- The match ends as soon as one HQ reaches 0 HP.
- The current backend implementation now uses HQ destruction as the only active win
  condition for this MVP.

## Deferred systems

These are intentionally out of MVP scope:

- hidden HQ / hidden information
- attrition win based on resource collapse
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
5. If hard terrain blocks the line before any valid enemy target is found, the attack fails.

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
- Current backend implementation applies this as a passive aura. Protected tiles gain one
  guard layer automatically while they remain inside the defender zone.

For the first MVP pass, DEF protection only needs to apply to friendly destructible
resource tiles. HQ protection can be added later if desired, but is not required for
the first playable version.

## Destructible resource tiles

The board should contain destructible non-HQ objectives so the game is not only an HQ rush.

Theme mapping:

- Farmer side resource tiles = `Wheat Paddocks`
- Emu side resource tiles = `Feeding Grounds`

Rules:

- Default HP = 1
- If protected by DEF, HP = 2
- They can be destroyed by ATK line attacks
- They do not need to generate resources yet

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

- `runner/run_old_mick_core_smoke.py`

## Implementation note

The first implementation should happen in `model_backend`.

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
