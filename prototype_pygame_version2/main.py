"""
PixelWar — entry point
Run with:  python main.py
"""
import sys

import pygame

from game.constants import (
    SCREEN_W, SCREEN_H, ROWS, COLS, CELL_SIZE, GAP, MARGIN,
    GRID_W, SIDE_PANEL_W, TOP_BAR_H, GRID_OFFSET_X, GRID_OFFSET_Y, GRID_H,
)
from game.state     import init_state
from game.logic     import resolve
from game.input     import (
    cell_click, pick_direction, sel_tok,
    start_team_pick, confirm_teams, done_setup, cont_setup_r, start_turn,
    undo_turn_plan,
)
from game.renderer  import cell_rect, draw_grid, draw_panel, draw_overlay, draw_tut_hint
from game.tutorial  import (
    MENU_OPTIONS, init_tutorial_state,
    tut_dismiss_popup, tut_resolve, tut_current,
)


def main():
    pygame.init()
    screen  = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Emu vs Rangers — Defend Your Pixels")
    clock   = pygame.time.Clock()
    font    = pygame.font.SysFont('monospace', 16, bold=True)
    font_sm = pygame.font.SysFont('monospace', 13)
    font_xs = pygame.font.SysFont('monospace', 11)

    from game.constants import C_BG
    state = init_state()

    # Direction preview for arrow-key combo (held keys → committed on release)
    dir_preview = None

    while True:
        screen.fill(C_BG)
        draw_grid(screen, state, font_sm, font_xs)
        resolve_btn, undo_btn, left_btns, right_btns, dir_btns, done_btn = draw_panel(
            screen, state, font, font_sm, font_xs
        )

        if state.tut_step >= 0 and state.phase == 'turn':
            draw_tut_hint(screen, state, font_xs)

        if state.phase in ('intro', 'team_pick', 'setup_pass', 'pass_turn', 'over', 'tut_popup'):
            draw_overlay(screen, state, font, font_sm)

        pygame.display.flip()
        clock.tick(60)

        # ── Arrow-key direction: check held keys each frame ───────────────
        atk_sel = state.phase == 'turn' and state.sel in ('a1', 'a2')
        if atk_sel:
            keys = pygame.key.get_pressed()
            p = state.turn
            if p == 'b':
                has_h, has_v = keys[pygame.K_RIGHT], keys[pygame.K_DOWN]
            else:
                has_h, has_v = keys[pygame.K_LEFT], keys[pygame.K_UP]

            if has_h or has_v:
                if has_h and has_v:
                    dir_preview = 'd'
                elif has_h:
                    dir_preview = 'h'
                else:
                    dir_preview = 'v'
            elif dir_preview is not None:
                pick_direction(state, dir_preview)
                dir_preview = None
        else:
            dir_preview = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

            elif event.type == pygame.KEYDOWN:

                # ── Main menu navigation ──────────────────────────────────
                if state.phase == 'intro':
                    if event.key in (pygame.K_UP, pygame.K_w):
                        state.menu_sel = (state.menu_sel - 1) % len(MENU_OPTIONS)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        state.menu_sel = (state.menu_sel + 1) % len(MENU_OPTIONS)
                    elif event.key == pygame.K_SPACE:
                        if state.menu_sel == 0:
                            start_team_pick(state)
                        elif state.menu_sel == 1:
                            state = init_tutorial_state()
                        elif state.menu_sel == 2:
                            pygame.quit()
                            sys.exit()
                    continue

                # ── Tutorial popup ────────────────────────────────────────
                if state.phase == 'tut_popup':
                    if event.key == pygame.K_SPACE:
                        result = tut_dismiss_popup(state)
                        if result == 'menu':
                            state = init_state()
                    continue

                # ── Token selection via 1 / 2 / 3 ────────────────────────
                if state.phase in ('turn', 'setup_b', 'setup_r'):
                    if event.key in (pygame.K_1, pygame.K_KP_1):
                        sel_tok(state, 'a1')
                        continue
                    elif event.key in (pygame.K_2, pygame.K_KP_2):
                        sel_tok(state, 'a2')
                        continue
                    elif event.key in (pygame.K_3, pygame.K_KP_3):
                        sel_tok(state, 'df')
                        continue

                # ── Arrow keys swallowed when ATK selected ────────────────
                if state.phase == 'turn' and state.sel in ('a1', 'a2') and event.key in (
                    pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
                ):
                    continue

                # ── Space bar (universal confirm) ─────────────────────────
                if event.key == pygame.K_SPACE:
                    if   state.phase == 'team_pick':   confirm_teams(state)
                    elif state.phase == 'setup_b':     done_setup(state)
                    elif state.phase == 'setup_pass':  cont_setup_r(state)
                    elif state.phase == 'setup_r':     done_setup(state)
                    elif state.phase == 'pass_turn':   start_turn(state)
                    elif state.phase == 'turn':
                        if state.tut_step >= 0:
                            tut_resolve(state)
                        else:
                            resolve(state)
                    elif state.phase == 'over':        state = init_state()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                p = state.turn

                if state.phase in ('intro', 'tut_popup'):
                    continue

                grid_left = GRID_OFFSET_X
                grid_right = GRID_OFFSET_X + GRID_W
                grid_top = GRID_OFFSET_Y
                grid_bottom = GRID_OFFSET_Y + GRID_H

                if grid_left <= mx < grid_right and grid_top <= my < grid_bottom:
                    for r in range(ROWS):
                        for c in range(COLS):
                            if cell_rect(r, c).collidepoint(mx, my):
                                cell_click(state, r, c)

                elif my >= grid_bottom:
                    handled = False
                    for btn, d in dir_btns:
                        if btn.collidepoint(mx, my):
                            pick_direction(state, d)
                            handled = True
                            break
                    if not handled:
                        if done_btn and done_btn.collidepoint(mx, my):
                            done_setup(state)
                        elif resolve_btn and resolve_btn.collidepoint(mx, my):
                            if state.tut_step >= 0:
                                tut_resolve(state)
                            else:
                                resolve(state)
                        elif undo_btn and undo_btn.collidepoint(mx, my):
                            undo_turn_plan(state)

                else:
                    active_btns = left_btns if p == 'b' else right_btns
                    for i, btn in enumerate(active_btns):
                        if btn.collidepoint(mx, my):
                            sel_tok(state, ['a1', 'a2', 'df'][i])


if __name__ == '__main__':
    main()
