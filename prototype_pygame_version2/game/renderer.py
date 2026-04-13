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
    AOE_SHIELD,
)
from .state import GameState, opp
from .logic import get_ray_cells, adj_own, def_shield_cells


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
# Grid axis labels
# ---------------------------------------------------------------------------

def draw_grid_labels(surf: pygame.Surface, font_xs: pygame.font.Font) -> None:
    """
    Draw column letters (A–L) above the grid and row numbers (1–12) to the left.
    """
    label_col = (80, 90, 110)   # muted blue-grey, unobtrusive

    for c in range(COLS):
        rect  = cell_rect(0, c)
        label = COL_LABELS[c]
        txt   = font_xs.render(label, True, label_col)
        # Horizontally centred over each column; vertically centred in top margin
        lx = rect.centerx - txt.get_width() // 2
        ly = (MARGIN - txt.get_height()) // 2
        surf.blit(txt, (lx, ly))

    for r in range(ROWS):
        rect  = cell_rect(r, 0)
        label = str(r + 1)
        txt   = font_xs.render(label, True, label_col)
        # Vertically centred next to each row; right-aligned against the grid edge
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

    # ── Axis labels ─────────────────────────────────────────────────────────
    draw_grid_labels(surf, font_xs)

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

            # Shield highlight (active shield applied during resolve)
            if cell.shld:
                pygame.draw.rect(surf, C_SHIELD, rect, 2)

            # HQ marker
            if state.hq.get(cell.own) == (r, c):
                txt = font_xs.render('HQ', True, C_WHITE)
                surf.blit(txt, txt.get_rect(center=rect.center))

            if state.nuke_mode and cell.own == opp(p) and cell.alive:
                pygame.draw.rect(surf, C_NUKE_TGT, rect, 2)

    # ── DEF token area-of-effect (shield preview) ───────────────────────────
    #  Base DEF  — 3×3 bubble (Chebyshev r=1): token cell + up to 8 neighbours
    #  DEF+ upg  — 5×5 bubble (Chebyshev r=2): adds the 16-cell outer ring
    #
    #  Inner ring cells (r≤1): bright green border 3 px
    #  Outer ring cells (r=2, DEF+ only): dim green border 1 px
    #  Own-alive cells get a "DEF" or "DEF+" chip; empty/other cells just the border.
    C_DEF_INNER = (34, 197, 94)    # bright green  — 3×3 core
    C_DEF_OUTER = (22, 120, 55)    # dim green     — 5×5 outer ring

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
                dist   = max(abs(dr), abs(dc))   # Chebyshev distance
                rect   = cell_rect(nr, nc)
                is_own = state.g[nr][nc].own == pl and state.g[nr][nc].alive

                if dist <= 1:
                    # Inner 3×3 — always shown
                    pygame.draw.rect(surf, C_DEF_INNER, rect, 3 if dist == 0 else 2)
                    if is_own:
                        lbl = font_xs.render('DEF', True, C_DEF_INNER)
                        surf.blit(lbl, (rect.x + 2, rect.y + 2))
                else:
                    # Outer ring (DEF+ only)
                    pygame.draw.rect(surf, C_DEF_OUTER, rect, 1)
                    if is_own:
                        lbl = font_xs.render('DEF+', True, C_DEF_OUTER)
                        surf.blit(lbl, (rect.x + 2, rect.y + 2))

    # ── Attack token ray path labels ─────────────────────────────────────────
    #  Instead of opaque colour fills, each cell on a ray gets a small
    #  "A1>" / "A2^" label and a thin coloured border — one per token.
    #  When two rays share a cell the labels stack so both are visible.
    #
    #  ray_map: {(r,c): [(player, token_key, kind), ...]}
    ray_map: dict = {}
    for pl in ('b', 'r'):
        for key, tok in state.tok[pl].items():
            if key == 'df' or not tok.pos or not tok.dir:
                continue
            tr, tc = tok.pos
            for rr, rc, kind in get_ray_cells(state, tr, tc, pl, tok.dir):
                coord = (rr, rc)
                ray_map.setdefault(coord, []).append((pl, key, kind))

    # Severity order for border colour selection when multiple rays overlap
    _sev = {'target': 3, 'terrain_hit': 2, 'blocked': 2, 'path': 1}

    for (rr, rc), entries in ray_map.items():
        rect = cell_rect(rr, rc)

        # Choose border colour from worst-case kind
        worst = max(entries, key=lambda e: _sev.get(e[2], 0))[2]
        if worst == 'target':
            border_col = (220, 60, 60)     # red — will be hit
        elif worst in ('terrain_hit', 'blocked'):
            border_col = (220, 140, 30)    # orange — blocked
        else:
            border_col = (160, 160, 80)    # dim yellow — passing through

        pygame.draw.rect(surf, border_col, rect, 1)

        # Stack labels bottom-up: first entry at bottom, second above it
        for i, (pl, key, kind) in enumerate(entries[:3]):
            dot_col = C_DOT_B_ATK if pl == 'b' else C_DOT_R_ATK
            arrow   = DIR_ARROW[pl][state.tok[pl][key].dir or 'h']
            lbl     = f"{key.upper()}{arrow}"
            rendered = font_xs.render(lbl, True, dot_col)

            lx = rect.x + 2
            ly = rect.bottom - 12 - i * 13   # stack from bottom upward

            # Dark background chip for readability
            bg = pygame.Rect(lx - 1, ly - 1, rendered.get_width() + 2, rendered.get_height() + 1)
            _alpha_blit(surf, bg, (0, 0, 0, 170))
            surf.blit(rendered, (lx, ly))

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

            # Direction arrow is now embedded in the ray label; skip here to avoid
            # doubling up. Keep it only on the token's own cell for quick reference.
            if key != 'df' and tok.dir:
                arrow = font_xs.render(DIR_ARROW[pl][tok.dir], True, dot_col)
                surf.blit(arrow, (rect.centerx + ox - 2, rect.centery + oy - 12))

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
        'setup_hq_b':   'Blue: click one of your pixels to mark as HQ',
        'setup_pass':   'Blue: look away  |  Red: press SPACE',
        'setup_hq_r':   'Red: click one of your pixels to mark as HQ',
        'init_place_b': 'SETUP — Blue: place all tokens, then Done',
        'init_pass':    'Blue: look away  |  Red: press SPACE',
        'init_place_r': 'SETUP — Red: place all tokens, then Done',
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
        (C_BLUE,              "Blue pixels"),
        (C_RED,               "Red pixels"),
        (C_TERRAIN_HARD,      "Hard terrain (indestr.)"),
        (C_TERRAIN_SOFT,      "Soft terrain (2 hits)"),
        (C_SHIELD,            "Active shield"),
        ((34, 197, 94),       "DEF 3×3 shield area"),
        ((22, 120, 55),       "DEF+ 5×5 outer ring"),
        (C_NUKE_TGT,          "Nuke target"),
        (C_DIAG,              "Neutral strip"),
    ]
    x = MARGIN
    for color, label in items:
        if x + 110 > SCREEN_W:
            y += 14
            x  = MARGIN
        pygame.draw.rect(surf, color, (x, y + 2, 9, 9))
        pygame.draw.rect(surf, C_GREY, (x, y + 2, 9, 9), 1)
        txt = font_xs.render(label, True, C_GREY)
        surf.blit(txt, (x + 12, y + 2))
        x += txt.get_width() + 22


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

    # ------------------------------------------------------------------
    # Intro — full rules card
    # ------------------------------------------------------------------
    if state.phase == 'intro':
        # Each entry: (style, text)
        #   'title'  → big font, gold
        #   'head'   → small font, white
        #   'body'   → small font, grey
        #   'note'   → small font, dim gold
        #   'cta'    → small font, bright white + box
        #   ''       → blank spacer (half line)
        lines = [
            ('title', "P I X E L W A R"),
            ('',      ''),
            ('body',  "Battle on a diagonal pixel grid — 24 pixels each."),
            ('body',  "Destroy ALL enemy pixels, or wipe out their HQ, to win."),
            ('',      ''),
            ('head',  "ATTACK TOKENS  [ A1 / A2 ]"),
            ('body',  "Place anywhere on your half.  Choose a direction:"),
            ('body',  "  H = horizontal   V = vertical   D = diagonal"),
            ('body',  "Ray fires until it hits the first enemy in its path."),
            ('',      ''),
            ('head',  "DEFENSE TOKEN  [ DF ]"),
            ('body',  "Shields a 3×3 bubble of friendly pixels (up to 9 cells)."),
            ('body',  "DEF+ upgrade expands the bubble to 5×5 (up to 25 cells)."),
            ('',      ''),
            ('note',  "Kills unlock:  Splash (3)  ·  DEF+ (6)  ·  Bonus ATK (10)  ·  NUKE (15)"),
            ('',      ''),
            ('body',  "First: each player secretly marks their HQ pixel."),
            ('',      ''),
            ('cta',   "SPACE  to start"),
        ]

        # Measure total height
        LINE_H   = 20   # normal line height
        HALF_H   = 8    # spacer height
        TITLE_H  = 28
        total_h  = sum(TITLE_H if s == 'title' else (HALF_H if s == '' else LINE_H)
                       for s, _ in lines)
        y_start  = cy - total_h // 2

        y_cur = y_start
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
                pygame.draw.rect(surf, C_GREEN,      box, 1, border_radius=4)
                surf.blit(rendered, r)
                y_cur += LINE_H + 10

    # ------------------------------------------------------------------
    # Pass screens
    # ------------------------------------------------------------------
    elif state.phase == 'setup_pass':
        lines = [
            (font,    C_WHITE, "Blue has chosen their HQ"),
            (font_sm, C_GREY,  ""),
            (font_sm, C_WHITE, "Blue: look away from the screen!"),
            (font_sm, C_GREY,  "Red: press  SPACE  when Blue has looked away"),
        ]
        _render_centred_lines(surf, cx, cy, lines)

    elif state.phase == 'init_pass':
        lines = [
            (font,    C_WHITE, "Blue has placed their tokens"),
            (font_sm, C_GREY,  ""),
            (font_sm, C_WHITE, "Blue: look away from the screen!"),
            (font_sm, C_GREY,  "Red: press  SPACE  to place your tokens"),
        ]
        _render_centred_lines(surf, cx, cy, lines)

    elif state.phase == 'pass_turn':
        pname = 'BLUE' if state.turn == 'b' else 'RED'
        pcol  = C_DOT_B_ATK if state.turn == 'b' else C_DOT_R_ATK
        lines = [
            (font,    pcol,    f"Pass to  {pname}"),
            (font_sm, C_GREY,  ""),
            (font_sm, C_WHITE, "Press  SPACE  when ready"),
        ]
        _render_centred_lines(surf, cx, cy, lines)

    elif state.phase == 'over':
        wname = 'BLUE' if state.winner == 'b' else 'RED'
        wcol  = C_DOT_B_ATK if state.winner == 'b' else C_DOT_R_ATK
        lines = [
            (font,    C_WHITE, "GAME OVER"),
            (font,    wcol,    f"{wname}  WINS!"),
            (font_sm, C_GREY,  ""),
            (font_sm, C_GREY,  f"Blue kills: {state.kills['b']}   Red kills: {state.kills['r']}"),
            (font_sm, C_GREY,  f"Rounds played: {state.round}"),
            (font_sm, C_GREY,  ""),
            (font_sm, C_WHITE, "SPACE  to play again"),
        ]
        _render_centred_lines(surf, cx, cy, lines)


def _render_centred_lines(
    surf: pygame.Surface,
    cx: int,
    cy: int,
    lines: list,   # [(font, colour, text), ...]
    line_h: int = 28,
) -> None:
    """Render a list of (font, colour, text) entries centred on (cx, cy)."""
    total = len(lines) * line_h
    y = cy - total // 2
    for f, col, text in lines:
        if text == '':
            y += line_h // 2
            continue
        rendered = f.render(text, True, col)
        surf.blit(rendered, rendered.get_rect(center=(cx, y + line_h // 2)))
        y += line_h
