# Old Mick Core Test Cases

This file defines the current core gameplay test cases for the `Old Mick Against the Mob`
MVP. These are the minimum rule checks the team should rerun whenever core backend logic
changes.

## Scope

This file covers only the current MVP core:

- line attack hits the first valid target
- hard terrain blocks line attacks
- defender protection makes a resource tile require two hits
- destroying the enemy HQ ends the game immediately

Upgrade-related test cases are intentionally deferred until Step 11.

## Manual / playtest checklist

### 1. First-hit line attack

Setup:

- Place an attacker with two enemy targets on the same line.
- Make sure the nearer target is a valid target.

Expected result:

- The nearer target is hit.
- The farther target is untouched.

### 2. Hard-terrain blocking

Setup:

- Place an attacker and an enemy HQ on the same line.
- Put hard terrain between them.

Expected result:

- The attack fails.
- `last_action` reports that the line attack was blocked.
- The HQ takes no damage.

### 3. Defender protection

Setup:

- Place a defender so that a friendly resource tile is inside its `3x3` zone.
- Attack that resource tile twice.

Expected result:

- First hit removes protection only.
- Second hit destroys the tile.

### 4. HQ destruction ends the game

Setup:

- Place an attacker with a clear line to the enemy HQ.
- Reduce the enemy HQ to lethal range, then attack.

Expected result:

- The HQ reaches `0 HP`.
- `game_over == True`.
- `winner` is set correctly.
- `last_action` includes that the player won by destroying the enemy HQ.

## Smoke test script

The current automated smoke test is:

- `python runner/run_old_mick_core_smoke.py`

It checks the same four core scenarios above.
