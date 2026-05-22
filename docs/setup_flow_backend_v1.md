# Setup Flow Backend v1

This document defines the current public phase model and the marker-driven HQ setup flow for the live runtime.

## Public Phase Order

The current runtime can expose these public phases:

1. `mode_select`
2. `scan`
3. `hq_placement`
4. `game`

Meaning:

- `mode_select`: no mode has been chosen yet
- `scan`: waiting for a valid board scan in the live tracker path
- `hq_placement`: hidden HQ setup is active
- `game`: battle phase is active

The backend is authoritative for all phase transitions.

## Marker-Driven Phase Flow

1. Start at `mode_select`.
2. After a mode is chosen, enter `scan` in the live tracker path.
3. Stay in `scan` until the board markers are readable.
4. Move to `hq_placement` once the board scan is ready.
5. During `hq_placement`, the first stable visible turn marker decides which side hides an HQ first.
6. The active side places its HQ marker on a valid cell.
7. Scanning `ID4` locks the active side's valid HQ candidate.
8. Setup control transfers to the other side.
9. Enter `game` only after both HQ locations are locked.

## Marker Roles Used By Setup

- board corners:
  - `0` top-left
  - `1` top-right
  - `2` bottom-left
  - `3` bottom-right
- setup markers:
  - `10` = `P1 TURN`
  - `11` = `P1 HQ`
  - `20` = `P2 TURN`
  - `21` = `P2 HQ`
  - `4` = shared `CONFIRM`

## Marker Roles Used By Gameplay

- `10` = begin `P1` positioning during battle
- `20` = begin `P2` positioning during battle
- `12` / `13` / `14` = `P1 ATK A` / `ATK B` / `DEF`
- `19` = `P1 NUKE`
- `22` / `23` / `24` = `P2 ATK A` / `ATK B` / `DEF`
- `29` = `P2 NUKE`
- `4` = shared battle confirm; resolves the active side's turn

## Hidden HQ Rule

- HQ locations are chosen during setup.
- The backend stores the true HQ coordinates internally.
- Confirmed HQ coordinates remain hidden from the public payload during normal play.
- HQ positions are only revealed through gameplay outputs such as `hq_revealed` after destruction.

## Safe Public Setup Payload

The public payload exposes only safe setup metadata:

- `setup.board_scan_ready`
- `setup.side_selection_complete`
- `setup.first_player_side`
- `setup.active_setup_side`
- `setup.hq.*.has_candidate`
- `setup.hq.*.confirmed`
- `setup.status_code`
- `setup.status_message`

It must not expose confirmed hidden HQ coordinates.

## Validation Rules

- `c + r < 11` => `p1`
- `c + r > 11` => `p2`
- `c + r == 11` => fence
- HQ must be on its own side and not on the fence.
- HQ must not overlap blocked terrain.
- Reserved corner cells are invalid HQ cells:
  - `p1`: `A1`, `A2`, `B1`
  - `p2`: `L12`, `L11`, `K12`

## Fallback And Debug Commands

The following commands still exist for fallback or manual/debug paths:

- `choose_side`
- `set_hq_candidate`
- `confirm_hq`
- `reset_setup`
- `cancel_hq`

They are documented in `docs/authoritative_actions_v1.md`, but they are not the primary live setup path for the camera-driven runtime.

## Related Documents

- `docs/board_state_v1.md`
- `docs/authoritative_actions_v1.md`
- `docs/manual_play.md`
- `docs/architecture.md`
