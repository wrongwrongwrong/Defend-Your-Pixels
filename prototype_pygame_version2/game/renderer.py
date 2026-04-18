# ---------------------------------------------------------------------------
# game/renderer.py — all Pygame draw routines: grid, panels, overlays
# ---------------------------------------------------------------------------
import random

import pygame

from .constants import (
    ROWS, COLS, CELL_SIZE, GAP, MARGIN, SIDE_PANEL_W, TOP_BAR_H, BOTTOM_H,
    SCREEN_W, SCREEN_H, GRID_W, GRID_H, GRID_OFFSET_X, GRID_OFFSET_Y,
    COL_LABELS, UPGRADES, GAME_TITLE, TEAM_NAMES, TEAM_FULL, WIN_LINES,
    DIR_ARROW, DIR_NAME,
    C_BG, C_EMPTY, C_DIAG, C_BLUE, C_RED,
    C_SHIELD,
    C_DOT_B_ATK, C_DOT_R_ATK, C_DOT_B_DEF, C_DOT_R_DEF,
    C_SEL, C_GOLD, C_WHITE, C_GREY, C_DIM, C_GREEN, C_PANEL,
    C_WALL, C_BARRICADE,
)
from .state import GameState, opp
from .logic import fire_ray
from .input import can_done_setup, reachable_cells
from .tutorial import TUT_STEPS, MENU_OPTIONS, tut_current


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def cell_rect(r: int, c: int) -> pygame.Rect:
    return pygame.Rect(
        GRID_OFFSET_X + MARGIN + c * (CELL_SIZE + GAP),
        GRID_OFFSET_Y + MARGIN + r * (CELL_SIZE + GAP),
        CELL_SIZE, CELL_SIZE,
    )


def _alpha_blit(surf: pygame.Surface, rect: pygame.Rect, rgba: tuple) -> None:
    s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    s.fill(rgba)
    surf.blit(s, rect.topleft)


def _team(pl: str) -> str:
    return TEAM_NAMES.get(pl, pl.upper())


def _team_col(pl: str) -> tuple:
    return C_DOT_B_ATK if pl == 'b' else C_DOT_R_ATK


# ---------------------------------------------------------------------------
# Top bar
# ---------------------------------------------------------------------------

_PHASE_LABELS = {
    'intro':      'Welcome',
    'team_pick':  'Choose Your Side',
    'setup_b':    f"{TEAM_NAMES['b']} Setup",
    'setup_pass': f"Pass to {TEAM_NAMES['r']}",
    'setup_r':    f"{TEAM_NAMES['r']} Setup",
    'pass_turn':  'Pass Device',
    'over':       'Game Over',
}


def draw_top_bar(
    surf: pygame.Surface,
    state: GameState,
    font: pygame.font.Font,
    font_sm: pygame.font.Font,
) -> None:
    pygame.draw.rect(surf, C_PANEL, (0, 0, SCREEN_W, TOP_BAR_H))
    pygame.draw.line(surf, C_DIM, (0, TOP_BAR_H - 1), (SCREEN_W, TOP_BAR_H - 1))

    title = font.render(GAME_TITLE, True, C_GOLD)
    surf.blit(title, (14, (TOP_BAR_H - title.get_height()) // 2))

    if state.phase == 'turn':
        pill_text = f"{_team(state.turn).upper()}'S TURN"
        pill_bg_col = _team_col(state.turn)
    else:
        pill_text = _PHASE_LABELS.get(state.phase, state.phase.upper())
        pill_bg_col = C_DIM

    pill = font_sm.render(pill_text, True, C_WHITE)
    pill_rect = pill.get_rect(center=(SCREEN_W // 2, TOP_BAR_H // 2))
    pill_bg = pill_rect.inflate(24, 10)
    pygame.draw.rect(surf, pill_bg_col, pill_bg, border_radius=6)
    surf.blit(pill, pill_rect)

    round_txt = font_sm.render(f"Round {state.round}", True, C_GREY)
    surf.blit(round_txt, (SCREEN_W - round_txt.get_width() - 14,
                          (TOP_BAR_H - round_txt.get_height()) // 2))


# ---------------------------------------------------------------------------
# Grid axis labels
# ---------------------------------------------------------------------------

def draw_grid_labels(surf: pygame.Surface, font_xs: pygame.font.Font) -> None:
    label_col = (80, 90, 110)
    for c in range(COLS):
        rect = cell_rect(0, c)
        txt = font_xs.render(COL_LABELS[c], True, label_col)
        lx = rect.centerx - txt.get_width() // 2
        ly = GRID_OFFSET_Y + (MARGIN - txt.get_height()) // 2
        surf.blit(txt, (lx, ly))

    for r in range(ROWS):
        rect = cell_rect(r, 0)
        txt = font_xs.render(str(r + 1), True, label_col)
        lx = rect.left - txt.get_width() - 3
        ly = rect.centery - txt.get_height() // 2
        surf.blit(txt, (lx, ly))


# ---------------------------------------------------------------------------
# Grid
# ---------------------------------------------------------------------------

def draw_grid(
    surf: pygame.Surface,
    state: GameState,
    font_sm: pygame.font.Font,
    font_xs: pygame.font.Font,
) -> None:
    p = state.turn
    draw_grid_labels(surf, font_xs)

    for r in range(ROWS):
        for c in range(COLS):
            pix = state.pixels[r][c]
            terr = state.terrain[r][c]
            rect = cell_rect(r, c)

            if r + c == 11:
                pygame.draw.rect(surf, C_DIAG, rect)
                continue

            if terr.kind == 'wall':
                pygame.draw.rect(surf, C_WALL, rect)
                pygame.draw.line(surf, (45, 48, 65), rect.topleft, rect.bottomright, 1)
                pygame.draw.line(surf, (45, 48, 65), rect.topright, rect.bottomleft, 1)
            elif terr.kind == 'barricade':
                col = C_BARRICADE if terr.alive else C_EMPTY
                pygame.draw.rect(surf, col, rect)
                if terr.alive:
                    for pip in range(terr.hp):
                        pygame.draw.rect(surf, (195, 145, 75),
                                         (rect.x + 3 + pip * 7, rect.y + 3, 5, 5))
            else:
                pygame.draw.rect(surf, C_EMPTY, rect)

            if pix.own in ('b', 'r'):
                base = C_BLUE if pix.own == 'b' else C_RED
                alpha = 230 if pix.alive else 70
                dot = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                pygame.draw.circle(dot, (*base, alpha),
                                   (rect.w // 2, rect.h // 2), rect.w // 2 - 4)
                surf.blit(dot, rect.topleft)

            if pix.shld:
                pygame.draw.rect(surf, C_SHIELD, rect, 2)

            if state.hq.get(pix.own) == (r, c):
                txt = font_xs.render('HQ', True, C_WHITE)
                surf.blit(txt, txt.get_rect(center=rect.center))

            if state.hq_pending and state.hq_pending[1] == (r, c):
                pygame.draw.rect(surf, C_GOLD, rect, 3)
                q = font_xs.render('?', True, C_GOLD)
                surf.blit(q, q.get_rect(center=(rect.centerx, rect.centery + 10)))

    # Reachable-cell highlight for selected token
    reach = reachable_cells(state)
    if reach:
        for (rr, rc) in reach:
            rect = cell_rect(rr, rc)
            ov = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            pygame.draw.rect(ov, (29, 78, 216, 40), (0, 0, rect.w, rect.h))
            surf.blit(ov, rect.topleft)
            pygame.draw.rect(surf, (29, 78, 216, 120), rect, 1)

    # DEF shield preview — only highlight cells containing friendly alive pixels
    C_DEF_INNER = (34, 197, 94)
    C_DEF_OUTER = (22, 120, 55)
    for pl in ('b', 'r'):
        df = state.tok[pl]['df']
        if not df.pos:
            continue
        tr, tc = df.pos
        radius = 2 if 'dt2' in state.upg[pl] else 1
        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                nr, nc = tr + dr, tc + dc
                if not (0 <= nr < ROWS and 0 <= nc < COLS):
                    continue
                if not (state.pixels[nr][nc].own == pl and state.pixels[nr][nc].alive):
                    continue
                dist = max(abs(dr), abs(dc))
                rect = cell_rect(nr, nc)
                if dist <= 1:
                    pygame.draw.rect(surf, C_DEF_INNER, rect, 2)
                    lbl = font_xs.render('DEF', True, C_DEF_INNER)
                    surf.blit(lbl, (rect.x + 2, rect.y + 2))
                else:
                    pygame.draw.rect(surf, C_DEF_OUTER, rect, 1)
                    lbl = font_xs.render('DEF+', True, C_DEF_OUTER)
                    surf.blit(lbl, (rect.x + 2, rect.y + 2))

    # Attack target markers
    target_map: dict = {}
    for pl in ('b', 'r'):
        for key, tok in state.tok[pl].items():
            if key == 'df' or not tok.pos or not tok.dir:
                continue
            hit = fire_ray(state, tok.pos[0], tok.pos[1], pl, tok.dir)
            if hit:
                target_map.setdefault(hit, []).append((pl, key))

    for (rr, rc), entries in target_map.items():
        rect = cell_rect(rr, rc)
        pygame.draw.rect(surf, (220, 60, 60), rect, 2)
        for i, (pl, key) in enumerate(entries[:3]):
            dot_col = C_DOT_B_ATK if pl == 'b' else C_DOT_R_ATK
            arrow = DIR_ARROW[pl][state.tok[pl][key].dir or 'h']
            lbl = f"{key.upper()}{arrow}"
            rendered = font_xs.render(lbl, True, dot_col)
            lx = rect.x + 2
            ly = rect.bottom - 12 - i * 13
            bg = pygame.Rect(lx - 1, ly - 1, rendered.get_width() + 2, rendered.get_height() + 1)
            _alpha_blit(surf, bg, (0, 0, 0, 170))
            surf.blit(rendered, (lx, ly))

    # Token dots + direction arrows
    for pl in ('b', 'r'):
        for key, tok in state.tok[pl].items():
            if not tok.pos:
                continue
            tr, tc = tok.pos
            rect = cell_rect(tr, tc)
            dot_col = (C_DOT_B_DEF if pl == 'b' else C_DOT_R_DEF) if key == 'df' \
                      else (C_DOT_B_ATK if pl == 'b' else C_DOT_R_ATK)
            alpha = 85 if tok.mv else 255
            s = pygame.Surface((10, 10), pygame.SRCALPHA)
            pygame.draw.circle(s, (*dot_col, alpha), (5, 5), 5)
            ox, oy = {'a1': (-7, -5), 'a2': (4, -5), 'df': (-2, 5)}[key]
            surf.blit(s, (rect.centerx + ox, rect.centery + oy))

            if key != 'df' and tok.dir:
                arrow = font_xs.render(DIR_ARROW[pl][tok.dir], True, dot_col)
                surf.blit(arrow, (rect.centerx + ox - 2, rect.centery + oy - 12))

            if state.sel and state.tok[state.turn].get(state.sel) is tok:
                pygame.draw.rect(surf, C_SEL, rect, 2)
            if state.pending_dir and state.tok[state.turn].get(state.pending_dir) is tok:
                pygame.draw.rect(surf, C_GOLD, rect, 2)

    # Upgrade pips
    for pl in ('b', 'r'):
        active = [k for _, k, _, _ in UPGRADES if k in state.upg[pl]]
        for key, tok in state.tok[pl].items():
            if not tok.pos or not active:
                continue
            rect = cell_rect(*tok.pos)
            for i in range(min(len(active), 3)):
                pygame.draw.circle(surf, C_GOLD,
                                   (rect.right - 4 - i * 5, rect.bottom - 4), 2)


# ---------------------------------------------------------------------------
# Side panel (one per player)
# ---------------------------------------------------------------------------

def _count_alive(state: GameState, pl: str) -> int:
    n = 0
    for r in range(ROWS):
        for c in range(COLS):
            if state.pixels[r][c].own == pl and state.pixels[r][c].alive:
                n += 1
    return n


def draw_side_panel(
    surf: pygame.Surface,
    state: GameState,
    pl: str,
    font_sm: pygame.font.Font,
    font_xs: pygame.font.Font,
) -> list:
    """Draw one player's sidebar. Returns list of token button rects."""
    is_left = (pl == 'b')
    px = 0 if is_left else (SIDE_PANEL_W + GRID_W)
    py = TOP_BAR_H
    pw = SIDE_PANEL_W
    ph = SCREEN_H - TOP_BAR_H

    pygame.draw.rect(surf, C_PANEL, (px, py, pw, ph))
    if is_left:
        pygame.draw.line(surf, C_DIM, (px + pw - 1, py), (px + pw - 1, py + ph))
    else:
        pygame.draw.line(surf, C_DIM, (px, py), (px, py + ph))

    cx = px + 10
    cw = pw - 20
    y = py + 10

    p_name = _team(pl).upper()
    p_col = _team_col(pl)
    active = state.turn == pl and state.phase in ('turn', 'setup_b', 'setup_r')

    # ── Header ────────────────────────────────────────────────────────────
    header = f"{p_name} SIDE"
    surf.blit(font_sm.render(header, True, p_col), (cx, y))
    y += 20

    # ── Kill / alive counters ─────────────────────────────────────────────
    kills_txt = font_sm.render(str(state.kills[pl]), True, C_WHITE)
    surf.blit(font_xs.render("PIXELS", True, C_GREY), (cx, y))
    surf.blit(font_xs.render("DESTROYED", True, C_GREY), (cx, y + 11))
    surf.blit(kills_txt, (cx + cw - kills_txt.get_width(), y + 2))
    y += 28

    alive = _count_alive(state, pl)
    alive_txt = font_sm.render(str(alive), True, C_GREEN)
    surf.blit(font_xs.render("PIXELS", True, C_GREY), (cx, y))
    surf.blit(font_xs.render("ALIVE", True, C_GREY), (cx, y + 11))
    surf.blit(alive_txt, (cx + cw - alive_txt.get_width(), y + 2))
    y += 30

    # ── Tokens ────────────────────────────────────────────────────────────
    surf.blit(font_xs.render("TOKENS", True, C_GREY), (cx, y))
    y += 14

    tok_btns = []
    for key in ['a1', 'a2', 'df']:
        tok = state.tok[pl][key]
        btn = pygame.Rect(cx, y, cw, 24)
        tok_btns.append(btn)

        is_sel = state.sel == key and active
        is_pnd = state.pending_dir == key and active
        border = C_GOLD if is_pnd else (C_SEL if is_sel else C_DIM)
        bg = (30, 35, 55) if is_sel else (15, 20, 35)
        pygame.draw.rect(surf, bg, btn)
        pygame.draw.rect(surf, border, btn, 1)

        kind_col = p_col
        kind_lbl = "ATK" if key != 'df' else "DEF"
        kind_surf = font_xs.render(kind_lbl, True, C_WHITE)
        badge = pygame.Rect(btn.right - kind_surf.get_width() - 12, btn.y + 3,
                            kind_surf.get_width() + 8, 18)
        pygame.draw.rect(surf, kind_col, badge, border_radius=3)
        surf.blit(kind_surf, kind_surf.get_rect(center=badge.center))

        dot_col = (C_DOT_B_DEF if pl == 'b' else C_DOT_R_DEF) if key == 'df' \
                  else (C_DOT_B_ATK if pl == 'b' else C_DOT_R_ATK)
        pygame.draw.circle(surf, dot_col, (btn.x + 10, btn.centery), 4)

        lbl = key.upper()
        if tok.mv:
            lbl += '  MV'
        elif tok.pos:
            r2, c2 = tok.pos
            lbl += f" @{COL_LABELS[c2]}{r2 + 1}"
            if key != 'df' and tok.dir:
                lbl += DIR_ARROW[pl][tok.dir]
        else:
            lbl += '  --'
        rendered = font_xs.render(lbl, True, C_WHITE)
        surf.blit(rendered, (btn.x + 20, btn.centery - rendered.get_height() // 2))
        y += 28

    y += 6

    # ── Upgrades ──────────────────────────────────────────────────────────
    surf.blit(font_xs.render("UPGRADES", True, C_GREY), (cx, y))
    y += 14

    for thresh, key, name, _ in UPGRADES:
        active_upg = key in state.upg[pl]
        is_new = key in state.new_upg.get(pl, set())
        row = pygame.Rect(cx, y, cw, 16)
        pygame.draw.rect(surf, (18, 38, 18) if active_upg else C_PANEL, row)
        name_col = C_GOLD if is_new else (C_GREEN if active_upg else C_GREY)
        surf.blit(font_xs.render(name, True, name_col), (cx + 2, y + 1))
        status = "NEW!" if is_new else ("ON" if active_upg else f"+{thresh - state.kills[pl]}")
        stat_col = C_GOLD if is_new else (C_GREEN if active_upg else C_GREY)
        st = font_xs.render(status, True, stat_col)
        surf.blit(st, (cx + cw - st.get_width() - 2, y + 1))
        y += 18

    y += 6

    # ── Kill progress bar ─────────────────────────────────────────────────
    next_t = next((t for t, k, _, _ in UPGRADES if k not in state.upg[pl]), None)
    prev_t = max((t for t, k, _, _ in UPGRADES if k in state.upg[pl]), default=0)
    bar_w = cw
    if next_t:
        pct = max(0.0, min(1.0, (state.kills[pl] - prev_t) / max(next_t - prev_t, 1)))
        lbl = f"{state.kills[pl]}/{next_t}"
    else:
        pct = 1.0
        lbl = "MAX"
    pygame.draw.rect(surf, C_DIM, (cx, y, bar_w, 6))
    pygame.draw.rect(surf, p_col, (cx, y, int(bar_w * pct), 6))
    y += 8
    surf.blit(font_xs.render(lbl, True, C_GREY), (cx, y))
    y += 16

    # ── HQ status ─────────────────────────────────────────────────────────
    surf.blit(font_xs.render("HQ STATUS", True, C_GREY), (cx, y))
    y += 14
    hq = state.hq.get(pl)
    if hq is not None:
        pygame.draw.circle(surf, p_col, (cx + 5, y + 5), 4)
        hq_label = "Location hidden — alive"
        alive_hq = state.pixels[hq[0]][hq[1]].alive if hq else False
        if not alive_hq and hq is not None:
            hq_label = "DESTROYED"
        surf.blit(font_xs.render(hq_label, True, C_GREY), (cx + 14, y))
    else:
        surf.blit(font_xs.render("Not placed", True, C_GREY), (cx, y))

    return tok_btns


# ---------------------------------------------------------------------------
# Bottom bar (event log + action buttons + direction picker)
# ---------------------------------------------------------------------------

def draw_bottom_bar(
    surf: pygame.Surface,
    state: GameState,
    font_sm: pygame.font.Font,
    font_xs: pygame.font.Font,
) -> tuple:
    """Draw log, direction picker, and action buttons below the grid.
    Returns (resolve_rect, undo_rect, dir_btns, done_rect).
    """
    bx = SIDE_PANEL_W
    by = TOP_BAR_H + GRID_H
    bw = GRID_W
    bh = BOTTOM_H

    pygame.draw.rect(surf, C_PANEL, (bx, by, bw, bh))
    pygame.draw.line(surf, C_DIM, (bx, by), (bx + bw, by))

    left_x = bx + 14
    y = by + 8

    # ── Event log (left side) ─────────────────────────────────────────────
    for i, entry in enumerate(state.log[:4]):
        cls = entry['cls']
        col = C_GOLD if cls == 'upg' else (C_WHITE if cls == 'win' else C_GREY)
        dot_col = C_GOLD if cls == 'upg' else (C_GREEN if cls == 'win' else C_DIM)
        pygame.draw.circle(surf, dot_col, (left_x + 3, y + 6), 3)
        surf.blit(font_xs.render(entry['msg'], True, col), (left_x + 12, y))
        y += 15

    # ── Direction picker + action buttons (right half) ────────────────────
    right_x = bx + bw // 2 + 20
    ry = by + 8
    dir_btns = []
    resolve_rect = None
    undo_rect = None
    done_rect = None
    p = state.turn

    atk_sel = state.phase == 'turn' and state.sel in ('a1', 'a2') \
              and state.tok[state.turn][state.sel].pos is not None
    if atk_sel:
        pl = state.turn
        sel_key = state.sel or ''
        cur_dir = state.tok[pl][sel_key].dir
        dir_label = DIR_NAME.get(cur_dir, '—') if cur_dir else '—'
        surf.blit(font_xs.render(f"Direction for {sel_key.upper()} [{dir_label}]:", True, C_GOLD),
                  (right_x, ry))
        ry += 16
        for i, d in enumerate(['h', 'v', 'd']):
            btn = pygame.Rect(right_x + i * 80, ry, 74, 22)
            dir_btns.append((btn, d))
            is_active = (cur_dir == d)
            bg_col = (60, 50, 10) if is_active else (35, 30, 10)
            border_col = C_WHITE if is_active else C_GOLD
            pygame.draw.rect(surf, bg_col, btn)
            pygame.draw.rect(surf, border_col, btn, 1)
            lbl = f"{DIR_ARROW[pl][d]} {DIR_NAME[d]}"
            rendered = font_xs.render(lbl, True, border_col)
            surf.blit(rendered, rendered.get_rect(center=btn.center))
        ry += 28
        if pl == 'b':
            arrow_hint = "Keys: Right=H  Down=V  hold both=Diag"
        else:
            arrow_hint = "Keys: Left=H  Up=V  hold both=Diag"
        surf.blit(font_xs.render(arrow_hint, True, C_GREY), (right_x, ry))
        ry += 14

    if state.phase == 'turn':
        resolve_rect = pygame.Rect(right_x, ry, 80, 24)
        pygame.draw.rect(surf, (35, 70, 35), resolve_rect)
        pygame.draw.rect(surf, C_SHIELD, resolve_rect, 1)
        surf.blit(font_sm.render("Resolve", True, C_WHITE),
                  font_sm.render("Resolve", True, C_WHITE).get_rect(center=resolve_rect.center))

        can_undo = (state.undo is not None and state.undo.get('turn') == state.turn)
        undo_rect = pygame.Rect(right_x + 88, ry, 72, 24)
        pygame.draw.rect(surf, (60, 60, 90) if can_undo else C_DIM, undo_rect)
        pygame.draw.rect(surf, (160, 160, 220) if can_undo else C_GREY, undo_rect, 1)
        surf.blit(font_sm.render("Undo", True, C_WHITE),
                  font_sm.render("Undo", True, C_WHITE).get_rect(center=undo_rect.center))

        # Spacebar hint
        hint = font_xs.render("SPACE = Resolve + End Turn", True, C_GREY)
        surf.blit(hint, (right_x, ry + 30))

    elif state.phase in ('setup_b', 'setup_r'):
        ready = can_done_setup(state)
        done_rect = pygame.Rect(right_x, ry, 130, 24)
        pygame.draw.rect(surf, (28, 58, 90) if ready else C_DIM, done_rect)
        pygame.draw.rect(surf, (80, 140, 200) if ready else C_GREY, done_rect, 1)
        rendered = font_sm.render("Done (Space)", True, C_WHITE if ready else C_GREY)
        surf.blit(rendered, rendered.get_rect(center=done_rect.center))

    return resolve_rect, undo_rect, dir_btns, done_rect


# ---------------------------------------------------------------------------
# Combined draw_panel (keeps main.py call signature compatible)
# ---------------------------------------------------------------------------

def draw_panel(
    surf: pygame.Surface,
    state: GameState,
    font: pygame.font.Font,
    font_sm: pygame.font.Font,
    font_xs: pygame.font.Font,
) -> tuple:
    """Draw all UI panels. Returns same tuple as before for click handling."""
    draw_top_bar(surf, state, font, font_sm)
    left_btns = draw_side_panel(surf, state, 'b', font_sm, font_xs)
    right_btns = draw_side_panel(surf, state, 'r', font_sm, font_xs)
    resolve_rect, undo_rect, dir_btns, done_rect = draw_bottom_bar(
        surf, state, font_sm, font_xs
    )
    return resolve_rect, undo_rect, left_btns, right_btns, dir_btns, done_rect


# ---------------------------------------------------------------------------
# Full-screen overlay (rules / pass screens / game-over)
# ---------------------------------------------------------------------------

def draw_overlay(
    surf: pygame.Surface,
    state: GameState,
    font: pygame.font.Font,
    font_sm: pygame.font.Font,
) -> None:
    ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 220))
    surf.blit(ov, (0, 0))
    cx, cy = SCREEN_W // 2, SCREEN_H // 2

    if state.phase == 'intro':
        lines = [
            ('title', "E M U   V S   R A N G E R S"),
            ('', ''),
            ('body', "A tabletop pixel battle."),
            ('body', "Place tokens, fire rays, and defend your pixels!"),
            ('', ''),
        ]
        _draw_styled_lines(surf, cx, cy - 60, lines, font, font_sm)
        _draw_menu(surf, cx, cy + 20, state.menu_sel, font_sm)

    elif state.phase == 'team_pick':
        lines = [
            ('title', "C H O O S E   Y O U R   S I D E"),
            ('', ''),
            ('head', f"{TEAM_NAMES['b']}   vs   {TEAM_NAMES['r']}"),
            ('', ''),
            ('body', "Negotiate with your opponent — who plays which side?"),
            ('body', "The Ranger defends the top-left farmlands."),
            ('body', "The Emu horde charges from the bottom-right."),
            ('', ''),
            ('cta', "SPACE  when both players are ready"),
        ]
        _draw_styled_lines(surf, cx, cy, lines, font, font_sm)

    elif state.phase == 'setup_pass':
        t_b = _team('b')
        t_r = _team('r')
        _render_centred_lines(surf, cx, cy, [
            (font, C_WHITE, f"{t_b} has finished setup"),
            (font_sm, C_GREY, ""),
            (font_sm, C_WHITE, f"{t_b}: look away from the screen!"),
            (font_sm, C_GREY, f"{t_r}: press  SPACE  when {t_b} has looked away"),
        ])

    elif state.phase == 'pass_turn':
        pname = _team(state.turn)
        pcol = _team_col(state.turn)
        _render_centred_lines(surf, cx, cy, [
            (font, pcol, f"Pass to  {pname}"),
            (font_sm, C_GREY, ""),
            (font_sm, C_WHITE, "Press  SPACE  when ready"),
        ])

    elif state.phase == 'tut_popup':
        step = tut_current(state)
        if step:
            _draw_tut_popup(surf, cx, cy, step, font, font_sm)

    elif state.phase == 'over':
        w = state.winner or 'b'
        wname = TEAM_FULL.get(w, _team(w))
        wcol = _team_col(w)
        flavour = random.choice(WIN_LINES.get(w, ["Victory!"]))
        _render_centred_lines(surf, cx, cy, [
            (font, C_WHITE, "GAME OVER"),
            (font_sm, C_GREY, ""),
            (font, wcol, f"{wname} win!"),
            (font_sm, wcol, flavour),
            (font_sm, C_GREY, ""),
            (font_sm, C_GREY, f"{_team('b')} kills: {state.kills['b']}   "
                              f"{_team('r')} kills: {state.kills['r']}"),
            (font_sm, C_GREY, f"Rounds played: {state.round}"),
            (font_sm, C_GREY, ""),
            (font_sm, C_WHITE, "SPACE  to play again"),
        ])


def _draw_styled_lines(surf, cx, cy, lines, font, font_sm):
    LINE_H = 20
    HALF_H = 8
    TITLE_H = 28
    total_h = sum(TITLE_H if s == 'title' else (HALF_H if s == '' else LINE_H)
                  for s, _ in lines)
    y_cur = cy - total_h // 2

    for style, text in lines:
        if style == '':
            y_cur += HALF_H
            continue
        if style == 'title':
            rendered = font.render(text, True, C_GOLD)
            surf.blit(rendered, rendered.get_rect(center=(cx, y_cur + TITLE_H // 2)))
            y_cur += TITLE_H
        elif style == 'head':
            rendered = font_sm.render(text, True, C_WHITE)
            surf.blit(rendered, rendered.get_rect(center=(cx, y_cur + LINE_H // 2)))
            y_cur += LINE_H
        elif style == 'body':
            rendered = font_sm.render(text, True, (170, 175, 195))
            surf.blit(rendered, rendered.get_rect(center=(cx, y_cur + LINE_H // 2)))
            y_cur += LINE_H
        elif style == 'note':
            rendered = font_sm.render(text, True, (180, 155, 60))
            surf.blit(rendered, rendered.get_rect(center=(cx, y_cur + LINE_H // 2)))
            y_cur += LINE_H
        elif style == 'cta':
            rendered = font_sm.render(text, True, C_WHITE)
            r = rendered.get_rect(center=(cx, y_cur + LINE_H // 2))
            box = r.inflate(24, 10)
            pygame.draw.rect(surf, (40, 55, 40), box, border_radius=4)
            pygame.draw.rect(surf, C_GREEN, box, 1, border_radius=4)
            surf.blit(rendered, r)
            y_cur += LINE_H + 10


def _render_centred_lines(
    surf: pygame.Surface,
    cx: int,
    cy: int,
    lines: list,
    line_h: int = 28,
) -> None:
    total = len(lines) * line_h
    y = cy - total // 2
    for f, col, text in lines:
        if text == '':
            y += line_h // 2
            continue
        rendered = f.render(text, True, col)
        surf.blit(rendered, rendered.get_rect(center=(cx, y + line_h // 2)))
        y += line_h


# ---------------------------------------------------------------------------
# Main menu options
# ---------------------------------------------------------------------------

def _draw_menu(
    surf: pygame.Surface,
    cx: int,
    y_start: int,
    sel: int,
    font_sm: pygame.font.Font,
) -> None:
    """Draw the main menu options with arrow-key selection highlight."""
    item_h = 32
    for i, label in enumerate(MENU_OPTIONS):
        y = y_start + i * item_h
        rendered = font_sm.render(label, True, C_WHITE)
        r = rendered.get_rect(center=(cx, y + item_h // 2))
        box = r.inflate(40, 12)
        if i == sel:
            pygame.draw.rect(surf, (40, 55, 40), box, border_radius=4)
            pygame.draw.rect(surf, C_GREEN, box, 1, border_radius=4)
        else:
            pygame.draw.rect(surf, (20, 24, 35), box, border_radius=4)
            pygame.draw.rect(surf, C_DIM, box, 1, border_radius=4)
        surf.blit(rendered, r)

    hint = font_sm.render("UP / DOWN  to select  ·  SPACE  to confirm", True, C_GREY)
    surf.blit(hint, hint.get_rect(center=(cx, y_start + len(MENU_OPTIONS) * item_h + 20)))


# ---------------------------------------------------------------------------
# Tutorial popup overlay
# ---------------------------------------------------------------------------

def _draw_tut_popup(
    surf: pygame.Surface,
    cx: int,
    cy: int,
    step: dict,
    font: pygame.font.Font,
    font_sm: pygame.font.Font,
) -> None:
    """Draw a framed popup box for a tutorial step."""
    title = step.get('title', '')
    body_lines = step.get('lines', [])

    line_h = 20
    title_h = 30
    padding = 24
    body_h = sum(line_h if ln else line_h // 2 for ln in body_lines)
    box_h = padding + title_h + 10 + body_h + padding
    box_w = 480

    box = pygame.Rect(cx - box_w // 2, cy - box_h // 2, box_w, box_h)
    pygame.draw.rect(surf, (12, 15, 28), box, border_radius=8)
    pygame.draw.rect(surf, C_GOLD, box, 2, border_radius=8)

    y = box.y + padding
    t = font.render(title, True, C_GOLD)
    surf.blit(t, t.get_rect(center=(cx, y + title_h // 2)))
    y += title_h + 10

    for ln in body_lines:
        if not ln:
            y += line_h // 2
            continue
        if ln.startswith('SPACE'):
            r = font_sm.render(ln, True, C_WHITE)
            rr = r.get_rect(center=(cx, y + line_h // 2))
            cta_box = rr.inflate(24, 8)
            pygame.draw.rect(surf, (40, 55, 40), cta_box, border_radius=4)
            pygame.draw.rect(surf, C_GREEN, cta_box, 1, border_radius=4)
            surf.blit(r, rr)
        else:
            r = font_sm.render(ln, True, (170, 175, 195))
            surf.blit(r, r.get_rect(center=(cx, y + line_h // 2)))
        y += line_h


# ---------------------------------------------------------------------------
# Tutorial play-mode hint bar + target highlight
# ---------------------------------------------------------------------------

def draw_tut_hint(
    surf: pygame.Surface,
    state: GameState,
    font_xs: pygame.font.Font,
) -> None:
    """During tutorial play steps, draw a hint bar and highlight the target cell."""
    step = tut_current(state)
    if not step or step['type'] != 'play':
        return

    hint_text = step.get('hint', '')
    if hint_text:
        bx = SIDE_PANEL_W
        by = TOP_BAR_H + GRID_H + BOTTOM_H - 18
        rendered = font_xs.render(hint_text, True, C_GOLD)
        surf.blit(rendered, (bx + 14, by))

    hl = step.get('highlight')
    if hl:
        rect = cell_rect(hl[0], hl[1])
        pulse = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(pulse, (34, 197, 94, 60), (0, 0, rect.w, rect.h))
        surf.blit(pulse, rect.topleft)
        pygame.draw.rect(surf, C_GREEN, rect, 2)
