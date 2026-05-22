# Documentation Index

This folder contains the main technical documentation for the current repository.

## How To Use This Folder

- Start at the root `README.md` for setup and launch instructions.
- Use this file to find the canonical technical document for each topic.
- Prefer the documents marked `Canonical` when updating behavior or onboarding new developers.

## Canonical Documents

| Topic | File | Status | Audience |
|------|------|--------|----------|
| General project setup and launch | `../README.md` | Canonical | Players, demo operators, developers |
| Documentation index | `docs/README.md` | Canonical | Everyone |
| System architecture | `docs/architecture.md` | Canonical | Developers, reviewers |
| External dependencies and licensing | `docs/dependencies_and_licenses.md` | Canonical | Developers, reviewers |
| Repository structure and responsibilities | `../README_PROJECT_MAP.md` | Canonical | Developers |
| Contributing, naming, and comment conventions | `../CONTRIBUTING.md` | Canonical | Developers |
| Runner entrypoints and support level | `../runner/README.md` | Canonical | Developers |
| Marker-driven setup and phase flow | `docs/setup_flow_backend_v1.md` | Canonical | Developers |
| Current payload/state contract | `docs/board_state_v1.md` | Canonical | Frontend/backend developers |
| Current action contract | `docs/authoritative_actions_v1.md` | Canonical | Frontend/backend developers |
| Manual and no-camera play | `docs/manual_play.md` | Canonical | Developers, testers |
| Browser protocol transport notes | `../protocol/websocket/contract.md` | Canonical | Frontend/backend developers |

## Supporting Documents

| Topic | File | Status | Notes |
|------|------|--------|-------|
| Audio asset reference | `docs/audio_assets.md` | Current reference | Tracks the active frontend audio manifest |
| Audio design and implementation notes | `docs/audio_plan.md` | Current reference | Planning/support document, not the runtime source of truth |

## Reference Or Historical Documents

These documents are still useful for context, but they are not the primary source of truth for the current runtime.

| File | Status | Notes |
|------|--------|-------|
| `docs/interaction_flow_v1.md` | Reference | Earlier interaction-model thinking; parts of it describe pre-current UI assumptions |
| `docs/old_mick_mvp_rules.md` | Reference | Game-rules background material |
| `../game_setup_and_documentation/old_mick_and_the_emus_gdd.html` | Historical | Legacy design document outside the canonical docs path |

## Recommended Reading Order For New Developers

1. `../README.md`
2. `docs/architecture.md`
3. `../README_PROJECT_MAP.md`
4. `../runner/README.md`
5. `docs/setup_flow_backend_v1.md`
6. `docs/board_state_v1.md`
7. `docs/authoritative_actions_v1.md`
8. `docs/manual_play.md`
9. `docs/dependencies_and_licenses.md`

## Documentation Maintenance Rules

- Update `README.md` when setup, launch, or operator flow changes.
- Update `docs/architecture.md` when component boundaries or runtime flow change.
- Update `docs/board_state_v1.md` and `docs/authoritative_actions_v1.md` when payloads or accepted actions change.
- Update `docs/dependencies_and_licenses.md` when adding or removing third-party libraries or externally sourced assets.
- If a document becomes historical, mark it clearly instead of leaving it ambiguous.
