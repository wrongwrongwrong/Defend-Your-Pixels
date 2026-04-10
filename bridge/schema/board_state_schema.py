"""Schema helpers for versioned `board_state` transport messages.

The authoritative game state lives in `model_backend`. This module only defines a
stable transport envelope for shipping that state over WebSocket.

See also:
- `docs/board_state_v1.md` for the minimal payload contract inside `data`.
"""

SCHEMA_VERSION = 1


def build_board_state(payload: dict) -> dict:
    """Wrap an authoritative board state dict in a versioned message envelope.

    Transport shape (JSON):
      {
        "type": "board_state",
        "version": 1,
        "data": { ... authoritative state ... }
      }

    The `data` field should follow the minimal contract described in:
    - docs/board_state_v1.md
    """
    return {
        "type": "board_state",
        "version": SCHEMA_VERSION,
        "data": payload,
    }
