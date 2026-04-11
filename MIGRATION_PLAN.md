# Migration Plan - Clean Professional Structure

This document proposes a safe, incremental migration from the current repository layout to a more maintainable and scalable structure.

## Target structure (long-term)

```text
defend-your-pixels/
├─ apps/
│  ├─ tracker-service/
│  ├─ game-service/
│  ├─ bridge-service/
│  └─ web-client/
├─ packages/
│  ├─ vision-core/
│  ├─ game-core/
│  ├─ protocol/
│  └─ common/
├─ scripts/
├─ docs/
├─ infra/
├─ tests/
└─ README.md
```

## Migration philosophy

- Do not break working runtime while restructuring.
- Move in small, testable steps.
- Prefer compatibility wrappers during transition.
- Keep PRs focused and easy to review.

---

## Phase 1 - Documentation and standards first (low risk)

Goal: improve readability immediately without moving core code.

### Tasks

1. Add system mapping docs:
   - `README_PROJECT_MAP.md`
   - Update root `README.md` with folder overview
2. Add team conventions:
   - `CONTRIBUTING.md`
3. Standardize naming on new files only:
   - Python: `snake_case.py`
   - React components: `PascalCase`
   - Hooks: `useXxx`
4. Add root placeholders for future layout:
   - `apps/`, `packages/`, `scripts/`, `infra/`, `tests/`

### Exit criteria

- New contributors can understand folder purposes in under 15 minutes.
- Team follows one naming convention.
- No runtime behavior changes introduced.

---

## Phase 2 - Extract shared foundations (moderate risk)

Goal: reduce coupling and duplication across modules.

### Tasks

1. Create `packages/protocol/`:
   - Move shared message schemas/contracts here.
   - Update `bridge`, `model_backend`, and frontend adapters to import from one source.
2. Create `packages/common/`:
   - Shared logging/config helpers.
3. Begin extraction of pure logic:
   - Vision utilities -> `packages/vision-core/`
   - Game rules/state core -> `packages/game-core/`
4. Add unit tests around extracted modules.

### Exit criteria

- Shared contracts have one authoritative location.
- Core logic is reusable and less tied to runtime folders.
- Existing demos still run.

---

## Phase 3 - Move runtimes into apps (higher impact)

Goal: complete professional app/package separation.

### Tasks

1. Create runtime app folders:
   - `apps/tracker-service`
   - `apps/game-service`
   - `apps/bridge-service`
   - `apps/web-client`
2. Move entrypoints from current locations into corresponding `apps/*`.
3. Move one-off run helpers into `scripts/`.
4. Move deployment artifacts into `infra/`.
5. Add integration tests under `tests/integration/`.
6. Keep temporary compatibility wrappers for old paths, then remove later.

### Exit criteria

- Each runtime has a clear entrypoint and ownership boundary.
- Integration tests validate end-to-end data flow.
- Old layout paths are fully deprecated and removed.

---

## Suggested timeline

- Week 1: Phase 1
- Week 2-3: Phase 2
- Week 4: Phase 3

If deadline is close, complete Phase 1 and partial Phase 2 for strong professional documentation with minimal risk.

## Branching strategy

- `chore/docs-and-standards`
- `refactor/protocol-package`
- `refactor/extract-game-core`
- `refactor/extract-vision-core`
- `refactor/apps-migration`

Guidelines:
- One objective per branch.
- Small PRs.
- Include run instructions in each PR.

## Risk management checklist

- [ ] Tag a stable baseline before each phase
- [ ] Keep old import compatibility during migration
- [ ] Run smoke tests after each move
- [ ] Avoid large rename-only PRs without tests
- [ ] Freeze major feature work during final cutover

## Definition of done

- Architecture is understandable from docs.
- Shared contracts are centralized.
- Runtimes are separated from reusable packages.
- CI validates lint/tests/build.
- Team can onboard quickly and contribute safely.

