SCHEMA_VERSION = 1


def build_action_message(action: dict) -> dict:
    return {
        "type": "action",
        "version": SCHEMA_VERSION,
        "data": action,
    }
