# Audio Plan

This document records the sound-design intent and maps each desired SFX
to the code that triggers it. Use it together with
`docs/audio_assets.md` (which lists filenames and where to drop mp3 files).

Status legend
- `Wired` - code already plays the sound when the matching event arrives.
- `Wired, needs validation` - code plays it, but depends on backend
  event timing or payload details that still need validation.
- `Pending` - needs additional event hook (frontend or backend) before
  it can fire.

## A. Marker rotation
Every time a marker on the board rotates noticeably.

| Sound key | Status | Trigger |
|-----------|--------|---------|
| `sfx_marker_turn` | Pending | Frontend needs to compare consecutive `state.p1.*.angle` / `state.p2.*.angle` and play once when delta > threshold. Could also fire on `turn_angle` change for the dedicated turn marker. |

Implementation note: detection should be debounced (for example ignore changes
smaller than 5 degrees) so camera jitter does not constantly fire it.

## B. Per-player actions

### B.1 HQ selection
When each side's HQ marker is locked in.

| Sound key | Status | Notes |
|-----------|--------|-------|
| `sfx_p1_hq_select` | Pending | Needs a backend event like `hq_locked` with a `side` field, or an equivalent frontend state-diff hook. |
| `sfx_p2_hq_select` | Pending | Same as above. |

The live frontend already references `hq_setup_complete` and `hq_markers` keys
in `state`. Once the exact HQ selection event shape is finalized, wiring is minimal.

### B.2 Attack fires
When the active player's ATK token actually shoots.

| Sound key | Status | Notes |
|-----------|--------|-------|
| `sfx_p1_attack` | Wired, needs validation | Currently fired on `cell_damaged` events that are not the first chip on a protected cell. |
| `sfx_p2_attack` | Pending | Best split would come from adding an `attacker` field to damage events, or by inferring it from turn state. |

### B.3 Defense activation
When a DEF token gets placed or moves into position.

| Sound key | Status | Notes |
|-----------|--------|-------|
| `sfx_p1_defense` | Pending | Frontend can detect a DEF token going from null to cell, or cell A to cell B, in successive states. |
| `sfx_p2_defense` | Pending | Same. |

## C. Damage stages
Two sounds: a chip on the first hit of a 2-HP cell, and a destroy sound on
the final hit.

| Sound key | Status | Trigger event |
|-----------|--------|---------------|
| `sfx_first_hit` | Wired | `cell_damaged` with `required_hp >= 2`. |
| `sfx_destroy` | Wired | `cell_destroyed`. |

## D. Tier upgrade
Same sound for every upgrade step.

| Sound key | Status | Trigger |
|-----------|--------|---------|
| `sfx_tier_up` | Wired | Frontend compares previous tier state, including per-token `state.game.atk_tiers` and `def_tier_p1` / `def_tier_p2`, and plays once whenever one increments. |

## E. Game end

| Sound key | Status | Trigger |
|-----------|--------|---------|
| `sfx_victory` | Wired | `attrition_win` event, or `state.game.winner` flipping non-null. |
| `sfx_defeat` | Pending | Needs the frontend to know which side the local player chose. |
| `sfx_explosion` | Wired | `hq_destroyed` event. |

## File checklist

These filenames should exist wherever the active frontend expects its audio assets:

- [ ] `bgm_outback.mp3`
- [ ] `sfx_marker_turn.mp3`
- [ ] `sfx_p1_hq_select.mp3`
- [ ] `sfx_p2_hq_select.mp3`
- [ ] `sfx_p1_attack.mp3`
- [ ] `sfx_p2_attack.mp3`
- [ ] `sfx_p1_defense.mp3`
- [ ] `sfx_p2_defense.mp3`
- [ ] `sfx_first_hit.mp3`
- [ ] `sfx_destroy.mp3`
- [ ] `sfx_tier_up.mp3`
- [ ] `sfx_victory.mp3`
- [ ] `sfx_defeat.mp3`
- [ ] `sfx_explosion.mp3`
- [ ] `sfx_block.mp3`
- [ ] `sfx_page.mp3`
- [ ] `sfx_select.mp3`

Missing files should only log a console warning and must not crash the game.

## Next steps

1. Add DEF placement detection.
2. Add marker rotation detection with debounce.
3. Decide whether HQ lock uses a dedicated event or a state-diff hook.
4. Add attacker-side information to damage events, or derive it from turn state.
5. Add defeat sound once local side-selection state is persisted in the frontend.
