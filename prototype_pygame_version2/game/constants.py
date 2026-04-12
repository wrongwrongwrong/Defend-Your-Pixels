# ---------------------------------------------------------------------------
# game/constants.py — all tunable values and colour palette
# ---------------------------------------------------------------------------

# Board
ROWS, COLS           = 12, 12
CELLS_PER_PLAYER     = 24

# Terrain
HARD_TERRAIN_COUNT   = 5
SOFT_TERRAIN_COUNT   = 6
SOFT_TERRAIN_HP      = 2

# Display
CELL_SIZE            = 42
GAP                  = 1
MARGIN               = 14
PANEL_HEIGHT         = 348

SCREEN_W = MARGIN * 2 + COLS * (CELL_SIZE + GAP)
SCREEN_H = MARGIN * 2 + ROWS * (CELL_SIZE + GAP) + PANEL_HEIGHT

COL_LABELS = list('ABCDEFGHIJKL')

# Upgrades: (kill_threshold, key, short_name, description)
UPGRADES = [
    (3,  't2',   'Splash',    'ATK hits 1 adjacent enemy after primary'),
    (6,  'dt2',  'DEF+',      'DEF also shields 1 adjacent friendly cell'),
    (10, 't3',   'Bonus ATK', 'Extra attack fires from ATK-A each resolve'),
    (15, 'nuke', 'NUKE',      'One-time 3x3 area blast'),
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

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
C_BG           = (11,  13,  20)
C_EMPTY        = (20,  25,  40)
C_DIAG         = (28,  31,  48)
C_BLUE         = (26,  58, 122)
C_RED          = (107, 26,  26)
C_SHIELD       = (34, 197,  94)
C_NUKE_TGT     = (249,115,  22)
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
C_TERRAIN_HARD = (62,  68,  88)   # dark slate  — indestructible rock
C_TERRAIN_SOFT = (126, 86,  36)   # warm brown  — breakable obstacle

# AoE overlay RGBA (used with SRCALPHA surfaces)
AOE_PATH       = (220, 210,  60,  30)   # dim yellow  — ray travels here
AOE_TARGET     = (255,  50,  50,  90)   # bright red  — will be hit
AOE_BLOCKED    = (255, 140,   0,  70)   # orange      — ray blocked by terrain
AOE_SHIELD     = ( 34, 197,  94,  50)   # green       — DEF shield area
