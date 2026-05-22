# Dependencies And Licenses

## Purpose

This document records the main third-party code dependencies and known licensing information visible from this repository at documentation time.

## Scope

- Python packages declared in `requirements.txt`
- packaging metadata declared in `pyproject.toml`
- bundled browser-side third-party code where identifiable from the repository
- known gaps where the repository does not pin or record enough metadata

## Python Runtime And Packaging

| Item | Version declared in repo | Purpose | License | Source evidence |
|------|--------------------------|---------|---------|-----------------|
| Python | `>=3.10` | Minimum runtime version | Python Software Foundation License | `pyproject.toml` |
| setuptools | `>=61` | Build backend | MIT | `pyproject.toml` build-system requirement |

## Python Application Dependencies

| Package | Version declared in repo | Purpose in this project | License | Notes |
|---------|--------------------------|-------------------------|---------|-------|
| `opencv-contrib-python` | Not pinned in `requirements.txt` | Camera access and ArUco marker tooling via OpenCV contrib build | Apache-2.0 | Repo does not declare an exact version; PyPI metadata identifies the package license as Apache 2.0 |
| `websockets` | Not pinned in `requirements.txt` | WebSocket server transport between Python runtime and browser | BSD-3-Clause | Repo does not declare an exact version |
| `numpy` | Not pinned in `requirements.txt` | Numeric and array operations used by the tracker path | BSD-style multi-license package | Repo does not declare an exact version |
| `django` | `5.0.0` | Present in requirements; not part of the primary live runtime path documented in this repo | BSD-3-Clause | Explicitly pinned in `requirements.txt` |

## Browser-Side Dependencies

| Dependency | Version declared in repo | Purpose | License | Notes |
|-----------|--------------------------|---------|---------|-------|
| `Phaser` | Exact bundled version not declared in repository | Main browser game framework | Version/license should be verified from the bundled artifact before redistribution | The repo ships `frontend/phaser.min.js`, but the exact artifact version is not declared in-repo |

## Project-Local Browser Platform Dependencies

These are platform capabilities rather than package-managed dependencies:

- WebSocket API
- DOM APIs
- Canvas rendering via Phaser
- Web Audio API for synthesized fallback sounds

They do not have repository-managed package versions.

## External Assets And Sources

### Markers

- The repository includes generated marker image assets in `markers/`.
- A printable `markersv2.pdf` is also present.
- The repository does not currently record the generation workflow or original source metadata for the PDF artifact.

### Audio

- The current audio manifest is defined in `frontend/src/audio.js`.
- The repository does not currently include a complete provenance record for every audio asset in `frontend/assets/audio/`.

### Images And Tutorial Media

- The repository contains first-party game art, tutorial GIFs, and board UI assets under `frontend/assets/`.
- Some assets appear historical or archival, especially under `frontend/assets/images/archive/`.
- The repository does not currently provide a complete provenance manifest for every image or GIF.

## Data Sets

- No separate machine-learning dataset or training dataset is documented in the current repository.
- The tracker operates on live camera input and marker layouts rather than a bundled labelled dataset.

## Known Documentation Gaps

The following items should be verified if the project is being prepared for formal release, assessment, or distribution:

1. Exact installed versions for unpinned Python packages in `requirements.txt`
2. Exact version and license provenance for the bundled `frontend/phaser.min.js` artifact
3. Provenance and licensing for audio assets in `frontend/assets/audio/`
4. Provenance and licensing for tutorial GIFs and any non-original art assets
5. Whether `django==5.0.0` is still required by the active codebase or is a leftover dependency

## Sources Used For This Document

- Repository files:
  - `pyproject.toml`
  - `requirements.txt`
  - `frontend/src/audio.js`
  - `frontend/phaser.min.js`
- Package metadata reviewed from official package indexes:
  - Django `5.0.0` PyPI metadata
  - NumPy PyPI metadata
  - websockets PyPI metadata
  - opencv-contrib-python PyPI metadata

Where the repository does not pin an exact version, this document reports that gap explicitly instead of inferring an installed version.
