"""Board-state message adapter (authoritative state -> transport).

Responsibilities:
- accept a board-state `payload` dict produced by the authoritative `model_backend`
- wrap it in a versioned transport envelope via `bridge.schema.board_state_schema.build_board_state`
- serialize to a JSON string so the WebSocket layer can broadcast it as-is

Design constraints:
- no rules/validation here (the model is authoritative)
- keep the frontend-facing shape/version stable
"""

import json

from bridge.schema.board_state_schema import build_board_state


def build_board_state_message(payload: dict) -> str:
    """Serialize a versioned board_state envelope to a JSON string."""
    return json.dumps(build_board_state(payload))
