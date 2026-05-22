# Contributing Guide

This repository favors small, well-scoped changes, clear naming, and documentation that stays aligned with the actual runtime.

## Core Principles

- Keep changes focused on one responsibility.
- Prefer explicit naming over short or clever naming.
- Preserve clear separation between tracker, rules, transport, runner, and frontend responsibilities.
- Update documentation whenever behavior, payload shape, setup flow, or supported runtime paths change.

## Naming Conventions

### Python

- Files/modules: `snake_case.py`
- Classes: `PascalCase`
- Functions: `snake_case`
- Variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`

Examples:

- Good: `tracker_snapshot.py`, `websocket_transport.py`, `GameModel`
- Avoid: `TrackerSnapshot.py`, `transportUtils.py`, `misc.py`

### JavaScript

- Scene files/classes: `PascalCase.js` with `PascalCase` exports for Phaser scenes
- General utility/browser modules: `camelCase.js` or established short lowercase names such as `ui.js`, `audio.js`, `constants.js`
- Functions/variables: `camelCase`
- Constants: `UPPER_SNAKE_CASE` when truly constant

Examples:

- Good: `IntroScene.js`, `GameScene.js`, `helpPopupTemplate.js`, `resolveWsUrl`
- Avoid: `intro_scene.js` inside the scenes folder, `Utils.js`, `stuff.js`

### Folders

- Use clear responsibility-based names.
- Avoid generic buckets such as `misc`, `temp`, or `stuff`.
- Keep archival or experimental material clearly separated from canonical runtime paths.

## File Responsibility Rules

- `backend/python_tracker/` owns vision and calibration logic.
- `backend/live_rules/` owns gameplay truth.
- `backend/bridge/` owns transport only.
- `runner/` assembles runtime modes and session flow; it should not absorb core game logic.
- `frontend/src/` owns browser presentation and interaction only.
- `protocol/` owns shared browser transport helpers and protocol notes.

One file should have one clear responsibility. When in doubt, prefer smaller focused changes over broad mixed edits.

## Comment Expectations

- Comment the reason for a decision, not the obvious mechanics of a line.
- Use comments to explain non-obvious control flow, protocol assumptions, or tricky runtime constraints.
- Keep comments short and factual.
- Remove or update comments when behavior changes.
- Do not leave comments that refer to outdated prototypes, removed flows, or no-longer-canonical behavior.

Good examples:

- explain why a payload field stays hidden
- explain why a setup phase ignores a command path
- explain why a transport queue exists instead of direct mutation

Avoid comments that only restate code such as "set variable to value".

## Documentation Expectations

The documentation set has a canonical path:

- `README.md` for general setup and launch
- `docs/README.md` for documentation routing
- `docs/architecture.md` for system structure
- `docs/board_state_v1.md` for payload shape
- `docs/authoritative_actions_v1.md` for accepted actions
- `docs/setup_flow_backend_v1.md` for marker-driven setup flow

Update the relevant document whenever you change:

- setup or launch instructions
- supported runtime modes
- payload or action contracts
- architecture boundaries
- naming or contribution rules

If a document becomes historical, mark it clearly rather than leaving conflicting instructions in place.

## Tests And Validation

- Run the checks that make sense for your change.
- For Python file changes, at minimum run syntax or type checks when available.
- For documentation-only changes, check links, commands, and file references against the actual repository.

This repository does not currently ship a formal test suite for all areas, so validation should be pragmatic and explicit.

## Pull Request Checklist

- [ ] Scope is focused
- [ ] Naming follows repository conventions
- [ ] Comments remain accurate and necessary
- [ ] Documentation was updated if behavior, setup, contracts, or runtime paths changed
- [ ] No unrelated files were changed

## Commit Message Style

Use concise, intent-focused commit messages.

Examples:

- `feat: add replay flow back to mode select`
- `fix: prevent duplicate websocket listeners on scene restart`
- `docs: reorganize onboarding and architecture references`
- `refactor: isolate battle payload handling`
