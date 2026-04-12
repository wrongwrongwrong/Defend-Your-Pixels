"""
generate_board.py

Generates a printable A4 board image (board.png) for PixelWar.

Layout:
  - 4 corner ArUco markers printed OUTSIDE the 12×12 playable grid
  - 12×12 grid with Blue (upper-left) and Red (lower-right) territories
  - Diagonal neutral strip
  - Turn marker zone on the right side
  - Column (A–L) and row (1–12) labels so players know where to place tokens
"""

import cv2
import numpy as np

# ── Page size (A4 at 150 DPI) ──────────────────────────────────────────────
DPI    = 150
A4_W   = int(8.27  * DPI)   # 1240 px
A4_H   = int(11.69 * DPI)   # 1753 px

# ── Layout measurements ────────────────────────────────────────────────────
MARGIN        = 60    # outer page margin
MARKER_SIZE   = 70    # ArUco corner marker size (px)
MARKER_GAP    = 10    # gap between marker and grid edge
TURN_ZONE_W   = 140   # width of the turn marker zone on the right

# Compute grid area (sits between the corner markers)
GRID_X = MARGIN + MARKER_SIZE + MARKER_GAP
GRID_Y = MARGIN + MARKER_SIZE + MARKER_GAP
GRID_W = A4_W - 2 * MARGIN - 2 * (MARKER_SIZE + MARKER_GAP) - TURN_ZONE_W - 20
GRID_H = A4_H - 2 * MARGIN - 2 * (MARKER_SIZE + MARKER_GAP)

COLS = 12
ROWS = 12
CELL_W = GRID_W // COLS
CELL_H = GRID_H // ROWS

# Re-snap grid dimensions to exact cell multiples
GRID_W = CELL_W * COLS
GRID_H = CELL_H * ROWS

# ── Colours (BGR) ─────────────────────────────────────────────────────────
WHITE      = (255, 255, 255)
BLACK      = (  0,   0,   0)
LIGHT_GREY = (220, 220, 220)
BLUE_LIGHT = (210, 220, 255)   # Blue territory fill
RED_LIGHT  = (255, 210, 210)   # Red territory fill
DIAG_GREY  = (200, 200, 200)   # Neutral diagonal strip
TURN_BG    = (240, 245, 230)   # Turn zone background


def draw_board():
    img = np.full((A4_H, A4_W, 3), 255, dtype=np.uint8)

    # ── Grid cells ──────────────────────────────────────────────────────────
    for r in range(ROWS):
        for c in range(COLS):
            x = GRID_X + c * CELL_W
            y = GRID_Y + r * CELL_H
            s = r + c

            if   s < 11: color = BLUE_LIGHT
            elif s > 11: color = RED_LIGHT
            else:        color = DIAG_GREY

            cv2.rectangle(img, (x, y), (x + CELL_W, y + CELL_H), color, -1)

    # ── Grid lines ──────────────────────────────────────────────────────────
    for c in range(COLS + 1):
        x = GRID_X + c * CELL_W
        cv2.line(img, (x, GRID_Y), (x, GRID_Y + GRID_H), BLACK, 1)
    for r in range(ROWS + 1):
        y = GRID_Y + r * CELL_H
        cv2.line(img, (GRID_X, y), (GRID_X + GRID_W, y), BLACK, 1)

    # ── Column labels (A–L) above the grid ──────────────────────────────────
    col_labels = list("ABCDEFGHIJKL")
    for c in range(COLS):
        x   = GRID_X + c * CELL_W + CELL_W // 2 - 7
        y   = GRID_Y - 8
        cv2.putText(img, col_labels[c], (x, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, BLACK, 1, cv2.LINE_AA)

    # ── Row labels (1–12) to the left of the grid ───────────────────────────
    for r in range(ROWS):
        x = GRID_X - 28
        y = GRID_Y + r * CELL_H + CELL_H // 2 + 6
        cv2.putText(img, str(r + 1), (x, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, BLACK, 1, cv2.LINE_AA)

    # ── Territory labels inside the grid ────────────────────────────────────
    cv2.putText(img, "BLUE (P1)", (GRID_X + 8, GRID_Y + 26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 180), 2, cv2.LINE_AA)
    cv2.putText(img, "RED (P2)", (GRID_X + GRID_W - 120, GRID_Y + GRID_H - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 180), 2, cv2.LINE_AA)

    # ── Diagonal label ───────────────────────────────────────────────────────
    mid_c = GRID_X + 10 * CELL_W + CELL_W // 2
    mid_r = GRID_Y + 1  * CELL_H + CELL_H // 2 + 6
    cv2.putText(img, "/", (mid_c, mid_r),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1, cv2.LINE_AA)

    # ── Corner ArUco markers ─────────────────────────────────────────────────
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)

    corner_positions = {
        0: (MARGIN,                              MARGIN),                               # TL
        1: (GRID_X + GRID_W + MARKER_GAP,        MARGIN),                               # TR
        2: (MARGIN,                              GRID_Y + GRID_H + MARKER_GAP),         # BL
        3: (GRID_X + GRID_W + MARKER_GAP,        GRID_Y + GRID_H + MARKER_GAP),         # BR
    }

    for marker_id, (mx, my) in corner_positions.items():
        marker_img = cv2.aruco.generateImageMarker(aruco_dict, marker_id, MARKER_SIZE)
        marker_bgr = cv2.cvtColor(marker_img, cv2.COLOR_GRAY2BGR)
        img[my:my + MARKER_SIZE, mx:mx + MARKER_SIZE] = marker_bgr

        # Label below each corner marker
        label = f"ID:{marker_id}"
        cv2.putText(img, label, (mx, my + MARKER_SIZE + 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (80, 80, 80), 1, cv2.LINE_AA)

    # ── Turn marker zone (right side) ────────────────────────────────────────
    tz_x = GRID_X + GRID_W + MARKER_SIZE + MARKER_GAP * 2 + 10
    tz_y = GRID_Y + GRID_H // 2 - 120
    tz_w = TURN_ZONE_W - 10
    tz_h = 240

    cv2.rectangle(img, (tz_x, tz_y), (tz_x + tz_w, tz_y + tz_h), LIGHT_GREY, -1)
    cv2.rectangle(img, (tz_x, tz_y), (tz_x + tz_w, tz_y + tz_h), BLACK, 2)

    # Turn marker (ID 20) printed inside the zone
    turn_marker = cv2.aruco.generateImageMarker(aruco_dict, 20, MARKER_SIZE)
    turn_marker_bgr = cv2.cvtColor(turn_marker, cv2.COLOR_GRAY2BGR)
    tm_x = tz_x + (tz_w - MARKER_SIZE) // 2
    tm_y = tz_y + 20
    img[tm_y:tm_y + MARKER_SIZE, tm_x:tm_x + MARKER_SIZE] = turn_marker_bgr

    # Instructions inside the turn zone
    lines = [
        "TURN",
        "MARKER",
        "",
        "ID: 20",
        "",
        "~0 deg",
        "= P1 turn",
        "",
        "~180 deg",
        "= P2 turn",
    ]
    for i, line in enumerate(lines):
        cv2.putText(img, line, (tz_x + 8, tm_y + MARKER_SIZE + 20 + i * 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, BLACK, 1, cv2.LINE_AA)

    # ── Token placement legend (bottom of page) ──────────────────────────────
    legend_y = GRID_Y + GRID_H + MARKER_SIZE + MARKER_GAP + 30
    cv2.putText(img, "Token rotation → direction:", (MARGIN, legend_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, BLACK, 1, cv2.LINE_AA)

    legend_items = [
        "~0 deg  = HORIZONTAL  (Blue: →   Red: ←)",
        "~90 deg = VERTICAL    (Blue: ↓   Red: ↑)",
        "~180 deg= DIAGONAL    (Blue: ↘   Red: ↖)",
    ]
    for i, item in enumerate(legend_items):
        cv2.putText(img, item, (MARGIN, legend_y + 20 + i * 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (60, 60, 60), 1, cv2.LINE_AA)

    return img


if __name__ == "__main__":
    print("Generating board.png ...")
    img = draw_board()
    cv2.imwrite("board.png", img)
    print("Done! Open board.png and print it at 100% scale on A4 paper.")
