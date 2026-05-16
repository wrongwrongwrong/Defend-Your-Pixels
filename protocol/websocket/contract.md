# WebSocket Protocol

This folder contains browser-side helpers and notes for connecting a frontend to the Python live runtime.

## Server

- Default URL: `ws://localhost:8765`
- The HTTP frontend server also exposes this folder at `/protocol/` so browser modules can import shared protocol code.

## Server To Browser

The current Python runtime broadcasts the full state as a raw JSON object. It is not wrapped in a `{ "type", "data" }` envelope.

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

## Browser To Server

Normal UI commands are sent as action messages:

```json
{
  "type": "action",
  "data": {
    "action": "choose_side",
    "first_player_side": "old_mick"
  }
}
```

The current debug/dev transport commands remain top-level messages:

```json
{ "type": "new_map" }
```

```json
{ "type": "tier", "player": 1, "delta": 1 }
```

Use `browser_client.js` from browser UI code to keep this wrapping consistent.
