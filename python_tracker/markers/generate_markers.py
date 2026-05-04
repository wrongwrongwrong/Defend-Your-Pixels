"""
generate_markers.py
====================
Generates ArUco marker images you can print and place on the board.

Output:
  markers/
    corner_0_TL.png   ← tape to top-left  corner of the board
    corner_1_TR.png   ← tape to top-right corner
    corner_2_BL.png   ← tape to bottom-left corner
    corner_3_BR.png   ← tape to bottom-right corner
    token_10_P1_Infantry.png
    token_11_P1_Tank.png
    token_12_P1_Bomber.png
    token_13_P1_DEF.png
    token_14_P2_Infantry.png
    token_15_P2_Tank.png
    token_16_P2_Bomber.png
    token_17_P2_DEF.png

Run:
    python python_tracker/markers/generate_markers.py
Then print the PNGs at the size you want (e.g. 5cm × 5cm for tokens,
3cm × 3cm for corner markers).
"""

import os
import cv2
import numpy as np

OUTPUT_DIR   = "markers"
MARKER_SIZE  = 200   # pixels per marker image (before adding white border)
BORDER_PX    = 20    # white border around each marker

ARUCO_DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)

MARKERS = {
    # Board corners
    0:  "corner_0_TL",
    1:  "corner_1_TR",
    2:  "corner_2_BL",
    3:  "corner_3_BR",
    # Player 1 tokens
    10: "token_10_P1_Infantry",
    11: "token_11_P1_Tank",
    12: "token_12_P1_Bomber",
    13: "token_13_P1_DEF",
    # Player 2 tokens
    14: "token_14_P2_Infantry",
    15: "token_15_P2_Tank",
    16: "token_16_P2_Bomber",
    17: "token_17_P2_DEF",
}

os.makedirs(OUTPUT_DIR, exist_ok=True)

for marker_id, name in MARKERS.items():
    # Generate marker image
    img = cv2.aruco.generateImageMarker(ARUCO_DICT, marker_id, MARKER_SIZE)

    # Add white border so the detector can find it on any background
    bordered = cv2.copyMakeBorder(
        img,
        BORDER_PX, BORDER_PX, BORDER_PX, BORDER_PX,
        cv2.BORDER_CONSTANT,
        value=255,
    )

    # Add label below
    label_h = 30
    label = np.full((label_h, bordered.shape[1]), 200, dtype=np.uint8)
    cv2.putText(label, f"ID {marker_id} — {name.split('_', 2)[-1]}",
                (4, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, 0, 1, cv2.LINE_AA)

    combined = np.vstack([bordered, label])

    path = os.path.join(OUTPUT_DIR, f"{name}.png")
    cv2.imwrite(path, combined)
    print(f"  Saved: {path}")

print(f"\nDone — {len(MARKERS)} markers saved to '{OUTPUT_DIR}/'")
print("Print them and place corner markers at the board edges.")
