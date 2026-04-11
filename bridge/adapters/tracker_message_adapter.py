"""Tracker message adapter (telemetry snapshot -> transport).

This module mirrors `board_state_message_adapter`, but for tracker telemetry:
- accept the raw tracker snapshot dict
- wrap it in a versioned `tracker_frame` envelope
- serialize to JSON for WebSocket broadcast
"""

import json

from bridge.schema.tracker_frame_schema import build_tracker_frame


def build_tracker_message(snapshot: dict) -> str:
    """Serialize a tracker_frame message to JSON.

    Input:
    - `snapshot`: raw dict produced by `python_tracker.state_output.tracker_snapshot`

    Output:
    - JSON string ready to be sent via WebSocket broadcast.
    """
    return json.dumps(build_tracker_frame(snapshot))
