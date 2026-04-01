SCHEMA_VERSION = 1


def build_tracker_frame(snapshot: dict) -> dict:
    return {
        "type": "tracker_frame",
        "version": SCHEMA_VERSION,
        "data": {
            "calibration_ready": snapshot.get("calibration_ready", False),
            "markers": snapshot.get("markers", []),
            "board_corners": snapshot.get("board_corners", []),
        },
    }
