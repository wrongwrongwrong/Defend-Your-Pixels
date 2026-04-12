# ---------------------------------------------------------------------------
# game/renderer.py — all Pygame draw routines: grid, panel, overlays
# ---------------------------------------------------------------------------
import pygame

from .constants import (
    ROWS, COLS, CELL_SIZE, GAP, MARGIN, PANEL_HEIGHT,
    SCREEN_W, SCREEN_H, COL_LABELS, UPGRADES,
    DIR_ARROW, DIR_NAME,
    C_BG, C_EMPTY, C_DIAG, C_BLUE, C_RED,
    C_SHIELD, C_NUKE_TGT,
    C_DOT_B_ATK, C_DOT_R_ATK, C_DOT_B_DEF, C_DOT_R_DEF,
    C_SEL, C_GOLD, C_WHITE, C_GREY, C_DIM, C_GREEN, C_PANEL,
    C_TERRAIN_HARD, C_TERRAIN_SOFT,
    AOE_PATH, AOE_TARGET, AOE_BLOCKED, AOE_SHIELD,
)
from .state import GameState, opp
from .logic import get_ray_cells, adj_own


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def cell_rect(r: int, c: int) -> pygame.Rect:
    return pygame.Rect(
        MARGIN + c * (CELL_SIZE + GAP),
        MARGIN + r * (CELL_SIZE + GAP),
        CELL_SIZE, CELL_SIZE,
    )


def _alpha_blit(surf: pygame.Surface, rect: pygame.Rect, rgba: tuple) -> None:
    s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    s.fill(rgba)
    surf.blit(s, rect.topleft)


# ---------------------------------------------------------------------------
# Grid
# ---------------------------------------------------------------------------

def draw_grid(surf: pygame.Surface, state: GameState, font_sm: pygame.font.Font) -> None:
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
                pygame.draw.line(surf, (45, 48, 65), rect.topleft,  rect.bottomright, 1)
                pygame.draw.line(surf, (45, 48, 65), rect.topright, rect.bottomleft,  1)
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
            for i in range(min(len(active), 3)):
                pygame.draw.circle(surf, C_GOLD,
                                   (rect.right - 4 - i * 5, rect.bottom - 4), 2)


# ---------------------------------------------------------------------------
# Panel helpers
# ---------------------------------------------------------------------------

def _draw_player_col(
    surf: pygame.Surface,
    state: GameState,
    pl: str,
    cx: int,
    y: int,
    col_w: int,
    font_xs: pygame.font.Font,
) -> tuple:
    """
    Draw one player column: header, token buttons, kill bar, upgrade rows.
    Returns (end_y, list_of_tok_btn_rects).
    """
    p_name = 'BLUE' if pl == 'b' else 'RED'
    p_col  = C_DOT_B_ATK if pl == 'b' else C_DOT_R_ATK
    active = state.turn == pl and state.phase in ('turn', 'init_place_b', 'init_place_r')

    # Header
    prefix = '> ' if active else '  '
    surf.blit(
        font_xs.render(f"{prefix}{p_name}  {state.kills[pl]} kills", True, p_col),
        (cx, y),
    )
    y += 16

    # Token buttons
    btn_w    = (col_w - 4) // 3
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
        lbl = key.upper()
        if tok.mv:
            lbl += ' MV'
        elif tok.pos:
            r2, c2 = tok.pos
            lbl   += f"@{COL_LABELS[c2]}{r2+1}"
            if key != 'df' and tok.dir:
                lbl += DIR_ARROW[pl][tok.dir]
        rendered = font_xs.render(lbl, True, C_WHITE)
        surf.blit(rendered, rendered.get_rect(center=btn.center))
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
    pygame.draw.rect(surf, C_DIM, (cx, y, bar_w, 5))
    pygame.draw.rect(surf, p_col, (cx, y, int(bar_w * pct), 5))
    surf.blit(font_xs.render(lbl, True, C_GREY), (cx + bar_w + 4, y - 2))
    y += 14

    # Upgrade rows
    for thresh, key, name, _ in UPGRADES:
        active_upg = key in state.upg[pl]
        is_new     = key in state.new_upg.get(pl, set())
        row        = pygame.Rect(cx, y, col_w - 4, 15)
        pygame.draw.rect(surf, (18, 38, 18) if active_upg else C_PANEL, row)
        name_col   = C_GOLD if is_new else (C_GREEN if active_upg else C_GREY)
        status     = "NEW!" if is_new else ("ON" if active_upg else f"+{thresh - state.kills[pl]}")
        stat_col   = C_GOLD if is_new else (C_GREEN if active_upg else C_GREY)
        surf.blit(font_xs.render(name,   True, name_col), (cx + 2, y + 1))
        st = font_xs.render(status, True, stat_col)
        surf.blit(st, (cx + col_w - st.get_width() - 6, y + 1))
        y += 16

    return y, tok_btns


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------

def draw_panel(
    surf: pygame.Surface,
    state: GameState,
    font: pygame.font.Font,
    font_sm: pygame.font.Font,
    font_xs: pygame.font.Font,
) -> tuple:
    """
    Draw the full info panel below the grid.
    Returns (resolve_rect, nuke_rect, left_btns, right_btns, dir_btns, done_rect).
    """
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
        'pass_turn':    'Pass device  |  press SPACE when ready',
        'over':         'GAME OVER',
    }
    if state.phase == 'turn':
        label = f"Round {state.round}  —  {'BLUE' if state.turn=='b' else 'RED'}'s Turn"
    else:
        label = PHASE_LABELS.get(state.phase, state.phase)
    p_col = C_DOT_B_ATK if state.turn == 'b' else C_DOT_R_ATK
    surf.blit(font.render(label, True, p_col), (MARGIN, y))
    y += 26

    # ── Two-column player section ──────────────────────────────────────────
    col_w   = pw // 2 - MARGIN - 4
    left_x  = MARGIN
    right_x = pw // 2 + 4

    left_end,  left_btns  = _draw_player_col(surf, state, 'b', left_x,  y, col_w, font_xs)
    right_end, right_btns = _draw_player_col(surf, state, 'r', right_x, y, col_w, font_xs)
    y = max(left_end, right_end) + 6

    # ── Divider ────────────────────────────────────────────────────────────
    pygame.draw.line(surf, C_DIM, (pw // 2, py + 4), (pw // 2, y - 2), 1)

    # ── Direction picker ────────────────────────────────────────────────────
    dir_btns = []
    if state.pending_dir and state.phase in ('turn', 'init_place_b', 'init_place_r'):
        pl = state.turn
        surf.blit(
            font_sm.render(f"Pick direction for {state.pending_dir.upper()}:", True, C_GOLD),
            (MARGIN, y),
        )
        y += 18
        for i, d in enumerate(['h', 'v', 'd']):
            bx  = MARGIN + i * 108
            btn = pygame.Rect(bx, y, 100, 24)
            dir_btns.append((btn, d))
            pygame.draw.rect(surf, (35, 30, 10), btn)
            pygame.draw.rect(surf, C_GOLD, btn, 1)
            lbl = f"{DIR_ARROW[pl][d]}  {DIR_NAME[d]}"
            rendered = font_sm.render(lbl, True, C_GOLD)
            surf.blit(rendered, rendered.get_rect(center=btn.center))
        y += 30

    # ── Action buttons ──────────────────────────────────────────────────────
    resolve_rect = None
    nuke_rect    = None
    done_rect    = None
    p            = state.turn

    if state.phase == 'turn':
        can_res      = not state.pending_dir
        resolve_rect = pygame.Rect(MARGIN, y, 100, 24)
        pygame.draw.rect(surf, (35, 70, 35) if can_res else C_DIM, resolve_rect)
        pygame.draw.rect(surf, C_SHIELD if can_res else C_GREY,    resolve_rect, 1)
        rendered = font_sm.render("Resolve", True, C_WHITE)
        surf.blit(rendered, rendered.get_rect(center=resolve_rect.center))

        nuke_avail = 'nuke' in state.upg[p] and not state.nuke_used[p]
        nuke_rect  = pygame.Rect(MARGIN + 110, y, 100, 24)
        pygame.draw.rect(surf, (55, 28, 8) if nuke_avail else C_DIM, nuke_rect)
        pygame.draw.rect(surf, C_NUKE_TGT if nuke_avail else C_GREY, nuke_rect, 1)
        nuke_lbl = "NUKE" + (" ON" if state.nuke_mode else "")
        rendered  = font_sm.render(nuke_lbl, True, C_WHITE)
        surf.blit(rendered, rendered.get_rect(center=nuke_rect.center))

    elif state.phase in ('init_place_b', 'init_place_r'):
        done_rect = pygame.Rect(MARGIN, y, 120, 24)
        pygame.draw.rect(surf, (28, 58, 90), done_rect)
        pygame.draw.rect(surf, (80, 140, 200), done_rect, 1)
        rendered = font_sm.render("Done Placing", True, C_WHITE)
        surf.blit(rendered, rendered.get_rect(center=done_rect.center))

    y += 30

    # ── Event log ──────────────────────────────────────────────────────────
    for i, entry in enumerate(state.log[:3]):
        cls = entry['cls']
        col = C_GOLD if cls == 'upg' else (C_WHITE if cls == 'win' else C_GREY)
        surf.blit(font_xs.render(entry['msg'], True, col), (MARGIN, y + i * 14))
    y += 46

    # ── Legend ─────────────────────────────────────────────────────────────
    draw_legend(surf, y, font_xs)

    return resolve_rect, nuke_rect, left_btns, right_btns, dir_btns, done_rect


# ---------------------------------------------------------------------------
# Legend
# ---------------------------------------------------------------------------

def draw_legend(surf: pygame.Surface, y: int, font_xs: pygame.font.Font) -> None:
    items = [
        (C_BLUE,         "Blue cell"),
        (C_RED,          "Red cell"),
        (C_TERRAIN_HARD, "Hard terrain (indestr.)"),
        (C_TERRAIN_SOFT, "Soft terrain (2 hits)"),
        (C_SHIELD,       "Shield"),
        (C_NUKE_TGT,     "Nuke target"),
        (C_DIAG,         "Neutral strip"),
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


# ---------------------------------------------------------------------------
# Full-screen overlay (intro / pass / game-over)
# ---------------------------------------------------------------------------

def draw_overlay(
    surf: pygame.Surface,
    state: GameState,
    font: pygame.font.Font,
    font_sm: pygame.font.Font,
) -> None:
    ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 215))
    surf.blit(ov, (0, 0))
    cx, cy = SCREEN_W // 2, SCREEN_H // 2

    if state.phase == 'intro':
        lines = [
            "PIXELWAR", "",
            "Diagonal board  |  24 cells each  |  Terrain",
            "Place tokens  >  pick direction  >  resolve",
            "Destroy all enemy cells or their King", "",
            "SPACE to start",
        ]
    elif state.phase == 'setup_pass':
        lines = ["Blue placed their King", "", "Blue: look away!", "Red: press SPACE"]
    elif state.phase == 'init_pass':
        lines = [
            "Blue placed tokens", "",
            "Blue: look away!",
            "Red: press SPACE to place your tokens",
        ]
    elif state.phase == 'pass_turn':
        pname = 'BLUE' if state.turn == 'b' else 'RED'
        lines = [f"Pass to {pname}", "", "Press SPACE when ready"]
    elif state.phase == 'over':
        wname = 'BLUE' if state.winner == 'b' else 'RED'
        lines = [
            "GAME OVER", f"{wname} WINS!", "",
            f"Blue kills: {state.kills['b']}   Red kills: {state.kills['r']}",
            f"Rounds: {state.round}", "",
            "SPACE to restart",
        ]
    else:
        return

    for i, line in enumerate(lines):
        f   = font if i == 0 else font_sm
        col = C_GOLD if (state.phase == 'over' and i == 1) else C_WHITE
        txt = f.render(line, True, col)
        surf.blit(txt, txt.get_rect(center=(cx, cy - 90 + i * 28)))
