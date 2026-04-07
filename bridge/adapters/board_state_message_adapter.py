import json

from bridge.schema.board_state_schema import build_board_state


def build_board_state_message(payload: dict) -> str:
    return json.dumps(build_board_state(payload))
