# Audio Assets Reference

This document tracks the current frontend audio manifest.

Canonical runtime source:

- `frontend/src/audio.js`

If this document and the code disagree, treat `frontend/src/audio.js` as authoritative and update this file.

## Current Manifest

| Audio key | File path(s) used by the frontend | Purpose |
|-----------|-----------------------------------|---------|
| `bgm_outback` | `assets/audio/bgm.mp3` | Main background music |
| `sfx_p1_attack` | `assets/audio/mick_attack.wav` | Old Mick attack fire |
| `sfx_p2_attack` | `assets/audio/emu_attack.wav` | Mob attack fire |
| `sfx_p1_hq_select` | `assets/audio/mick_trigger.mp3` | P1 trigger/select family |
| `sfx_p2_hq_select` | `assets/audio/emu_trigger.mp3` | P2 trigger/select family |
| `sfx_p1_defense` | `assets/audio/mick_trigger.mp3` | P1 defense family |
| `sfx_p2_defense` | `assets/audio/emu_trigger.mp3` | P2 defense family |
| `sfx_explosion` | `assets/audio/HQ_destroyed.mp3` | HQ destruction / large explosion |
| `sfx_destroy` | `assets/audio/HQ_destroyed.mp3` | Reused destruction cue |
| `sfx_tier_up` | `assets/audio/level_up.mp3` | Tier increase |
| `sfx_victory` | `assets/audio/win.mp3` | Win fanfare |
| `sfx_select` | `assets/audio/place_HQ.mp3` | UI confirm / placement / end turn |
| `sfx_page` | `assets/audio/intro.wav` | Intro/UI page cue |

## Synthesized Fallback Sound

The runtime also synthesizes one sound in code instead of loading a file:

| Audio key | Source | Purpose |
|-----------|--------|---------|
| `sfx_marker_turn` | Web Audio synth in `frontend/src/audio.js` | Token rotation feedback |

## Declared But Not Yet Backed By Files

The current code leaves these commented out as future additions:

- `sfx_block`
- `sfx_first_hit`
- `sfx_defeat`

Missing files should not crash the game. The frontend is intentionally tolerant of absent audio assets.

## Provenance Gap

The repository does not yet include a complete provenance and license record for every audio file in `frontend/assets/audio/`. See `docs/dependencies_and_licenses.md` for the current known gaps.
