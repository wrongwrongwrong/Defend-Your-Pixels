"""Token rotation helpers.

Given a 4-corner ArUco marker polygon, compute a stable rotation angle in degrees
for UI/telemetry purposes.
"""

import math


def compute_rotation_deg(corners4) -> float:
    tl = corners4[0]
    tr = corners4[1]
    dx = float(tr[0] - tl[0])
    dy = float(tr[1] - tl[1])
    angle_deg = math.degrees(math.atan2(dy, dx))
    return (angle_deg + 360) % 360
