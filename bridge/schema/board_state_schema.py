SCHEMA_VERSION = 1


def build_board_state(payload: dict) -> dict:
    return {
        "type": "board_state",
        "version": SCHEMA_VERSION,
        "data": payload,
    }
