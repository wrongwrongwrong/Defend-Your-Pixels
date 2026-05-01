# Audio plan — yu_test2

This document records the sound-design intent and maps each desired SFX
to the code that triggers it. Use it together with
`frontend/assets/audio/README.md` (which lists filenames + where to drop
mp3 files).

Status legend
- ✅ **Wired** — code already plays the sound when the matching event arrives.
- 🟡 **Wired, needs validation** — code plays it, but depends on backend
  event the FW2 backend may or may not emit yet.
- ⏳ **Pending** — needs additional event hook (frontend or backend) before
  it can fire.

---

## A. Marker rotation
Every time a marker on the board rotates noticeably.

| Sound key             | Status | Trigger                                                           |
|-----------------------|--------|-------------------------------------------------------------------|
| `sfx_marker_turn`     | ⏳     | Frontend needs to compare consecutive `state.p1.*.angle` /        |
|                       |        | `state.p2.*.angle` and play once when delta > threshold.          |
|                       |        | (Could also fire on `turn_angle` change for the dedicated turn    |
|                       |        | marker as a separate `sfx_turn`.)                                 |

Implementation note: detection should be **debounced** (e.g. ignore changes
< 5°) so micro-jitter from camera noise doesn't constantly fire it.

---

## B. Per-player actions

### B.1  HQ selection
When each side's HQ marker is locked in.

| Sound key              | Status | Notes                                                            |
|------------------------|--------|------------------------------------------------------------------|
| `sfx_p1_hq_select`     | ⏳     | Needs FW2 backend to emit an event like `hq_locked` with a       |
|                        |        | `side` field. Frontend would handle it in the `events` switch.   |
| `sfx_p2_hq_select`     | ⏳     | Same as above.                                                   |

The yu_test1 frontend already references `hq_setup_complete` and
`hq_markers` keys in `state` — once we know the exact shape of HQ
selection events from FW2, wiring is one line each.

### B.2  Attack fires
When the active player's ATK token actually shoots.

| Sound key         | Status | Notes                                                                |
|-------------------|--------|----------------------------------------------------------------------|
| `sfx_p1_attack`   | 🟡     | Currently fired on every `cell_damaged` event without a              |
|                   |        | `required_hp ≥ 2` check. Once events carry an `attacker` or `side`   |
|                   |        | field we can split P1 vs P2.                                         |
| `sfx_p2_attack`   | ⏳     | Pending an `attacker` field on damage events. FW2 game_model already |
|                   |        | knows `attacker` internally — just needs to be added to the event.   |

Quick alternative: derive `attacker` on the frontend from `state.turn`
(the player whose turn is ending = the attacker). That works without
backend changes.

### B.3  Defense activation
When a DEF token gets placed or moves into position.

| Sound key         | Status | Notes                                                              |
|-------------------|--------|--------------------------------------------------------------------|
| `sfx_p1_defense`  | ⏳     | Frontend can detect a DEF token going from null → cell             |
|                   |        | (or cell-A → cell-B) in successive states.                         |
| `sfx_p2_defense`  | ⏳     | Same.                                                              |

---

## C. Damage stages
Two sounds — a "chip" on the first hit of a 2-HP cell, a "destroy" on the
final hit.

| Sound key       | Status | Trigger event                                                        |
|-----------------|--------|----------------------------------------------------------------------|
| `sfx_first_hit` | ✅     | `cell_damaged` with `required_hp >= 2` (DEF-zone cells).             |
| `sfx_destroy`   | ✅     | `cell_destroyed` (any cell).                                         |

Note: a cell **outside** the DEF zone has 1 HP, so a hit on it goes
straight to `cell_destroyed` (one shot kill) → only `sfx_destroy` plays.
This matches the rule.

---

## D. Tier upgrade
Same sound for every upgrade step (1 → 2 → 3 → 4).

| Sound key     | Status | Trigger                                                                 |
|---------------|--------|-------------------------------------------------------------------------|
| `sfx_tier_up` | ✅     | Frontend compares previous and current `state.game.tier_p1` /           |
|               |        | `tier_p2`; plays once whenever either increments.                        |

---

## E. Game end

| Sound key      | Status | Trigger                                                                |
|----------------|--------|------------------------------------------------------------------------|
| `sfx_victory`  | ✅     | `attrition_win` event, or `state.game.winner` flipping non-null.       |
| `sfx_defeat`   | ⏳     | Needs the frontend to know which side the local player chose so it     |
|                |        | can decide victory vs defeat. Hold off until we wire side-selection    |
|                |        | properly.                                                              |
| `sfx_explosion`| ✅     | `hq_destroyed` event — the dramatic stinger when HQ falls.             |

---

## File checklist

Drop these into `frontend/assets/audio/` (filenames must match exactly):

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

Missing files just log a console warning — they don't crash the game,
so add them incrementally and listen as each one drops in.

---

## Next steps to fully wire this list

1. **DEF placement detection** (B.3) — track DEF tok col/row deltas in
   `_renderTokens` and fire a one-shot.
2. **Marker rotation detection** (A) — same approach: compare angles
   between successive states with a debounce threshold.
3. **HQ-lock event** (B.1) — coordinate with backend to emit
   `{type: "hq_locked", side: "p1"}` (or similar) when each HQ is
   confirmed.
4. **Attacker side on damage events** (B.2 split) — backend should add
   `"attacker": "p1"` to `cell_damaged` / `cell_destroyed` events, OR
   frontend can infer from `state.turn`.
5. **Defeat sound** (E) — hook side selection (currently the IntroScene
   sends `choose_side` but doesn't store it locally) so we know which
   sound the local player should hear.
