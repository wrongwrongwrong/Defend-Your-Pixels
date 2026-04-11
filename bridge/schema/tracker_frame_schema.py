"""Schema helpers for versioned `tracker_frame` transport messages.

Tracker frames are camera/vision telemetry, not authoritative game state. They are
useful for debugging and for prototype UI behaviors (e.g. overlaying marker-derived
positions/rotations).
"""

SCHEMA_VERSION = 1


def build_tracker_frame(snapshot: dict) -> dict:
    """Build a versioned tracker frame message from a raw tracker snapshot.

    This message is NOT authoritative game state; it is camera/tracker telemetry
    used by the frontend to:
    - show calibration readiness / board corners
    - merge marker-derived positions into UI tokens (prototype behavior)

    Transport shape (JSON):
      {
        "type": "tracker_frame",
        "version": 1,
        "data": {
          "calibration_ready": bool,
          "markers": [...],
          "board_corners": [...]
        }
      }
    """
    return {
        "type": "tracker_frame",
        "version": SCHEMA_VERSION,
        "data": {
            # Whether homography / board mapping is stable enough to trust.
            "calibration_ready": snapshot.get("calibration_ready", False),
            # List of detected token markers; each entry typically includes id, position, rotation.
            "markers": snapshot.get("markers", []),
            # Four board corner points in camera coordinates (for visualization/debug).
            "board_corners": snapshot.get("board_corners", []),
        },
    }
