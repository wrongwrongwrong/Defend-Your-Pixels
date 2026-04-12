import pygame
import random
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ROWS, COLS           = 12, 12
CELLS_PER_PLAYER     = 24
CELL_SIZE            = 42
GAP                  = 1
MARGIN               = 14
PANEL_HEIGHT         = 348

HARD_TERRAIN_COUNT   = 5
SOFT_TERRAIN_COUNT   = 6
SOFT_TERRAIN_HP      = 2

SCREEN_W = MARGIN * 2 + COLS * (CELL_SIZE + GAP)
SCREEN_H = MARGIN * 2 + ROWS * (CELL_SIZE + GAP) + PANEL_HEIGHT

COL_LABELS = list('ABCDEFGHIJKL')

# Upgrades — scaled thresholds for 24-cell game
UPGRADES = [
    (3,  't2',   'Splash',    'ATK hits 1 adjacent enemy after primary'),
    (6,  'dt2',  'DEF+',      'DEF also shields 1 adjacent friendly cell'),
    (10, 't3',   'Bonus ATK', 'Extra attack fires from ATK-A each resolve'),
    (15, 'nuke', 'NUKE',      'One-time 3x3 area blast'),
]

# Direction vectors per player
#  'h' = horizontal  'v' = vertical  'd' = diagonal — all pointing toward enemy
DIRS = {
    'b': {'h': (0,  1), 'v': (1,  0), 'd': (1,  1)},
    'r': {'h': (0, -1), 'v': (-1, 0), 'd': (-1,-1)},
}
DIR_ARROW = {
    'b': {'h': '>', 'v': 'v', 'd': 'x'},
    'r': {'h': '<', 'v': '^', 'd': 'x'},
}
DIR_NAME = {'h': 'Horiz', 'v': 'Vert', 'd': 'Diag'}

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
C_BG            = (11,  13,  20)
C_EMPTY         = (20,  25,  40)
C_DIAG          = (28,  31,  48)
C_BLUE          = (26,  58, 122)
C_RED           = (107, 26,  26)
C_SHIELD        = (34, 197,  94)
C_NUKE_TGT      = (249,115,  22)
C_DOT_B_ATK     = (29,  78, 216)
C_DOT_R_ATK     = (153, 27,  27)
C_DOT_B_DEF     = (22, 101,  52)
C_DOT_R_DEF     = (146, 64,  14)
C_SEL           = (251,191,  36)
C_GOLD          = (234,179,   8)
C_WHITE         = (255,255, 255)
C_GREY          = (100,110, 130)
C_DIM           = (40,  45,  60)
C_GREEN         = (34, 197,  94)
C_PANEL         = (15,  18,  30)
C_TERRAIN_HARD  = (62,  68,  88)   # dark slate — indestructible
C_TERRAIN_SOFT  = (126, 86,  36)   # warm brown — breakable

# AoE overlay RGBA values
AOE_PATH        = (220, 210,  60,  30)
AOE_TARGET      = (255,  50,  50,  90)
AOE_BLOCKED     = (255, 140,   0,  70)
AOE_SHIELD      = ( 34, 197,  94,  50)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class Cell:
    own:     Optional[str] = None   # 'b' | 'r' | None
    alive:   bool          = False
    hp:      int           = 1
    shld:    bool          = False
    terrain: Optional[str] = None   # 'hard' | 'soft'


@dataclass
class Token:
    pos: Optional[tuple] = None     # (row, col) or None
    mv:  bool            = False    # moved this turn — no fire
    dir: Optional[str]   = None     # 'h' | 'v' | 'd'  (ATK only)


@dataclass
class GameState:
    g:           list          = field(default_factory=list)
    king:        dict          = field(default_factory=dict)
    tok:         dict          = field(default_factory=dict)
    kills:       dict          = field(default_factory=dict)
    upg:         dict          = field(default_factory=dict)
    nuke_used:   dict          = field(default_factory=dict)
    turn:        str           = 'b'
    round:       int           = 1
    phase:       str           = 'intro'
    sel:         Optional[str] = None
    nuke_mode:   bool          = False
    pending_dir: Optional[str] = None
    new_upg:     dict          = field(default_factory=dict)
    winner:      Optional[str] = None
    log:         list          = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def opp(p):
    return 'r' if p == 'b' else 'b'

def log_event(state, msg, cls='info'):
    state.log.insert(0, {'msg': msg, 'cls': cls})
    if len(state.log) > 40:
        state.log.pop()

def _alpha_blit(surf, rect, rgba):
    s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    s.fill(rgba)
    surf.blit(s, rect.topleft)


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------
def w_sample(items, weights, n):
    pool = list(zip(items, weights))
    result = []
    for _ in range(n):
        total = sum(w for _, w in pool)
        r = random.uniform(0, total)
        cum = 0.0
        for i, (item, w) in enumerate(pool):
            cum += w
            if r <= cum:
                result.append(item)
                pool.pop(i)
                break
    return result


def gen_grid():
    """
    Diagonal split: r+c < 11 = Blue (upper-left)
                    r+c > 11 = Red  (lower-right)
                    r+c == 11 = neutral strip
    24 cells each with strong corner bias.
    Terrain scattered in mid-board area.
    """
    grid = [[Cell() for _ in range(COLS)] for _ in range(ROWS)]

    # Blue — strong bias toward (0,0)
    bc = [(r, c) for r in range(ROWS) for c in range(COLS) if r + c < 11]
    bw = [(12 - r) ** 2 * (12 - c) ** 2 for r, c in bc]
    for r, c in w_sample(bc, bw, CELLS_PER_PLAYER):
        grid[r][c] = Cell(own='b', alive=True, hp=1)

    # Red — strong bias toward (11,11)
    rc = [(r, c) for r in range(ROWS) for c in range(COLS) if r + c > 11]
    rw = [(r + 1) ** 2 * (c + 1) ** 2 for r, c in rc]
    for r, c in w_sample(rc, rw, CELLS_PER_PLAYER):
        grid[r][c] = Cell(own='r', alive=True, hp=1)

    # Terrain — empty non-diagonal cells, weighted toward mid-board
    empty = [
        (r, c) for r in range(ROWS) for c in range(COLS)
        if r + c != 11 and not grid[r][c].alive and grid[r][c].own is None
    ]
    tw = [max(1, 9 - abs(r + c - 11)) for r, c in empty]

    hard_list = w_sample(empty, tw, HARD_TERRAIN_COUNT)
    hard_set  = set(map(tuple, hard_list))
    for r, c in hard_list:
        grid[r][c] = Cell(terrain='hard', alive=True, hp=999)

    remain    = [(r, c) for r, c in empty if (r, c) not in hard_set]
    remain_tw = [max(1, 9 - abs(r + c - 11)) for r, c in remain]
    for r, c in w_sample(remain, remain_tw, SOFT_TERRAIN_COUNT):
        grid[r][c] = Cell(terrain='soft', alive=True, hp=SOFT_TERRAIN_HP)

    return grid


def init_state():
    return GameState(
        g=gen_grid(),
        king={'b': None, 'r': None},
        tok={
            'b': {'a1': Token(), 'a2': Token(), 'df': Token()},
            'r': {'a1': Token(), 'a2': Token(), 'df': Token()},
        },
        kills={'b': 0, 'r': 0},
        upg={'b': set(), 'r': set()},
        nuke_used={'b': False, 'r': False},
        new_upg={'b': set(), 'r': set()},
        turn='b', round=1, phase='intro',
    )


# ---------------------------------------------------------------------------
# Game logic
# ---------------------------------------------------------------------------
def fire_ray(state, r, c, player, direction):
    """
    Cast a ray from (r,c) in the given direction.
    Hard terrain: permanently blocks — returns None.
    Soft terrain: hittable — returns its position.
    Destroyed soft terrain: ray passes through.
    Enemy cell: returns position.
    """
    dr, dc = DIRS[player][direction]
    nr, nc = r + dr, c + dc
    while 0 <= nr < ROWS and 0 <= nc < COLS:
        cell = state.g[nr][nc]
        if cell.terrain == 'hard':
            return None
        if cell.terrain == 'soft' and cell.alive:
            return (nr, nc)
        if cell.terrain == 'soft' and not cell.alive:
            nr += dr; nc += dc; continue     # pass through destroyed soft terrain
        if cell.own == opp(player) and cell.alive:
            return (nr, nc)
        nr += dr
        nc += dc
    return None


def get_ray_cells(state, r, c, player, direction):
    """
    Visualization helper — returns [(row, col, kind)] along a ray.
    Kinds: 'path' | 'target' | 'terrain_hit' | 'blocked'
    """
    dr, dc = DIRS[player][direction]
    nr, nc = r + dr, c + dc
    cells  = []
    while 0 <= nr < ROWS and 0 <= nc < COLS:
        cell = state.g[nr][nc]
        if cell.terrain == 'hard':
            cells.append((nr, nc, 'blocked'))
            break
        if cell.terrain == 'soft' and cell.alive:
            cells.append((nr, nc, 'terrain_hit'))
            break
        if cell.terrain == 'soft' and not cell.alive:
            cells.append((nr, nc, 'path'))
        elif cell.own == opp(player) and cell.alive:
            cells.append((nr, nc, 'target'))
            break
        else:
            cells.append((nr, nc, 'path'))
        nr += dr
        nc += dc
    return cells


def adj_enemy(state, player, r, c):
    return [(r+dr, c+dc)
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]
            if 0 <= r+dr < ROWS and 0 <= c+dc < COLS
            and state.g[r+dr][c+dc].own == opp(player)
            and state.g[r+dr][c+dc].alive]


def adj_own(state, player, r, c):
    return [(r+dr, c+dc)
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]
            if 0 <= r+dr < ROWS and 0 <= c+dc < COLS
            and state.g[r+dr][c+dc].own == player
            and state.g[r+dr][c+dc].alive]


def check_upg(state, player):
    k, u = state.kills[player], state.upg[player]
    for thresh, key, name, _ in UPGRADES:
        if k >= thresh and key not in u:
            u.add(key)
            state.new_upg[player].add(key)
            log_event(state, f"{'Blue' if player=='b' else 'Red'} unlocked {name}!", 'upg')


def hit_cell(state, r, c, attacker, label='ATK'):
    cell  = state.g[r][c]
    coord = f"{COL_LABELS[c]}{r+1}"
    if not cell.alive:
        return False
    if cell.shld:
        log_event(state, f"{label} > {coord} blocked by shield")
        cell.shld = False
        return False
    cell.hp -= 1
    if cell.hp <= 0:
        cell.alive = False
        if cell.terrain:
            log_event(state, f"{label} destroyed terrain at {coord}")
            return True                          # no kill credit for terrain
        state.kills[attacker] += 1
        check_upg(state, attacker)
        if state.king[opp(attacker)] == (r, c):
            log_event(state, f"KING at {coord} destroyed! {'Blue' if attacker=='b' else 'Red'} wins!", 'win')
            return 'king'
        log_event(state, f"{label} destroyed {coord}")
        return True
    if cell.terrain:
        log_event(state, f"{label} hit terrain at {coord} (HP {cell.hp})")
    else:
        log_event(state, f"{label} hit {coord} (HP {cell.hp})")
    return False


def _check_win(state, king_hit):
    o = opp(state.turn)
    enemy_alive = any(
        state.g[r][c].alive
        for r in range(ROWS) for c in range(COLS)
        if state.g[r][c].own == o
    )
    if king_hit or not enemy_alive:
        state.phase  = 'over'
        state.winner = state.turn
        return True
    return False


def resolve(state):
    p        = state.turn
    king_hit = False
    state.new_upg = {'b': set(), 'r': set()}

    # 1 — clear own shields
    for r in range(ROWS):
        for c in range(COLS):
            if state.g[r][c].own == p:
                state.g[r][c].shld = False

    # 2 — defense token shields its cell (and adjacent if dt2)
    df = state.tok[p]['df']
    if df.pos and not df.mv:
        dr, dc = df.pos
        state.g[dr][dc].shld = True
        log_event(state, f"DEF shields {COL_LABELS[dc]}{dr+1}")
        if 'dt2' in state.upg[p]:
            for nr, nc in adj_own(state, p, dr, dc)[:1]:
                state.g[nr][nc].shld = True
                log_event(state, f"DEF+ shields {COL_LABELS[nc]}{nr+1}")

    # 3 — stacked attack (both ATK on same cell)
    a1, a2  = state.tok[p]['a1'], state.tok[p]['a2']
    stacked = (a1.pos and a2.pos and not a1.mv and not a2.mv and a1.pos == a2.pos)

    if stacked:
        target = fire_ray(state, *a1.pos, p, a1.dir or 'h')
        if target:
            res = hit_cell(state, *target, p, 'STACK')
            if res == 'king': king_hit = True
            if not state.g[target[0]][target[1]].terrain:
                for er, ec in adj_enemy(state, p, *target):
                    if hit_cell(state, er, ec, p, 'STACK-AOE') == 'king':
                        king_hit = True
    else:
        for key, tok in [('a1', a1), ('a2', a2)]:
            if not tok.pos:
                continue
            if tok.mv:
                log_event(state, f"{key.upper()} moved — no fire")
                continue
            tr, tc = tok.pos
            if not state.g[tr][tc].alive:
                log_event(state, f"{key.upper()} cell dead — reposition")
                continue
            if not tok.dir:
                log_event(state, f"{key.upper()} has no direction — skip")
                continue
            target = fire_ray(state, tr, tc, p, tok.dir)
            if target:
                res = hit_cell(state, *target, p, key.upper())
                if res == 'king':
                    king_hit = True
                elif res and 't2' in state.upg[p] and not state.g[target[0]][target[1]].terrain:
                    for er, ec in adj_enemy(state, p, *target)[:1]:
                        if hit_cell(state, er, ec, p, 'SPLASH') == 'king':
                            king_hit = True

    # 4 — t3 bonus attack from ATK-A
    if 't3' in state.upg[p] and a1.pos and not a1.mv and a1.dir:
        target = fire_ray(state, *a1.pos, p, a1.dir)
        if target:
            if hit_cell(state, *target, p, 'T3-BONUS') == 'king':
                king_hit = True

    if _check_win(state, king_hit):
        return

    o = opp(p)
    state.turn        = o
    state.round      += 1
    for tok in state.tok[o].values():
        tok.mv = False
    state.sel         = None
    state.nuke_mode   = False
    state.pending_dir = None
    state.phase       = 'pass_turn'


def do_nuke(state, r, c):
    p = state.turn
    for dr in range(-1, 2):
        for dc in range(-1, 2):
            nr, nc = r + dr, c + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS and state.g[nr][nc].own == opp(p):
                hit_cell(state, nr, nc, p, 'NUKE')
    state.nuke_used[p] = True
    state.nuke_mode    = False
    _check_win(state, False)


# ---------------------------------------------------------------------------
# Input handlers
# ---------------------------------------------------------------------------
def _place_token(state, r, c):
    """Shared token placement logic for turn + init phases."""
    p    = state.turn
    cell = state.g[r][c]
    if not state.sel:
        return
    tok = state.tok[p][state.sel]
    if tok.pos == (r, c):
        state.sel = None
        return
    if cell.own != p or not cell.alive:
        return
    if state.sel == 'df':
        for k in ('a1', 'a2'):
            if state.tok[p][k].pos == (r, c):
                log_event(state, "DEF can't share a cell with ATK")
                return
        had      = tok.pos is not None
        tok.pos  = (r, c)
        tok.mv   = had
        state.sel = None
    else:
        had               = tok.pos is not None
        tok.pos           = (r, c)
        tok.mv            = had
        tok.dir           = None
        state.pending_dir = state.sel
        state.sel         = None


def cell_click(state, r, c):
    if state.phase == 'setup_king_b':
        if state.g[r][c].own == 'b' and state.g[r][c].alive:
            state.king['b'] = (r, c)
            state.phase = 'setup_pass'
        return

    if state.phase == 'setup_king_r':
        if state.g[r][c].own == 'r' and state.g[r][c].alive:
            state.king['r'] = (r, c)
            state.phase = 'init_place_b'
            state.turn  = 'b'
        return

    if state.phase in ('turn', 'init_place_b', 'init_place_r'):
        if state.pending_dir:
            return
        if state.nuke_mode:
            if state.g[r][c].own == opp(state.turn) and state.g[r][c].alive:
                do_nuke(state, r, c)
            return
        _place_token(state, r, c)


def pick_direction(state, direction):
    if not state.pending_dir:
        return
    state.tok[state.turn][state.pending_dir].dir = direction
    state.pending_dir = None


def sel_tok(state, key):
    if state.pending_dir:
        return
    state.nuke_mode = False
    state.sel = None if state.sel == key else key


def toggle_nuke(state):
    if state.pending_dir:
        return
    state.sel       = None
    state.nuke_mode = not state.nuke_mode


def done_init_place(state):
    """Player clicks Done during initial setup placement."""
    state.sel         = None
    state.pending_dir = None
    state.nuke_mode   = False
    if state.phase == 'init_place_b':
        state.phase = 'init_pass'          # Blue looks away, Red takes over
    elif state.phase == 'init_place_r':
        state.turn  = 'b'
        state.phase = 'pass_turn'          # Both placed — normal turns begin


def start_setup(state):
    state.phase = 'setup_king_b'

def cont_setup_r(state):
    state.phase = 'setup_king_r'

def cont_init_r(state):
    state.turn  = 'r'
    state.phase = 'init_place_r'

def start_turn(state):
    state.phase       = 'turn'
    state.sel         = None
    state.nuke_mode   = False
    state.pending_dir = None


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
def cell_rect(r, c):
    return pygame.Rect(
        MARGIN + c * (CELL_SIZE + GAP),
        MARGIN + r * (CELL_SIZE + GAP),
        CELL_SIZE, CELL_SIZE
    )


def draw_grid(surf, state, font_sm):
    p = state.turn

    # ── Base cells ──────────────────────────────────────────────────────────
    for r in range(ROWS):
        for c in range(COLS):
            cell = state.g[r][c]
            rect = cell_rect(r, c)

            if r + c == 11:
                pygame.draw.rect(surf, C_DIAG, rect)
                continue

            if cell.terrain == 'hard':
                pygame.draw.rect(surf, C_TERRAIN_HARD, rect)
                pygame.draw.line(surf, (45, 48, 65), rect.topleft,    rect.bottomright, 1)
                pygame.draw.line(surf, (45, 48, 65), rect.topright,   rect.bottomleft,  1)
                continue

            if cell.terrain == 'soft':
                col = C_TERRAIN_SOFT if cell.alive else (75, 52, 22)
                pygame.draw.rect(surf, col, rect)
                if cell.alive:
                    for pip in range(cell.hp):
                        pygame.draw.rect(surf, (195, 145, 75),
                                         (rect.x + 3 + pip * 7, rect.y + 3, 5, 5))
                continue

            if cell.own == 'b':
                _alpha_blit(surf, rect, (*C_BLUE, 255 if cell.alive else 55))
            elif cell.own == 'r':
                _alpha_blit(surf, rect, (*C_RED,  255 if cell.alive else 55))
            else:
                pygame.draw.rect(surf, C_EMPTY, rect)

            if cell.shld:
                pygame.draw.rect(surf, C_SHIELD, rect, 2)
            if state.king.get(cell.own) == (r, c):
                k = font_sm.render('K', True, C_WHITE)
                surf.blit(k, k.get_rect(center=rect.center))
            if state.nuke_mode and cell.own == opp(p) and cell.alive:
                pygame.draw.rect(surf, C_NUKE_TGT, rect, 2)

    # ── AoE overlays ────────────────────────────────────────────────────────
    for pl in ('b', 'r'):
        for key, tok in state.tok[pl].items():
            if not tok.pos:
                continue
            tr, tc = tok.pos
            if key == 'df':
                _alpha_blit(surf, cell_rect(tr, tc), AOE_SHIELD)
                if 'dt2' in state.upg[pl]:
                    for ar, ac in adj_own(state, pl, tr, tc):
                        _alpha_blit(surf, cell_rect(ar, ac), (*AOE_SHIELD[:3], 28))
            elif tok.dir:
                for rr, rc, kind in get_ray_cells(state, tr, tc, pl, tok.dir):
                    rgba = {
                        'target':      AOE_TARGET,
                        'terrain_hit': AOE_BLOCKED,
                        'blocked':     AOE_BLOCKED,
                        'path':        AOE_PATH,
                    }.get(kind, AOE_PATH)
                    _alpha_blit(surf, cell_rect(rr, rc), rgba)

    # ── Token dots + direction arrows ────────────────────────────────────────
    for pl in ('b', 'r'):
        for key, tok in state.tok[pl].items():
            if not tok.pos:
                continue
            tr, tc  = tok.pos
            rect    = cell_rect(tr, tc)
            dot_col = (C_DOT_B_DEF if pl == 'b' else C_DOT_R_DEF) if key == 'df' \
                      else (C_DOT_B_ATK if pl == 'b' else C_DOT_R_ATK)
            alpha   = 85 if tok.mv else 255
            s       = pygame.Surface((10, 10), pygame.SRCALPHA)
            pygame.draw.circle(s, (*dot_col, alpha), (5, 5), 5)
            ox, oy  = {'a1': (-7, -5), 'a2': (4, -5), 'df': (-2, 5)}[key]
            surf.blit(s, (rect.centerx + ox, rect.centery + oy))

            if key != 'df' and tok.dir:
                arrow = font_sm.render(DIR_ARROW[pl][tok.dir], True, dot_col)
                surf.blit(arrow, (rect.centerx + ox - 2, rect.centery + oy - 13))

            if state.sel and state.tok[state.turn].get(state.sel) is tok:
                pygame.draw.rect(surf, C_SEL, rect, 2)
            if state.pending_dir and state.tok[state.turn].get(state.pending_dir) is tok:
                pygame.draw.rect(surf, C_GOLD, rect, 2)

    # ── Upgrade pips on token cells ──────────────────────────────────────────
    for pl in ('b', 'r'):
        active = [k for _, k, _, _ in UPGRADES if k in state.upg[pl] and k != 'nuke']
        for key, tok in state.tok[pl].items():
            if not tok.pos or not active:
                continue
            rect = cell_rect(*tok.pos)
            for i, _ in enumerate(active[:3]):
                pygame.draw.circle(surf, C_GOLD,
                                   (rect.right - 4 - i * 5, rect.bottom - 4), 2)


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------
def _draw_player_col(surf, state, pl, cx, y, col_w, font_xs):
    """
    Draw one player's column: header, 3 token buttons, kill bar, 4 upgrade rows.
    Returns (end_y, list_of_tok_btn_rects).
    """
    p_name  = 'BLUE' if pl == 'b' else 'RED'
    p_col   = C_DOT_B_ATK if pl == 'b' else C_DOT_R_ATK
    active  = state.turn == pl and state.phase in ('turn', 'init_place_b', 'init_place_r')

    # Header
    prefix  = '> ' if active else '  '
    surf.blit(font_xs.render(f"{prefix}{p_name}  {state.kills[pl]} kills", True, p_col),
              (cx, y))
    y += 16

    # Token buttons
    btn_w   = (col_w - 4) // 3
    tok_btns = []
    for i, key in enumerate(['a1', 'a2', 'df']):
        tok    = state.tok[pl][key]
        bx     = cx + i * (btn_w + 2)
        btn    = pygame.Rect(bx, y, btn_w, 26)
        tok_btns.append(btn)
        is_sel = state.sel == key and active
        is_pnd = state.pending_dir == key and active
        border = C_GOLD if is_pnd else (C_SEL if is_sel else C_GREY)
        bg     = (30, 35, 55) if is_sel else (15, 20, 35)
        pygame.draw.rect(surf, bg,     btn)
        pygame.draw.rect(surf, border, btn, 1)
        lbl    = key.upper()
        if tok.mv:
            lbl += ' MV'
        elif tok.pos:
            r2, c2 = tok.pos
            lbl   += f"@{COL_LABELS[c2]}{r2+1}"
            if key != 'df' and tok.dir:
                lbl += DIR_ARROW[pl][tok.dir]
        surf.blit(
            font_xs.render(lbl, True, C_WHITE),
            font_xs.render(lbl, True, C_WHITE).get_rect(center=btn.center)
        )
    y += 30

    # Kill progress bar
    next_t = next((t for t, k, _, _ in UPGRADES if k not in state.upg[pl]), None)
    prev_t = max((t for t, k, _, _ in UPGRADES if k in state.upg[pl]), default=0)
    bar_w  = col_w - 4
    if next_t:
        pct = max(0.0, min(1.0, (state.kills[pl] - prev_t) / max(next_t - prev_t, 1)))
        lbl = f"+{next_t - state.kills[pl]} to next"
    else:
        pct = 1.0
        lbl = "MAX"
    pygame.draw.rect(surf, C_DIM,  (cx, y, bar_w, 5))
    pygame.draw.rect(surf, p_col,  (cx, y, int(bar_w * pct), 5))
    surf.blit(font_xs.render(lbl, True, C_GREY), (cx + bar_w + 4, y - 2))
    y += 14

    # Upgrade rows
    for thresh, key, name, desc in UPGRADES:
        active_upg = key in state.upg[pl]
        is_new     = key in state.new_upg.get(pl, set())
        row        = pygame.Rect(cx, y, col_w - 4, 15)
        pygame.draw.rect(surf, (18, 38, 18) if active_upg else C_PANEL, row)
        name_col   = C_GOLD if is_new else (C_GREEN if active_upg else C_GREY)
        status     = "NEW!" if is_new else ("ON" if active_upg else f"+{thresh - state.kills[pl]}")
        stat_col   = C_GOLD if is_new else (C_GREEN if active_upg else C_GREY)
        surf.blit(font_xs.render(name,   True, name_col), (cx + 2,  y + 1))
        st = font_xs.render(status, True, stat_col)
        surf.blit(st, (cx + col_w - st.get_width() - 6, y + 1))
        y += 16

    return y, tok_btns


def draw_panel(surf, state, font, font_sm, font_xs):
    py = MARGIN * 2 + ROWS * (CELL_SIZE + GAP)
    pw = SCREEN_W
    pygame.draw.rect(surf, C_PANEL, (0, py, pw, PANEL_HEIGHT))

    y = py + 6

    # ── Banner ────────────────────────────────────────────────────────────
    PHASE_LABELS = {
        'intro':        'Welcome to PixelWar',
        'setup_king_b': 'Blue: click a cell to place your King',
        'setup_pass':   'Blue: look away  |  Red: press SPACE',
        'setup_king_r': 'Red: click a cell to place your King',
        'init_place_b': 'SETUP  Blue: place all tokens, then Done',
        'init_pass':    'Blue: look away  |  Red: press SPACE',
        'init_place_r': 'SETUP  Red: place all tokens, then Done',
        'pass_turn':    f"Pass device  |  press SPACE when ready",
        'over':         'GAME OVER',
    }
    if state.phase == 'turn':
        label = f"Round {state.round}  —  {'BLUE' if state.turn=='b' else 'RED'}'s Turn"
    else:
        label = PHASE_LABELS.get(state.phase, state.phase)
    p_col = C_DOT_B_ATK if state.turn == 'b' else C_DOT_R_ATK
    surf.blit(font.render(label, True, p_col), (MARGIN, y))
    y += 26

    # ── Two-column player section ─────────────────────────────────────────
    col_w   = pw // 2 - MARGIN - 4
    left_x  = MARGIN
    right_x = pw // 2 + 4

    left_end,  left_btns  = _draw_player_col(surf, state, 'b', left_x,  y, col_w, font_xs)
    right_end, right_btns = _draw_player_col(surf, state, 'r', right_x, y, col_w, font_xs)
    y = max(left_end, right_end) + 6

    # ── Divider ───────────────────────────────────────────────────────────
    pygame.draw.line(surf, C_DIM, (pw // 2, py + 4), (pw // 2, y - 2), 1)

    # ── Direction picker ──────────────────────────────────────────────────
    dir_btns = []
    if state.pending_dir and state.phase in ('turn', 'init_place_b', 'init_place_r'):
        pl   = state.turn
        surf.blit(
            font_sm.render(f"Pick direction for {state.pending_dir.upper()}:", True, C_GOLD),
            (MARGIN, y)
        )
        y += 18
        for i, d in enumerate(['h', 'v', 'd']):
            bx  = MARGIN + i * 108
            btn = pygame.Rect(bx, y, 100, 24)
            dir_btns.append((btn, d))
            pygame.draw.rect(surf, (35, 30, 10), btn)
            pygame.draw.rect(surf, C_GOLD, btn, 1)
            lbl = f"{DIR_ARROW[pl][d]}  {DIR_NAME[d]}"
            surf.blit(
                font_sm.render(lbl, True, C_GOLD),
                font_sm.render(lbl, True, C_GOLD).get_rect(center=btn.center)
            )
        y += 30

    # ── Action buttons ────────────────────────────────────────────────────
    resolve_rect = None
    nuke_rect    = None
    done_rect    = None
    p            = state.turn

    if state.phase == 'turn':
        can_res      = not state.pending_dir
        resolve_rect = pygame.Rect(MARGIN, y, 100, 24)
        pygame.draw.rect(surf, (35, 70, 35) if can_res else C_DIM, resolve_rect)
        pygame.draw.rect(surf, C_SHIELD if can_res else C_GREY,     resolve_rect, 1)
        surf.blit(
            font_sm.render("Resolve", True, C_WHITE),
            font_sm.render("Resolve", True, C_WHITE).get_rect(center=resolve_rect.center)
        )
        nuke_avail = 'nuke' in state.upg[p] and not state.nuke_used[p]
        nuke_rect  = pygame.Rect(MARGIN + 110, y, 100, 24)
        pygame.draw.rect(surf, (55, 28, 8) if nuke_avail else C_DIM, nuke_rect)
        pygame.draw.rect(surf, C_NUKE_TGT if nuke_avail else C_GREY, nuke_rect, 1)
        surf.blit(
            font_sm.render("NUKE" + (" ON" if state.nuke_mode else ""), True, C_WHITE),
            font_sm.render("NUKE", True, C_WHITE).get_rect(center=nuke_rect.center)
        )

    elif state.phase in ('init_place_b', 'init_place_r'):
        done_rect = pygame.Rect(MARGIN, y, 120, 24)
        pygame.draw.rect(surf, (28, 58, 90), done_rect)
        pygame.draw.rect(surf, (80, 140, 200), done_rect, 1)
        surf.blit(
            font_sm.render("Done Placing", True, C_WHITE),
            font_sm.render("Done Placing", True, C_WHITE).get_rect(center=done_rect.center)
        )

    y += 30

    # ── Event log ─────────────────────────────────────────────────────────
    for i, entry in enumerate(state.log[:3]):
        cls = entry['cls']
        col = C_GOLD if cls == 'upg' else (C_WHITE if cls == 'win' else C_GREY)
        surf.blit(font_xs.render(entry['msg'], True, col), (MARGIN, y + i * 14))
    y += 46

    # ── Legend ────────────────────────────────────────────────────────────
    draw_legend(surf, y, font_xs)

    return resolve_rect, nuke_rect, left_btns, right_btns, dir_btns, done_rect


def draw_legend(surf, y, font_xs):
    """Colour swatch + label for every visual element."""
    items = [
        (C_BLUE,          "Blue cell"),
        (C_RED,           "Red cell"),
        (C_TERRAIN_HARD,  "Hard terrain (indestr.)"),
        (C_TERRAIN_SOFT,  "Soft terrain (2 hits)"),
        (C_SHIELD,        "Shield"),
        (C_NUKE_TGT,      "Nuke target"),
        (C_DIAG,          "Neutral strip"),
    ]
    x = MARGIN
    for color, label in items:
        if x + 100 > SCREEN_W:
            y += 14
            x  = MARGIN
        pygame.draw.rect(surf, color, (x, y + 2, 9, 9))
        pygame.draw.rect(surf, C_GREY, (x, y + 2, 9, 9), 1)
        txt = font_xs.render(label, True, C_GREY)
        surf.blit(txt, (x + 12, y + 2))
        x += txt.get_width() + 22


def draw_overlay(surf, state, font, font_sm):
    ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 215))
    surf.blit(ov, (0, 0))
    cx, cy = SCREEN_W // 2, SCREEN_H // 2

    if state.phase == 'intro':
        lines = ["PIXELWAR", "",
                 "Diagonal board  |  24 cells each  |  Terrain",
                 "Place tokens  >  pick direction  >  resolve",
                 "Destroy all enemy cells or their King", "",
                 "SPACE to start"]
    elif state.phase == 'setup_pass':
        lines = ["Blue placed their King", "", "Blue: look away!", "Red: press SPACE"]
    elif state.phase == 'init_pass':
        lines = ["Blue placed tokens", "", "Blue: look away!",
                 "Red: press SPACE to place your tokens"]
    elif state.phase == 'pass_turn':
        pname = 'BLUE' if state.turn == 'b' else 'RED'
        lines = [f"Pass to {pname}", "", "Press SPACE when ready"]
    elif state.phase == 'over':
        wname = 'BLUE' if state.winner == 'b' else 'RED'
        lines = ["GAME OVER", f"{wname} WINS!", "",
                 f"Blue kills: {state.kills['b']}   Red kills: {state.kills['r']}",
                 f"Rounds: {state.round}", "", "SPACE to restart"]
    else:
        return

    for i, line in enumerate(lines):
        f   = font if i == 0 else font_sm
        col = C_GOLD if (state.phase == 'over' and i == 1) else C_WHITE
        txt = f.render(line, True, col)
        surf.blit(txt, txt.get_rect(center=(cx, cy - 90 + i * 28)))


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def main():
    pygame.init()
    screen  = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("PixelWar")
    clock   = pygame.time.Clock()
    font    = pygame.font.SysFont('monospace', 16, bold=True)
    font_sm = pygame.font.SysFont('monospace', 13)
    font_xs = pygame.font.SysFont('monospace', 11)

    state = init_state()

    while True:
        screen.fill(C_BG)
        draw_grid(screen, state, font_sm)
        resolve_btn, nuke_btn, left_btns, right_btns, dir_btns, done_btn = draw_panel(
            screen, state, font, font_sm, font_xs
        )
        if state.phase in ('intro', 'setup_pass', 'init_pass', 'pass_turn', 'over'):
            draw_overlay(screen, state, font, font_sm)

        pygame.display.flip()
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if state.phase == 'intro':         start_setup(state)
                    elif state.phase == 'setup_pass':  cont_setup_r(state)
                    elif state.phase == 'init_pass':   cont_init_r(state)
                    elif state.phase == 'pass_turn':   start_turn(state)
                    elif state.phase == 'over':        state = init_state()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my  = event.pos
                panel_y = MARGIN * 2 + ROWS * (CELL_SIZE + GAP)
                p       = state.turn

                if my < panel_y:
                    for r in range(ROWS):
                        for c in range(COLS):
                            if cell_rect(r, c).collidepoint(mx, my):
                                cell_click(state, r, c)
                else:
                    # Direction buttons take priority
                    handled = False
                    for btn, d in dir_btns:
                        if btn.collidepoint(mx, my):
                            pick_direction(state, d)
                            handled = True
                            break

                    if not handled:
                        if done_btn and done_btn.collidepoint(mx, my):
                            done_init_place(state)
                        elif resolve_btn and resolve_btn.collidepoint(mx, my) and not state.pending_dir:
                            resolve(state)
                        elif nuke_btn and nuke_btn.collidepoint(mx, my):
                            if 'nuke' in state.upg[p] and not state.nuke_used[p]:
                                toggle_nuke(state)
                        else:
                            active_btns = left_btns if p == 'b' else right_btns
                            for i, btn in enumerate(active_btns):
                                if btn.collidepoint(mx, my):
                                    sel_tok(state, ['a1', 'a2', 'df'][i])


if __name__ == '__main__':
    main()
