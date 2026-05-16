# Manual Play Mode

## Overview

This repository now includes an add-only manual play mode that lets you drive the current live game without ArUco markers.

The existing marker-based flow is unchanged.

Manual mode:
- uses the mainline frontend served over HTTP
- keeps using the same WebSocket host and port
- keeps using `live_rules/game_model.py` and `live_rules/terrain_gen.py`
- replaces marker input with terminal commands

## Files

- `runner/run_manual_play.py`
- `docs/manual_play.md`

## How To Launch

From the repository root, start the manual runner directly:

```powershell
.venv\Scripts\python -m runner.run_manual_play
```

This will:
- start `runner.run_manual_play`

Open `http://localhost:8080` separately in your browser.

## Terminal Commands

Type commands into the manual runner terminal window.

Available commands:

```text
help
show
show_setup
choose_side old_mick
choose_side mob
set_hq p1 A3
confirm_hq p1
reset_setup
set p1 atk_a A3 E
set p1 atk_b C4 NW
set p1 def D5
set p2 atk_a J9 W
clear p1 atk_a
turn 1
turn 2
flip
new_map
tier 1 +1
tier 2 -1
quit
```

Rules for commands:
- board cells use `A1` through `L12`
- attackers need a direction: `E`, `SE`, `S`, `SW`, `W`, `NW`, `N`, `NE`
- defenders only need a position
- choose a setup side before confirming HQs
- use `set_hq` and `confirm_hq` to finish hidden HQ setup
- `flip` toggles turn `1 <-> 2`
- `turn 1` or `turn 2` sets the current turn explicitly
- `new_map` regenerates terrain and resets the setup flow
- `tier` changes the same tier values the browser UI already renders
- `show` prints a readable summary of the current state
- `show_setup` prints setup-only progress and status

## Example Session

```text
set p1 atk_a A3 E
set p1 atk_b B4 SE
set p1 def C5
set p2 atk_a J9 W
set p2 atk_b K8 NW
set p2 def H8
show
flip
show
new_map
quit
```

Typical flow:
1. Launch the manual runner.
2. Choose the first setup side with `choose_side old_mick` or `choose_side mob`.
3. Set and confirm both HQs with `set_hq` and `confirm_hq`.
4. Place both sides with `set` commands.
5. Open or watch `http://localhost:8080`.
6. Use `flip` or `turn 1` / `turn 2` to advance the battle and trigger attack resolution.
7. Use `show` or `show_setup` whenever you want a terminal-side summary.

## Notes and Limitations

- This mode is terminal-controlled, not browser-click controlled.
- The browser page is now the mainline frontend at `http://localhost:8080`.
- Do not run manual mode and marker mode at the same time. Both use `ws://localhost:8765`.
- Manual mode is add-only and does not replace the existing marker-driven flow.
- `corners_found` is reported as ready in manual mode so the existing UI can render normally without tracker input.
- `new_map` resets the terrain and setup flow. Token placements remain under your manual control and can be updated with more `set` or `clear` commands.
- HQ positions are chosen during setup but remain hidden from the public payload after confirmation.
