# Interaction Flow v1

This document defines the current MVP interaction flow for `Old Mick Against the Mob`.

This is not a visual design spec. It describes how players operate the prototype and how
the frontend should communicate state and intent.

## Purpose

This flow should answer five core questions:

- how the player selects an ATK token
- how the player chooses an attack direction
- how the player understands the attack line
- how the player understands the DEF zone
- how the player sees turn state and win state

## Pre-game setup flow

Before gameplay begins, the backend now requires:

1. board scan readiness
2. side selection
3. sequential HQ placement with confirmation
4. transition to `game`

Backend responsibility during setup:

- wait for a valid board scan before allowing setup
- track which side sets HQ first
- validate that each HQ stays on its own side and off the fence
- keep both confirmed HQ locations hidden from the public payload

## Core interaction model

The MVP uses a two-mode interaction model:

- `Move mode`
- `Act mode`

The selected token is the anchor for both modes.

Frontend responsibility:

- let the player select a token
- make the current mode visible
- show where a move can go
- show how an attack direction is being chosen
- show backend status after every action

Backend responsibility:

- validate moves
- validate attacks
- resolve first-hit logic
- resolve blocking
- resolve defender protection
- resolve HQ destruction and game over

## 1. Selecting an ATK token

### Required player flow

1. Player identifies a controllable token.
2. Player selects that token.
3. UI confirms which token is selected.

### Current React validation behavior

- Player clicks a token on the board.
- UI stores `selectedTokenId`.
- Status text shows:
  - token theme name
  - token id
  - token position

Example:

- `Selected Riflemen u0 at (4, 11)`

### Current pygame prototype behavior

- `Q / E` cycles active-player units.
- The currently selected unit is the one used for move or attack actions.

### Validation goal

Players should never need to guess which token is currently selected.

## 2. Choosing an attack direction

### Required player flow

1. Player selects an attacker.
2. Player switches to `Act mode`.
3. Player indicates one of 8 directions.
4. Frontend converts that interaction into `attack_in_direction`.

### Current React validation behavior

- Player switches to `Act mode`.
- Player clicks a board cell.
- Frontend derives a direction from:
  - selected token position
  - clicked cell position
- Only straight or diagonal lines are accepted.
- Invalid clicks are rejected with an interaction hint.

Current accepted directions:

- `up`
- `down`
- `left`
- `right`
- `up_left`
- `up_right`
- `down_left`
- `down_right`

### Current pygame prototype behavior

- Player switches to attack mode with `1`.
- Player chooses direction with:
  - `W A S D` for orthogonal directions
  - `Q E Z C` for diagonal directions
- `Enter` confirms the attack.

### Validation goal

The player should understand that they are choosing a direction, not choosing an arbitrary target tile.

## 3. Understanding the attack line

### Required player flow

The frontend should make it clear that:

- attacks travel in a straight or diagonal line
- only the first valid enemy target is hit
- hard terrain may block the attack before a target is reached

### Current React validation behavior

- The frontend currently communicates this through:
  - mode labels
  - footer hint
  - interaction hint
  - backend `last_action`
- Example feedback:
  - invalid click -> `Act mode only accepts straight or diagonal lines from the selected token.`
  - valid click -> `Attack queued: Riflemen -> up right`

### Current pygame prototype behavior

- Attack mode highlights reachable line cells for the selected direction family.
- Preview follows the chosen direction.
- HUD explains that attack uses directional line attack.

### MVP limitation

Current React validation layer does not yet render a dedicated attack-line overlay.

This is acceptable for the current validation pass, but should be improved in later frontend work.

### Validation goal

First-time players should understand why an attack succeeded, failed, or hit a specific target.

## 4. Understanding the DEF zone

### Required player flow

The frontend should communicate that:

- defenders are passive anchors
- each defender protects a `3x3` area
- protected resource tiles require one extra hit

### Current React validation behavior

- Defender meaning is currently explained via:
  - HUD labels
  - validation summary
  - footer / role text
- The React validation layer does **not** yet draw a dedicated DEF-zone overlay.

### Current pygame prototype behavior

- Debug HUD states that defenders provide passive `3x3` protection.
- Protected resource tiles are drawn brighter.

### MVP limitation

Current frontend state does not yet expose a dedicated protection overlay payload.

For now, the prototype validates understanding through:

- rules text
- HUD wording
- backend result text
- brighter protected resource tiles in pygame

### Validation goal

Players should understand that defenders are not healers or direct attack units in this MVP.

## 5. Understanding turn state and win state

### Required player flow

The frontend should always show:

- current turn number
- active player
- latest backend status
- whether move countdown is active
- when the game is over
- who won

### Current React validation behavior

React currently shows:

- `Turn`
- `Active`
- `Status` from `last_action`
- move countdown box
- game-over overlay

### Current pygame prototype behavior

- HUD shows turn number and active player
- HUD shows current status text
- HUD shows game-over state and winner

### Validation goal

Players should never be confused about whose turn it is or why the match ended.

## Turn integrity

During gameplay, accidental movement of the inactive side's physical markers does not change authoritative state.

The backend now:

- ignores inactive-side token position or rotation changes
- keeps the last accepted state for that side
- reports a validation status through `inactive_side_token_changed`

## Current validation checklist

The interaction flow is good enough for MVP testing if players can do the following without verbal rescue:

1. select a token
2. tell whether they are in move or act mode
3. move a token legally
4. perform a directional attack legally
5. understand that defenders are passive protection units
6. identify current turn and game-over state

## Current gaps

The following are still known gaps, not blockers:

- React does not yet draw a dedicated attack-line overlay
- React does not yet draw a dedicated defender-zone overlay
- resource tiles are not yet surfaced as first-class frontend objects
- hidden information flow is not yet designed

These should be treated as later refinements, not blockers for MVP validation.

## Related docs

- `docs/old_mick_mvp_rules.md`
- `docs/frontend_backend_contract_v1.md`
- `docs/authoritative_actions_v1.md`
- `docs/old_mick_core_test_cases.md`
- `docs/phaser_handoff_v1.md`
