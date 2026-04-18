# ---------------------------------------------------------------------------
# game/constants.py — all tunable values and colour palette
# ---------------------------------------------------------------------------

# Board
ROWS, COLS           = 12, 12
CELLS_PER_PLAYER     = 24

# Terrain
WALL_COUNT           = 5
BARRICADE_COUNT      = 6
BARRICADE_HP         = 2

# Display
CELL_SIZE            = 42
GAP                  = 1
MARGIN               = 22
SIDE_PANEL_W         = 220
TOP_BAR_H            = 40
BOTTOM_H             = 120

GRID_W = MARGIN * 2 + COLS * (CELL_SIZE + GAP)
GRID_H = MARGIN * 2 + ROWS * (CELL_SIZE + GAP)

GRID_OFFSET_X = SIDE_PANEL_W
GRID_OFFSET_Y = TOP_BAR_H

SCREEN_W = SIDE_PANEL_W * 2 + GRID_W
SCREEN_H = TOP_BAR_H + GRID_H + BOTTOM_H

GAME_TITLE = "Defend Your Pixels"

TEAM_NAMES = {'b': 'Ranger', 'r': 'Emu'}
TEAM_FULL  = {'b': 'The Rangers', 'r': 'The Emus'}

WIN_LINES = {
    'b': [
        "The Rangers held the line!",
        "Not a single emu crossed the fence.",
        "Order restored to the farmlands.",
    ],
    'r': [
        "The Emus have overrun the paddocks!",
        "Feathers fly in victory!",
        "No fence can stop the Great Emu Charge.",
    ],
}

COL_LABELS = list('ABCDEFGHIJKL')

# Upgrades: (kill_threshold, key, short_name, description)
UPGRADES = [
    (3,  't2',   'Splash',    'ATK hits 1 adjacent enemy after primary'),
    (6,  'dt2',  'DEF+',      'DEF also shields 1 adjacent friendly cell'),
    (10, 't3',   'Bonus ATK', 'Extra attack fires from ATK-A each resolve'),
]

# Attack directions per player — all pointing toward the enemy corner
#   'h' = horizontal   'v' = vertical   'd' = diagonal
DIRS = {
    'b': {'h': (0,  1), 'v': (1,  0), 'd': (1,  1)},  # Blue: right / down / down-right
    'r': {'h': (0, -1), 'v': (-1, 0), 'd': (-1,-1)},  # Red:  left / up   / up-left
}
DIR_ARROW = {
    'b': {'h': '>', 'v': 'v', 'd': 'x'},
    'r': {'h': '<', 'v': '^', 'd': 'x'},
}
DIR_NAME = {'h': 'Horiz', 'v': 'Vert', 'd': 'Diag'}

TOKEN_MOVE_RANGE     = 2   # Chebyshev distance — max tiles a token can move per turn

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
C_BG           = (11,  13,  20)
C_EMPTY        = (20,  25,  40)
C_DIAG         = (28,  31,  48)
C_BLUE         = (26,  58, 122)
C_RED          = (107, 26,  26)
C_SHIELD       = (34, 197,  94)
C_DOT_B_ATK    = (29,  78, 216)
C_DOT_R_ATK    = (153, 27,  27)
C_DOT_B_DEF    = (22, 101,  52)
C_DOT_R_DEF    = (146, 64,  14)
C_SEL          = (251,191,  36)
C_GOLD         = (234,179,   8)
C_WHITE        = (255,255, 255)
C_GREY         = (100,110, 130)
C_DIM          = (40,  45,  60)
C_GREEN        = (34, 197,  94)
C_PANEL        = (15,  18,  30)
C_WALL         = (62,  68,  88)   # dark slate  — indestructible wall
C_BARRICADE    = (126, 86,  36)   # warm brown  — breakable barricade

# AoE overlay RGBA (used with SRCALPHA surfaces)
AOE_PATH       = (220, 210,  60,  30)   # dim yellow  — ray travels here
AOE_TARGET     = (255,  50,  50,  90)   # bright red  — will be hit
AOE_BLOCKED    = (255, 140,   0,  70)   # orange      — ray blocked by terrain
AOE_SHIELD     = ( 34, 197,  94,  50)   # green       — DEF shield area
