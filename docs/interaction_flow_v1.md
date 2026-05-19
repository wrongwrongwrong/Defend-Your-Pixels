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

<<<<<<< Updated upstream
### Current pygame prototype behavior

- Attack mode highlights reachable line cells for the selected direction family.
- Preview follows the chosen direction.
- HUD explains that attack uses directional line attack.

### MVP limitation

Current React validation layer does not yet render a dedicated attack-line overlay.

This is acceptable for the current validation pass, but should be improved in later frontend work.
=======
### Current frontend behavior

The frontend renders attack-line previews from the active token positions and directions. The preview tints path cells, highlights the first target or terrain blocker, and the resolved `ray_complete` events animate the final path after `ID4` confirmation.
>>>>>>> Stashed changes

### Validation goal

First-time players should understand why an attack succeeded, failed, or hit a specific target.

## 4. Understanding the DEF zone

### Required player flow

The frontend should communicate that:

- defenders are passive anchors
- each defender protects a `3x3` area, expanding to `5x5` after the DEF upgrade threshold
- protected resource tiles require one extra hit
- cells whose DEF layer has already been consumed are no longer protected until the DEF token moves and resets the zone

### Current React validation behavior

<<<<<<< Updated upstream
- Defender meaning is currently explained via:
  - HUD labels
  - validation summary
  - footer / role text
- The React validation layer does **not** yet draw a dedicated DEF-zone overlay.

### Current pygame prototype behavior

- Debug HUD states that defenders provide passive `3x3` protection.
- Protected resource tiles are drawn brighter.
=======
- The board draws a DEF-zone overlay around each visible DEF token.
- The overlay is drawn cell-by-cell so consumed DEF cells appear as holes in the protection area.
- Consumed cells keep a broken-protection marker so players can distinguish "protection spent" from "resource destroyed".
- The DEF card's protected-cell count excludes destroyed cells and consumed DEF cells.
>>>>>>> Stashed changes

### Nuke target preview

When a side's one-use nuke is unlocked, `ID19` for `p1` or `ID29` for `p2` can be placed in enemy territory during that side's active turn. The backend exposes the valid target as `battle.pending_nuke`.

The frontend renders:

<<<<<<< Updated upstream
- rules text
- HUD wording
- backend result text
- brighter protected resource tiles in pygame
=======
- the side-specific nuke icon on the center cell
- a `3x3` orange/red target preview around that center
- the existing explosion animation after `ID4` confirms and the backend resolves the nuke
>>>>>>> Stashed changes

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

<<<<<<< Updated upstream
- React does not yet draw a dedicated attack-line overlay
- React does not yet draw a dedicated defender-zone overlay
- resource tiles are not yet surfaced as first-class frontend objects
- hidden information flow is not yet designed
=======
- resource tiles are still rendered from the live terrain payload rather than a normalized `resource_tiles[]` contract shape
- invalid nuke marker placement currently fails silently instead of drawing an invalid target marker
- HQ setup still depends on backend validation; browser-side previews are temporary and non-authoritative
>>>>>>> Stashed changes

These should be treated as later refinements, not blockers for MVP validation.

## Related docs

- `docs/old_mick_mvp_rules.md`
- `docs/frontend_backend_contract_v1.md`
- `docs/authoritative_actions_v1.md`
- `docs/old_mick_core_test_cases.md`
- `docs/phaser_handoff_v1.md`
