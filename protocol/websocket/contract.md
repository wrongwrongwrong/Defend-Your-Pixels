# WebSocket Protocol

This folder contains browser-side helpers and notes for connecting the frontend to the Python live runtime.

## Server

- Default URL: `ws://localhost:8765`
- Override port via query string: `http://localhost:8080?ws_port=8765`
- The HTTP frontend server exposes this folder at `/protocol/` so browser modules can import shared protocol code

## Server To Browser

The current Python runtime broadcasts the full state as a raw JSON object.

It is not wrapped in a `{ "type", "data" }` envelope.

Common top-level fields include:

- `phase`
- `mode`
- `setup`
- `battle`
- `terrain`
- `game`
- `p1`
- `p2`
- `hq_markers`
- `events`
- `errors`
- `help_visible`
- `tutorial`
- `manual_controls`

## Browser To Server

Normal UI commands are sent as action messages:

```json
{
  "type": "action",
  "data": {
    "action": "select_mode",
    "mode": "normal"
  }
}
```

Examples of action names currently used by the frontend or runtimes:

- `select_mode`
- `return_to_mode_select`
- `trigger_nuke`
- `tutorial_dismiss`
- `tutorial_undo`
- `place_token`
- `rotate_token`
- `end_turn`

Fallback/debug setup actions may also exist in some runtimes:

- `choose_side`
- `set_hq_candidate`
- `confirm_hq`
- `reset_setup`
- `cancel_hq`

## Top-Level Transport Commands

Some debug/dev transport commands remain top-level messages:

```json
{ "type": "new_map" }
```

```json
{ "type": "tier", "player": 1, "delta": 1 }
```

```json
{ "type": "demo_next" }
```

Use `browser_client.js` from browser UI code to keep this wrapping consistent.

## Related Documents

- `docs/board_state_v1.md`
- `docs/authoritative_actions_v1.md`
