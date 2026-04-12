# Pixel Defense Prototype Rules (Readable Spec)

This file is the gameplay contract for the current `prototype_pygame` + `model_backend` implementation.

## Quick summary

- Turn-based grid game.
- Objective is to destroy enemy **pixels**.
- Ether/drill system is disabled in this ruleset.
- Defenders are **not healers**; defenders only apply shield.

## Core gameplay requirements

### 1) Match format

- Grid map loaded from ASCII level files.
- Two sides (P1/P2).
- Typical setup target: 2 attackers + 2 defenders per side (map controls exact spawn).

### 2) Pixel system

- Each side starts with **35 pixels**.
- Pixels block movement.
- Pixels have guard state: `guarded_turns` in `{0, 1}`.
- If an enemy pixel is **unguarded**, one attacker hit destroys it.
- If an enemy pixel is **guarded**, first hit removes guard; second hit destroys it.

### 3) Defender behavior (corrected)

- Defender action is **shield only**.
- No repairing units.
- No repairing HQ.
- Defender shield ability affects **3x3 area centered on defender**.
- Friendly pixels in that 3x3 get `guarded_turns = 1` (max 1).
- Guard decays when that pixel owner's opponent finishes a turn.

### 4) Turn and controls (Pygame)

- `Q / E`: cycle selected active-player unit.
- `2`: move mode.
- `1`: action mode.
- Move mode: `WASD` preview move, `Enter` confirm, `Tab` undo last confirmed move.
- Action mode: `WASD` preview target, `Enter` confirm action.
- `Space`: end turn (with skip confirmation when no action was taken).
- `Esc`: quit.

### 5) Win condition

- First player to destroy **25 enemy pixels** wins.
- HUD must show current destroyed counts and winner at game end.

## Current status

- **Implemented now:** pixel destruction, guard strip/destroy sequence, defender 3x3 shielding, guard decay, win at 25, turn UI/hints.
- **Out of scope now:** AI opponent, ether economy, drill capture gameplay, tracker synchronization logic in this file.

## Code mapping

- Rules/state: `model_backend/game/state.py`, `model_backend/game/entities.py`
- Input loop: `prototype_pygame/control.py`
- Rendering/HUD: `prototype_pygame/view.py`
- Level loading: `prototype_pygame/levels/level_loader.py`
