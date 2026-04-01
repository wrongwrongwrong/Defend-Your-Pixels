import json

from bridge.schema.tracker_frame_schema import build_tracker_frame


def build_tracker_message(snapshot: dict) -> str:
    return json.dumps(build_tracker_frame(snapshot))
