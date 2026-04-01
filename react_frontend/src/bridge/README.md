# Bridge Translation

Purpose
- keep tracker-frame parsing and semantic translation out of React hooks
- convert raw marker observations into game-facing token updates

Current files
- `translation/normalizeTrackerFrame.js`: normalize incoming tracker payloads
- `translation/tokenRegistry.js`: map marker ids to token/game metadata
- `translation/rotationMapping.js`: convert tracker rotation degrees to game-facing directions
- `translation/translateTrackerFrame.js`: build translated tracked-token state and apply it to UI game state
