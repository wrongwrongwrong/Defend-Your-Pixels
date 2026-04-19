# Old Mick Against the Mob Prototype Rules

This file is the readable gameplay contract for the current `prototype_pygame` +
`model_backend` prototype.

This file now follows the `Old Mick Against the Mob` MVP rules instead of the older
pixel-defense ruleset.

## Quick summary

- Turn-based grid game.
- Two factions: Farmers versus Emus.
- Main objective: destroy the enemy HQ.
- Attackers use directional line attacks.
- Defenders protect nearby resource tiles passively.
- Economy, upgrades, and hidden information are out of scope for this prototype pass.

## Core gameplay requirements

### 1) Match format

- Grid map loaded from ASCII level files.
- Two sides (`P1` / `P2`).
- MVP target setup per side:
  - `ATK x2`
  - `DEF x1`
  - `HQ x1`

### 2) Theme mapping

- Farmer ATK = `Riflemen`
- Farmer DEF = `Old Mick`
- Farmer HQ = `Homestead`
- Farmer resource tiles = `Wheat Paddocks`

- Emu ATK = `Mob`
- Emu DEF = `Cassowary`
- Emu HQ = `Nest`
- Emu resource tiles = `Feeding Grounds`

Internal engine names may still use `Attacker`, `Defender`, `CommandTower`, and `Pixel`,
but prototype behavior must follow the themed rules above.

### 3) Win condition

- Destroy the enemy HQ to win immediately.
- The current MVP does **not** use the old pixel-count victory rule.
- Attrition-based victory is deferred to a later phase.

### 4) Attack behavior

- Attackers no longer use the old `act_on_target` tile-picking rule.
- Instead, an attacker chooses one of 8 directions:
  - `up`, `down`, `left`, `right`
  - `up-left`, `up-right`, `down-left`, `down-right`
- The model traces a line in that direction.
- The attack hits the **first valid enemy target** on that line.
- If hard terrain blocks the line first, the attack fails.

Current valid targets in the MVP:

- enemy HQ
- enemy resource tile

### 5) Defender behavior

- Defenders do not repair units or HQs.
- Defenders act as passive defensive anchors.
- Each defender provides a `3x3` protection zone centered on itself.
- Friendly resource tiles in that zone gain one protection layer.
- In practice, protected resource tiles take 2 hits instead of 1.
- No stacking.
- No special exceptions.

### 6) Resource tiles

- Resource tiles are destructible non-HQ objectives.
- Default HP = 1.
- Protected by defender zone = 2 hits required.
- They do not generate economy yet.

### 7) Turn and controls (Pygame)

- `Q / E`: cycle selected active-player unit in move mode.
- `2`: move mode.
- `1`: attack mode.
- Move mode:
  - `WASD` preview move
  - `Enter` confirm move
  - `Tab` undo last confirmed move
- Attack mode:
  - `WASD` for orthogonal directions
  - `Q / E / Z / C` for diagonal directions
  - `Enter` confirm attack
- `Space`: end turn (with skip confirmation when no action was taken).
- `Esc`: quit.

### 8) Out of scope for this prototype

- hidden HQ / hidden information
- economy / resource generation
- upgrade tiers
- one-time special attacks
- tracker-driven attack input

## Current status

- **Implemented now:**
  - HQ-destruction win condition
  - directional line attack
  - hard-terrain blocking
  - passive defender `3x3` protection
  - protected resource tiles requiring two hits
  - updated turn UI / debug HUD
- **Still to come later:**
  - attrition rule
  - upgrade system
  - hidden HQ
  - Phaser-oriented frontend flow

## Code mapping

- Rules/state: `model_backend/game/state.py`, `model_backend/game/entities.py`
- Input loop: `prototype_pygame/control.py`
- Rendering/HUD: `prototype_pygame/view.py`
- Level loading: `model_backend/scenarios/level_loader.py`
- Detailed MVP rules: `docs/old_mick_mvp_rules.md`
