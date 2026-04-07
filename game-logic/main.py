import pygame
import random
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ROWS, COLS        = 12, 12
CELLS_PER_PLAYER  = 24
CELL_SIZE         = 44
GAP               = 2
MARGIN            = 16
PANEL_HEIGHT      = 334

SCREEN_W = MARGIN * 2 + COLS * (CELL_SIZE + GAP)
SCREEN_H = MARGIN * 2 + ROWS * (CELL_SIZE + GAP) + PANEL_HEIGHT

COL_LABELS = list('ABCDEFGHIJKL')

# Upgrade table  [(kill_threshold, key, short_name, description)]
UPGRADES = [
    (5,  't2',   'Splash',    'ATK also hits one adjacent enemy after primary hit'),
    (10, 'dt2',  'DEF+',      'DEF also shields one adjacent friendly cell'),
    (15, 't3',   'Bonus ATK', 'A second attack fires from ATK-A each resolve'),
    (20, 'nuke', 'NUKE',      'One-time 3×3 area blast — activated manually'),
]

# Direction vectors and labels per player
#   'h' = horizontal (toward opponent)
#   'v' = vertical   (toward opponent)
#   'd' = diagonal   (toward opponent corner)
DIRS = {
    'b': {'h': (0,  1), 'v': (1,  0), 'd': (1,  1)},   # Blue shoots right/down/↘
    'r': {'h': (0, -1), 'v': (-1, 0), 'd': (-1,-1)},   # Red  shoots left/up/↖
}
DIR_ARROW = {
    'b': {'h': '→', 'v': '↓', 'd': '↘'},
    'r': {'h': '←', 'v': '↑', 'd': '↖'},
}
DIR_NAME = {'h': 'Horizontal', 'v': 'Vertical', 'd': 'Diagonal'}

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
C_BG        = (11,  13,  20)
C_EMPTY     = (20,  25,  40)
C_DIAG      = (30,  33,  50)
C_BLUE      = (26,  58, 122)
C_RED       = (107, 26,  26)
C_SHIELD    = (34, 197,  94)
C_NUKE_TGT  = (249,115,  22)
C_DOT_B_ATK = (29,  78, 216)
C_DOT_R_ATK = (153, 27,  27)
C_DOT_B_DEF = (22, 101,  52)
C_DOT_R_DEF = (146, 64,  14)
C_SEL       = (251,191,  36)
C_GOLD      = (234,179,   8)
C_WHITE     = (255,255, 255)
C_GREY      = (100,110, 130)
C_DIM       = (40,  45,  60)
C_GREEN     = (34, 197,  94)
C_PANEL     = (15,  18,  30)
C_PANEL_ALT = (20,  23,  38)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class Cell:
    own:   Optional[str] = None   # 'b', 'r', or None
    alive: bool          = False
    hp:    int           = 1
    shld:  bool          = False


@dataclass
class Token:
    pos: Optional[tuple] = None   # (row, col) or None
    mv:  bool            = False
    dir: Optional[str]   = None   # 'h', 'v', 'd'  — ATK only


@dataclass
class GameState:
    g:           list         = field(default_factory=list)
    king:        dict         = field(default_factory=dict)
    tok:         dict         = field(default_factory=dict)
    kills:       dict         = field(default_factory=dict)
    upg:         dict         = field(default_factory=dict)
    nuke_used:   dict         = field(default_factory=dict)
    turn:        str          = 'b'
    round:       int          = 1
    phase:       str          = 'intro'
    sel:         Optional[str]= None
    nuke_mode:   bool         = False
    pending_dir: Optional[str]= None   # tok key waiting for direction choice
    new_upg:     dict         = field(default_factory=dict)  # newly unlocked this turn
    winner:      Optional[str]= None
    log:         list         = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def opp(p: str) -> str:
    return 'r' if p == 'b' else 'b'


def log_event(state: GameState, msg: str, cls: str = 'info'):
    state.log.insert(0, {'msg': msg, 'cls': cls})
    if len(state.log) > 40:
        state.log.pop()


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------
def w_sample(items, weights, n):
    """Weighted random sample without replacement."""
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
    Diagonal board split: r+c < 11 → Blue territory (upper-left triangle)
                          r+c > 11 → Red  territory (lower-right triangle)
                          r+c == 11 → neutral diagonal strip
    24 cells each, weighted toward their home corner.
    """
    grid = [[Cell() for _ in range(COLS)] for _ in range(ROWS)]

    # Blue: upper-left triangle, weight high near (0,0)
    bc = [(r, c) for r in range(ROWS) for c in range(COLS) if r + c < 11]
    bw = [(12 - r) * (12 - c) for r, c in bc]
    for r, c in w_sample(bc, bw, CELLS_PER_PLAYER):
        grid[r][c] = Cell(own='b', alive=True, hp=1)

    # Red: lower-right triangle, weight high near (11,11)
    rc = [(r, c) for r in range(ROWS) for c in range(COLS) if r + c > 11]
    rw = [(r + 1) * (c + 1) for r, c in rc]
    for r, c in w_sample(rc, rw, CELLS_PER_PLAYER):
        grid[r][c] = Cell(own='r', alive=True, hp=1)

    return grid


def init_state() -> GameState:
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
def fire_ray(state: GameState, r: int, c: int, player: str, direction: str):
    """
    Cast a ray from (r,c) in the given direction.
    Returns (row, col) of first living enemy cell on the ray, or None.
    """
    dr, dc = DIRS[player][direction]
    nr, nc = r + dr, c + dc
    while 0 <= nr < ROWS and 0 <= nc < COLS:
        cell = state.g[nr][nc]
        if cell.own == opp(player) and cell.alive:
            return (nr, nc)
        nr += dr
        nc += dc
    return None


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


def check_upg(state: GameState, player: str):
    k = state.kills[player]
    u = state.upg[player]
    for thresh, key, name, _ in UPGRADES:
        if k >= thresh and key not in u:
            u.add(key)
            state.new_upg[player].add(key)
            log_event(state, f"{'Blue' if player=='b' else 'Red'} unlocked {name}!", 'upg')


def hit_cell(state: GameState, r: int, c: int, attacker: str, label: str = 'ATK'):
    cell  = state.g[r][c]
    coord = f"{COL_LABELS[c]}{r+1}"
    if not cell.alive:
        return False
    if cell.shld:
        log_event(state, f"{label} → {coord} blocked by shield")
        cell.shld = False
        return False
    cell.hp -= 1
    if cell.hp <= 0:
        cell.alive = False
        state.kills[attacker] += 1
        check_upg(state, attacker)
        if state.king[opp(attacker)] == (r, c):
            log_event(state, f"KING at {coord} destroyed — {'Blue' if attacker=='b' else 'Red'} wins!", 'win')
            return 'king'
        log_event(state, f"{label} destroyed {coord}")
        return True
    log_event(state, f"{label} hit {coord} (HP {cell.hp})")
    return False


def _check_win(state: GameState, king_hit: bool):
    """Set phase to 'over' and record winner if win condition met."""
    p, o = state.turn, opp(state.turn)
    enemy_alive = any(
        state.g[r][c].alive
        for r in range(ROWS) for c in range(COLS)
        if state.g[r][c].own == o
    )
    if king_hit or not enemy_alive:
        state.phase  = 'over'
        state.winner = p
        return True
    return False


def resolve(state: GameState):
    p = state.turn
    state.new_upg = {'b': set(), 'r': set()}
    king_hit = False

    # 1 — clear active player's shields from last turn
    for r in range(ROWS):
        for c in range(COLS):
            if state.g[r][c].own == p:
                state.g[r][c].shld = False

    # 2 — defense token
    df = state.tok[p]['df']
    if df.pos and not df.mv:
        dr, dc = df.pos
        state.g[dr][dc].shld = True
        log_event(state, f"DEF shields {COL_LABELS[dc]}{dr+1}")
        if 'dt2' in state.upg[p]:
            neighbors = adj_own(state, p, dr, dc)
            if neighbors:
                nr, nc = neighbors[0]
                state.g[nr][nc].shld = True
                log_event(state, f"DEF+ shields {COL_LABELS[nc]}{nr+1}")

    # 3 — stacked attack (both ATK on same cell, same direction)
    a1, a2 = state.tok[p]['a1'], state.tok[p]['a2']
    stacked = (
        a1.pos and a2.pos
        and not a1.mv and not a2.mv
        and a1.pos == a2.pos
    )

    if stacked:
        direction = a1.dir or 'h'
        target = fire_ray(state, *a1.pos, p, direction)
        if target:
            res = hit_cell(state, *target, p, 'STACK')
            if res == 'king': king_hit = True
            for er, ec in adj_enemy(state, p, *target):
                if hit_cell(state, er, ec, p, 'STACK-AOE') == 'king':
                    king_hit = True
    else:
        # 4 — individual attack tokens
        for key, tok in [('a1', a1), ('a2', a2)]:
            if not tok.pos:
                continue
            if tok.mv:
                log_event(state, f"{key.upper()} moved — no fire this turn")
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
                elif res and 't2' in state.upg[p]:
                    for er, ec in adj_enemy(state, p, *target)[:1]:
                        if hit_cell(state, er, ec, p, 'SPLASH') == 'king':
                            king_hit = True

    # 5 — t3 bonus attack (extra ray from ATK-A)
    if 't3' in state.upg[p] and a1.pos and not a1.mv and a1.dir:
        target = fire_ray(state, *a1.pos, p, a1.dir)
        if target:
            if hit_cell(state, *target, p, 'T3-BONUS') == 'king':
                king_hit = True

    # 6 — win check / turn swap
    if _check_win(state, king_hit):
        return

    o = opp(p)
    state.turn = o
    state.round += 1
    for tok in state.tok[o].values():
        tok.mv = False
    state.sel         = None
    state.nuke_mode   = False
    state.pending_dir = None
    state.phase       = 'pass_turn'


def do_nuke(state: GameState, r: int, c: int):
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
def cell_click(state: GameState, r: int, c: int):
    cell = state.g[r][c]
    p    = state.turn

    if state.phase == 'setup_king_b':
        if cell.own == 'b' and cell.alive:
            state.king['b'] = (r, c)
            state.phase = 'setup_pass'
        return

    if state.phase == 'setup_king_r':
        if cell.own == 'r' and cell.alive:
            state.king['r'] = (r, c)
            state.phase = 'pass_turn'
        return

    if state.phase != 'turn' or state.pending_dir:
        return

    if state.nuke_mode:
        if cell.own == opp(p) and cell.alive:
            do_nuke(state, r, c)
        return

    if not state.sel:
        return

    tok = state.tok[p][state.sel]

    if tok.pos == (r, c):          # click same cell → deselect
        state.sel = None
        return

    if cell.own != p or not cell.alive:
        return

    if state.sel == 'df':
        for k in ('a1', 'a2'):
            if state.tok[p][k].pos == (r, c):
                log_event(state, "DEF can't share a cell with ATK")
                return
        tok.pos = (r, c)
        tok.mv  = tok.pos is not None and tok.pos != (r, c)
        tok.pos = (r, c)
        state.sel = None
    else:
        # ATK token: place then ask for direction
        had_pos  = tok.pos is not None
        tok.pos  = (r, c)
        tok.mv   = had_pos
        tok.dir  = None
        state.pending_dir = state.sel
        state.sel         = None


def pick_direction(state: GameState, direction: str):
    if not state.pending_dir:
        return
    state.tok[state.turn][state.pending_dir].dir = direction
    state.pending_dir = None


def sel_tok(state: GameState, key: str):
    if state.pending_dir:
        return
    state.nuke_mode = False
    state.sel = None if state.sel == key else key


def toggle_nuke(state: GameState):
    if state.pending_dir:
        return
    state.sel       = None
    state.nuke_mode = not state.nuke_mode


def start_setup(state: GameState):
    state.phase = 'setup_king_b'


def cont_setup_r(state: GameState):
    state.phase = 'setup_king_r'


def start_turn(state: GameState):
    state.phase       = 'turn'
    state.sel         = None
    state.nuke_mode   = False
    state.pending_dir = None


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
def cell_rect(r: int, c: int) -> pygame.Rect:
    x = MARGIN + c * (CELL_SIZE + GAP)
    y = MARGIN + r * (CELL_SIZE + GAP)
    return pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)


def draw_grid(surf: pygame.Surface, state: GameState, font_sm: pygame.font.Font):
    p = state.turn

    for r in range(ROWS):
        for c in range(COLS):
            cell = state.g[r][c]
            rect = cell_rect(r, c)
            diag = r + c

            # Neutral diagonal strip
            if diag == 11:
                pygame.draw.rect(surf, C_DIAG, rect)
                continue

            if cell.own == 'b':
                color = C_BLUE
                alpha = 255 if cell.alive else 55
            elif cell.own == 'r':
                color = C_RED
                alpha = 255 if cell.alive else 55
            else:
                color = C_EMPTY
                alpha = 255

            s = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            s.fill((*color, alpha))
            surf.blit(s, rect.topleft)

            if cell.shld:
                pygame.draw.rect(surf, C_SHIELD, rect, 2)

            if state.king.get(cell.own) == (r, c):
                k = font_sm.render('K', True, C_WHITE)
                surf.blit(k, k.get_rect(center=rect.center))

            if state.nuke_mode and cell.own == opp(p) and cell.alive:
                pygame.draw.rect(surf, C_NUKE_TGT, rect, 2)

    # Token dots + direction arrow
    for pl in ('b', 'r'):
        for key, tok in state.tok[pl].items():
            if tok.pos is None:
                continue
            r, c = tok.pos
            rect  = cell_rect(r, c)

            if key == 'df':
                dot_color = C_DOT_B_DEF if pl == 'b' else C_DOT_R_DEF
            else:
                dot_color = C_DOT_B_ATK if pl == 'b' else C_DOT_R_ATK

            alpha = 85 if tok.mv else 255
            s = pygame.Surface((10, 10), pygame.SRCALPHA)
            pygame.draw.circle(s, (*dot_color, alpha), (5, 5), 5)

            offsets = {'a1': (-7, -5), 'a2': (3, -5), 'df': (-2, 5)}
            ox, oy  = offsets[key]
            surf.blit(s, (rect.centerx + ox, rect.centery + oy))

            # Direction arrow on ATK token (small text)
            if key != 'df' and tok.dir:
                arrow = DIR_ARROW[pl][tok.dir]
                a_surf = font_sm.render(arrow, True, (*dot_color, alpha) if alpha < 255 else dot_color)
                surf.blit(a_surf, (rect.centerx + ox - 1, rect.centery + oy - 12))

            # Selection / pending-direction outline
            if state.sel and state.tok[state.turn].get(state.sel) is tok:
                pygame.draw.rect(surf, C_SEL, rect, 2)
            if state.pending_dir and state.tok[state.turn].get(state.pending_dir) is tok:
                pygame.draw.rect(surf, C_GOLD, rect, 2)


def draw_panel(surf, state, font, font_sm, font_xs):
    py = MARGIN * 2 + ROWS * (CELL_SIZE + GAP)
    pw = SCREEN_W
    pygame.draw.rect(surf, C_PANEL, (0, py, pw, PANEL_HEIGHT))

    p      = state.turn
    p_name = 'BLUE' if p == 'b' else 'RED'
    p_col  = C_DOT_B_ATK if p == 'b' else C_DOT_R_ATK

    y = py + 6

    # ── Banner ────────────────────────────────────────────────────────────
    surf.blit(
        font.render(f"Round {state.round}  —  {p_name}'s Turn", True, p_col),
        (MARGIN, y)
    )
    y += 26

    # ── Token buttons ─────────────────────────────────────────────────────
    tok_btns = []
    for i, key in enumerate(['a1', 'a2', 'df']):
        tok  = state.tok[p][key]
        bx   = MARGIN + i * 128
        btn  = pygame.Rect(bx, y, 120, 32)
        tok_btns.append(btn)

        is_sel     = state.sel == key
        is_pending = state.pending_dir == key
        border     = C_GOLD if is_pending else (C_SEL if is_sel else C_GREY)
        bg         = (30, 35, 55) if is_sel else C_PANEL
        pygame.draw.rect(surf, bg, btn)
        pygame.draw.rect(surf, border, btn, 2)

        label = key.upper()
        if tok.mv:
            label += ' MOVED'
        elif tok.pos:
            r2, c2 = tok.pos
            label += f" @{COL_LABELS[c2]}{r2+1}"
            if key != 'df' and tok.dir:
                label += f" {DIR_ARROW[p][tok.dir]}"
        surf.blit(
            font_sm.render(label, True, C_WHITE),
            font_sm.render(label, True, C_WHITE).get_rect(center=btn.center)
        )
    y += 38

    # ── Direction picker (shown only when an ATK token awaits a direction) ─
    dir_btns = []
    if state.pending_dir:
        hint = font_sm.render(
            f"Choose direction for {state.pending_dir.upper()}:", True, C_GOLD
        )
        surf.blit(hint, (MARGIN, y))
        y += 20
        for i, d in enumerate(['h', 'v', 'd']):
            bx  = MARGIN + i * 106
            btn = pygame.Rect(bx, y, 98, 28)
            dir_btns.append((btn, d))
            pygame.draw.rect(surf, (35, 30, 10), btn)
            pygame.draw.rect(surf, C_GOLD, btn, 2)
            lbl = f"{DIR_ARROW[p][d]}  {DIR_NAME[d]}"
            surf.blit(
                font_sm.render(lbl, True, C_GOLD),
                font_sm.render(lbl, True, C_GOLD).get_rect(center=btn.center)
            )
        y += 36
    else:
        y += 0   # space already allocated below via fixed positions

    # ── Action buttons ────────────────────────────────────────────────────
    # Pad y to a fixed row so the upgrade panel never jumps
    action_y = py + 26 + 38 + 64    # fixed offset from panel top

    can_resolve = state.phase == 'turn' and not state.pending_dir
    resolve_rect = pygame.Rect(MARGIN, action_y, 110, 30)
    pygame.draw.rect(surf, (35, 70, 35) if can_resolve else C_DIM, resolve_rect)
    pygame.draw.rect(surf, C_SHIELD if can_resolve else C_GREY, resolve_rect, 2)
    surf.blit(
        font_sm.render("Resolve", True, C_WHITE),
        font_sm.render("Resolve", True, C_WHITE).get_rect(center=resolve_rect.center)
    )

    nuke_avail  = 'nuke' in state.upg[p] and not state.nuke_used[p]
    nuke_rect   = pygame.Rect(MARGIN + 128, action_y, 110, 30)
    pygame.draw.rect(surf, (55, 28, 8) if nuke_avail else C_DIM, nuke_rect)
    pygame.draw.rect(surf, C_NUKE_TGT if nuke_avail else C_GREY, nuke_rect, 2)
    nuke_label  = "NUKE  ON" if state.nuke_mode else "NUKE"
    surf.blit(
        font_sm.render(nuke_label, True, C_WHITE),
        font_sm.render(nuke_label, True, C_WHITE).get_rect(center=nuke_rect.center)
    )

    # ── Upgrade panels (Blue left, Red right) ────────────────────────────
    upg_y  = action_y + 38
    col_w  = pw // 2 - MARGIN

    for pi, pl in enumerate(['b', 'r']):
        cx      = MARGIN + pi * (pw // 2)
        pl_name = 'BLUE' if pl == 'b' else 'RED'
        pl_col  = C_DOT_B_ATK if pl == 'b' else C_DOT_R_ATK
        kills   = state.kills[pl]

        # Find next unlock threshold
        next_thresh = next((t for t, k, _, _ in UPGRADES if k not in state.upg[pl]), None)
        prev_thresh = 0
        for t, k, _, _ in UPGRADES:
            if k in state.upg[pl]:
                prev_thresh = t

        # Kill count line
        if next_thresh:
            need = next_thresh - kills
            kline = f"{pl_name}  {kills} kills  ({need} to next)"
        else:
            kline = f"{pl_name}  {kills} kills  (MAX)"
        surf.blit(font_xs.render(kline, True, pl_col), (cx, upg_y))

        # Progress bar
        bar_y = upg_y + 14
        bar_w = col_w - 4
        if next_thresh:
            pct = (kills - prev_thresh) / max(next_thresh - prev_thresh, 1)
            pct = max(0.0, min(1.0, pct))
        else:
            pct = 1.0
        pygame.draw.rect(surf, C_DIM,   (cx, bar_y, bar_w, 5))
        pygame.draw.rect(surf, pl_col,  (cx, bar_y, int(bar_w * pct), 5))

        # Four upgrade rows
        ry = bar_y + 9
        for thresh, key, name, desc in UPGRADES:
            active  = key in state.upg[pl]
            is_new  = key in state.new_upg.get(pl, set())

            if active:
                row_bg   = (18, 38, 18)
                name_col = C_GOLD if is_new else C_GREEN
                status   = "NEW!" if is_new else "ACTIVE"
                stat_col = C_GOLD if is_new else C_GREEN
            else:
                row_bg   = C_PANEL
                name_col = C_GREY
                remaining = thresh - kills
                status   = f"+{remaining} kills"
                stat_col = C_GREY

            row_rect = pygame.Rect(cx, ry, col_w - 4, 17)
            pygame.draw.rect(surf, row_bg, row_rect)

            surf.blit(font_xs.render(name,   True, name_col), (cx + 2,          ry + 2))
            surf.blit(font_xs.render(desc,   True, C_GREY if not active else (180,200,180)), (cx + 56, ry + 2))
            stat_surf = font_xs.render(status, True, stat_col)
            surf.blit(stat_surf, (cx + col_w - stat_surf.get_width() - 6, ry + 2))
            ry += 18

    # ── Event log ─────────────────────────────────────────────────────────
    log_y = upg_y + 14 + 5 + 9 + 4 * 18 + 4
    for i, entry in enumerate(state.log[:3]):
        cls = entry['cls']
        col = C_GOLD if cls == 'upg' else (C_WHITE if cls == 'win' else C_GREY)
        surf.blit(font_xs.render(entry['msg'], True, col), (MARGIN, log_y + i * 15))

    return resolve_rect, nuke_rect, tok_btns, dir_btns


def draw_overlay(surf, state, font, font_sm):
    ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 210))
    surf.blit(ov, (0, 0))
    cx, cy = SCREEN_W // 2, SCREEN_H // 2

    if state.phase == 'intro':
        lines = [
            "PIXELWAR",
            "",
            "Diagonal board  ·  24 cells each",
            "Place tokens, pick direction, resolve",
            "Destroy all enemy cells or their King",
            "",
            "SPACE to start",
        ]
    elif state.phase == 'setup_pass':
        lines = ["Blue placed their King", "", "Blue: look away!", "Red: press SPACE when ready"]
    elif state.phase == 'pass_turn':
        pname = 'BLUE' if state.turn == 'b' else 'RED'
        lines = [f"Pass to {pname}", "", "Press SPACE when ready"]
    elif state.phase == 'over':
        wname = 'BLUE' if state.winner == 'b' else 'RED'
        lines = [
            "GAME OVER",
            f"{wname} WINS!",
            "",
            f"Blue kills: {state.kills['b']}   Red kills: {state.kills['r']}",
            f"Rounds played: {state.round}",
            "",
            "SPACE to restart",
        ]
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
    font    = pygame.font.SysFont('monospace', 17, bold=True)
    font_sm = pygame.font.SysFont('monospace', 13)
    font_xs = pygame.font.SysFont('monospace', 11)

    state = init_state()

    while True:
        screen.fill(C_BG)
        draw_grid(screen, state, font_sm)
        resolve_btn, nuke_btn, tok_btns, dir_btns = draw_panel(
            screen, state, font, font_sm, font_xs
        )
        if state.phase in ('intro', 'setup_pass', 'pass_turn', 'over'):
            draw_overlay(screen, state, font, font_sm)

        pygame.display.flip()
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if state.phase == 'intro':
                        start_setup(state)
                    elif state.phase == 'setup_pass':
                        cont_setup_r(state)
                    elif state.phase == 'pass_turn':
                        start_turn(state)
                    elif state.phase == 'over':
                        state = init_state()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                panel_y = MARGIN * 2 + ROWS * (CELL_SIZE + GAP)

                if my < panel_y:
                    for r in range(ROWS):
                        for c in range(COLS):
                            if cell_rect(r, c).collidepoint(mx, my):
                                cell_click(state, r, c)
                else:
                    if state.phase == 'turn':
                        # Direction buttons take priority when pending
                        handled = False
                        for btn, d in dir_btns:
                            if btn.collidepoint(mx, my):
                                pick_direction(state, d)
                                handled = True
                                break
                        if not handled:
                            if resolve_btn.collidepoint(mx, my) and not state.pending_dir:
                                resolve(state)
                            elif nuke_btn.collidepoint(mx, my):
                                if 'nuke' in state.upg[state.turn] and not state.nuke_used[state.turn]:
                                    toggle_nuke(state)
                            else:
                                for i, btn in enumerate(tok_btns):
                                    if btn.collidepoint(mx, my):
                                        sel_tok(state, ['a1', 'a2', 'df'][i])


if __name__ == '__main__':
    main()
