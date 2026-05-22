# Audio Plan

This document is a design-and-implementation reference for audio behavior.

Canonical runtime source:

- `frontend/src/audio.js` for the active manifest and playback helpers

This file is useful for planning and validation, but it is not the source of truth for filenames or exact loaded paths.

## Current Runtime Coverage

### Already wired in code

- background music
- attack sounds
- trigger/select sounds
- destruction/explosion sounds
- tier-up sound
- victory sound
- selection sound
- synthesized marker-rotation click

### Partially wired or still design-oriented

- dedicated block sound
- dedicated first-hit sound
- defeat sound
- richer HQ-lock/defense-placement specific cues

## Runtime Mapping Summary

| Event family | Current runtime status | Notes |
|--------------|------------------------|-------|
| Marker rotation | Wired via synth | Implemented in browser interaction flow |
| Attack fire | Wired | Per-side attack sounds are loaded |
| HQ/select trigger family | Wired | Shared files are currently reused |
| Defense trigger family | Wired | Shared files are currently reused |
| Destruction/explosion | Wired | HQ and destruction reuse the current available files |
| Tier-up | Wired | Frontend state diff triggers playback |
| Victory | Wired | Frontend win path plays victory |
| Defeat | Planned | No dedicated current runtime path |

## Maintenance Rule

If a filename or audio key changes in `frontend/src/audio.js`, update `docs/audio_assets.md` first and then revise this document if the design intent also changed.
