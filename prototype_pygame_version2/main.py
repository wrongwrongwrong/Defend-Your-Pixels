"""
PixelWar — entry point
Run with:  python main.py
"""
import pygame

from game.constants import SCREEN_W, SCREEN_H, ROWS, COLS, CELL_SIZE, GAP, MARGIN, GRID_W
from game.state     import init_state
from game.logic     import resolve
from game.input     import (
    cell_click, pick_direction, sel_tok, toggle_nuke,
    done_init_place, start_setup, cont_setup_r, cont_init_r, start_turn,
    undo_turn_plan,
)
from game.renderer  import cell_rect, draw_grid, draw_panel, draw_overlay


def main():
    pygame.init()
    screen  = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("PixelWar")
    clock   = pygame.time.Clock()
    font    = pygame.font.SysFont('monospace', 16, bold=True)
    font_sm = pygame.font.SysFont('monospace', 13)
    font_xs = pygame.font.SysFont('monospace', 11)

    from game.constants import C_BG
    state = init_state()

    while True:
        screen.fill(C_BG)
        draw_grid(screen, state, font_sm, font_xs)
        resolve_btn, undo_btn, nuke_btn, left_btns, right_btns, dir_btns, done_btn = draw_panel(
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
                    if   state.phase == 'intro':      start_setup(state)
                    elif state.phase == 'setup_pass': cont_setup_r(state)
                    elif state.phase == 'init_pass':  cont_init_r(state)
                    elif state.phase == 'pass_turn':  start_turn(state)
                    elif state.phase == 'over':       state = init_state()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my  = event.pos
                p       = state.turn

                if mx < GRID_W:
                    # Grid area — find which cell was clicked
                    for r in range(ROWS):
                        for c in range(COLS):
                            if cell_rect(r, c).collidepoint(mx, my):
                                cell_click(state, r, c)
                else:
                    # Panel area — direction buttons take priority
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
                        elif undo_btn and undo_btn.collidepoint(mx, my):
                            undo_turn_plan(state)
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
