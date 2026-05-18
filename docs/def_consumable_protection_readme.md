# Consumable DEF Protection

## Summary

The DEF token no longer provides a permanently passive `+1 HP` aura to every covered cell.

Protection is now tracked per covered cell for the current DEF anchor position.

## New Behavior

- DEF still covers a square zone centered on the token.
- Normal DEF zone: `3x3`.
- Upgraded DEF zone: `5x5` once that side has `12` or fewer remaining resource cells.
- Each covered attackable cell gets one protection charge for the current DEF position.
- When a covered cell is hit, that cell consumes its protection immediately.
- Other covered cells remain protected until they are hit themselves.
- Consumed protection does not come back while the DEF token stays on the same `col,row`.
- Moving the DEF token to a different `col,row` starts a fresh protection cycle.
- Moving DEF away and later back to the same cell also restores protection, because the anchor changed in between.

## Scope

- The authoritative change lives in `backend/live_rules/game_model.py`.
- No frontend rule logic was added.
- Existing line-attack, splash, terrain, win-condition, and nuke behavior stays unchanged.

## Snapshot Debug Fields

`GameModel.snapshot()` now includes:

- `def_anchor_cells`
- `def_consumed_cells`

These fields are debug-friendly snapshots of the current DEF anchor and the cells that have already consumed protection for that anchor.

## Files Changed

- `backend/live_rules/game_model.py`
- `docs/def_consumable_protection_readme.md`
