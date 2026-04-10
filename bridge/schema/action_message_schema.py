"""Schema helpers for versioned `action` transport messages.

This module defines the minimal envelope used over WebSocket so that:
- clients can identify message type (`type: "action"`)
- producers/consumers can evolve the payload safely via `version`

The envelope wraps a raw action dict that is ultimately dispatched to the model
by the bridge action dispatcher.
"""

SCHEMA_VERSION = 1


def build_action_message(action: dict) -> dict:
    """Wrap a raw action payload in a versioned message envelope.

    Transport shape (JSON):
      {
        "type": "action",
        "version": 1,
        "data": { ... action dict ... }
      }

    Notes:
    - The frontend typically sends this envelope to the WS server.
    - The server extracts `data` and dispatches to `model_backend` via the bridge.
    """
    return {
        "type": "action",
        "version": SCHEMA_VERSION,
        "data": action,
    }
