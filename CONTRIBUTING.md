# Contributing Guide

This guide keeps the repository consistent and professional across team members.

## Core principles

- Keep changes small and focused.
- Prefer clear naming over short naming.
- Avoid mixing unrelated concerns in one pull request.
- Preserve backward compatibility when refactoring.

## Folder naming conventions

- Use `kebab-case` for folder names: `react-frontend`, `tracker-service`.
- Use meaningful names based on responsibility.
- Avoid ambiguous names like `misc`, `temp`, or `stuff`.

## Python naming conventions

- Files/modules: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`

Examples:
- Good: `tracker_snapshot.py`, `model_action_dispatcher.py`
- Avoid: `TrackerSnapshot.py`, `utils2.py`

## JavaScript/React naming conventions

- React components: `PascalCase.jsx` or `PascalCase.tsx`
- Hooks: `useXxx.js` / `useXxx.ts`
- Utility modules: choose one style and keep it consistent (`camelCase` recommended)

Examples:
- Good: `BoardView.jsx`, `useWebSocket.js`, `adaptBoardStateToUi.js`
- Avoid: `board_view.jsx`, `websockethook.js`

## File responsibility rules

- One file should have one clear responsibility.
- Do not put business logic in runner scripts.
- Keep transport logic separate from game rules.
- Keep pure logic separate from UI rendering.

## Tests and validation

- Add or update tests for behavior changes.
- Use naming:
  - Python: `test_<module>.py`
  - Frontend: `<module>.test.js` or `<module>.spec.js`
- Run relevant local checks before committing.

## Documentation expectations

For each meaningful change, update docs when needed:
- Runtime behavior
- Message schema/protocol
- Setup/run instructions

Each major folder should have a short `README.md` with:
- purpose
- key files
- how to run/test

## Pull request checklist

Before opening a PR:

- [ ] Scope is focused (single topic)
- [ ] Naming follows conventions
- [ ] Tests/checks pass locally
- [ ] Docs updated if behavior changed
- [ ] No unrelated file changes included

## Commit message style

Use concise, intent-focused messages.

Recommended pattern:
- `feat: add tracker-frame adapter for UI`
- `fix: prevent invalid move from stale marker input`
- `docs: add architecture flow for bridge`
- `refactor: extract board state serializer`

