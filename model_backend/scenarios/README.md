# model_backend.scenarios

Purpose: define authoritative game-start scenarios used by backend-driven runtime paths.

## Responsibility

- Own scenario/level loading that produces a `model_backend.game.GameState`
- Own scenario files used by live backend entrypoints such as `runner/run_live_tracker.py`
- Stay separate from transport (`bridge`) and UI (`react_frontend`)
- Stay separate from core game rules in `model_backend/game`

## Current usage

- `runner/run_live_tracker.py` loads `build_react_integration_level()` from this package

## Relationship to prototype_pygame

- `prototype_pygame/levels` is still kept for prototype flows and project history
- Live tracker should not import scenarios from `prototype_pygame/levels`
- If a scenario is meant for authoritative backend runtime, prefer adding it here

## Files

- `level_loader.py`: ASCII map -> `GameState`
- `react_integration_level.py`: live tracker default scenario factory
- `react_integration_level.txt`: live tracker default ASCII map
