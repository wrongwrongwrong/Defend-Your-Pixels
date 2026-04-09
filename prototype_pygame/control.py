"""
4.3-style controller: pygame event loop + keyboard → model calls.
Analogue: SlugDungeon.handle_key_press + redraw loop.
"""

from __future__ import annotations

import pygame

from model_backend.game import Direction, GameState, PlayerId
from model_backend.game.types import Pos

from .levels import build_pvp_level1, build_solo_range_test
from .support_grid import compute_screen_size
from .view import BoardView


_KEY_TO_DIR = {
    pygame.K_w: Direction.UP,
    pygame.K_s: Direction.DOWN,
    pygame.K_a: Direction.LEFT,
    pygame.K_d: Direction.RIGHT,
}


class PVPController:
    def __init__(
        self,
        model: GameState | None = None,
        title: str = "Pixel Defense — Pygame PVP (level1.txt)",
        *,
        single_player: bool = False,
    ) -> None:
        pygame.init()
        self.model: GameState = model or build_pvp_level1()
        self.single_player = single_player
        sw, sh = compute_screen_size(self.model.board.width, self.model.board.height)
        self.screen = pygame.display.set_mode((sw, sh))
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.view = BoardView()
        self._unit_ids: list[str] = []
        self._sel = 0
        self._preview_dest: Pos | None = None
        self._undo_move: tuple[int, int, str, Pos, float, bool] | None = None
        self._any_action_this_turn: bool = False
        self._mode: str = "move"  # "move" or "attack"
        self._confirm_skip: bool = False
        self._refresh_unit_list()
        self._reset_preview()

    def _selected_id(self) -> str | None:
        if not self._unit_ids:
            return None
        return self._unit_ids[self._sel % len(self._unit_ids)]

    def _reset_preview(self) -> None:
        uid = self._selected_id()
        self._preview_dest = self.model.units[uid].pos if uid else None

    def run(self) -> None:
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    running = self._on_key(event.key)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    running = self._on_mouse(event)

            uid = self._selected_id()
            reachable = self.model.reachable_positions(uid) if uid and self._mode == "move" else {}
            attack_tiles: set[Pos] = self.model.valid_action_targets(uid) if uid and self._mode == "attack" else set()
            self.view.draw(
                self.screen,
                self.model,
                selected_unit_id=uid,
                reachable=reachable,
                preview_dest=self._preview_dest,
                mode=self._mode,
                attack_tiles=attack_tiles,
                confirm_skip=self._confirm_skip,
            )
            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()

    def _on_key(self, key: int) -> bool:
        if self.model.game_over:
            return key != pygame.K_ESCAPE

        if self._confirm_skip:
            if key == pygame.K_RETURN or key == pygame.K_KP_ENTER:
                self._confirm_skip = False
                self._end_turn()
            elif key == pygame.K_ESCAPE:
                self._confirm_skip = False
            return True

        if key == pygame.K_ESCAPE:
            return False
        if key == pygame.K_SPACE:
            if not self._any_action_this_turn:
                self._confirm_skip = True
            else:
                self._end_turn()
            return True
        if key == pygame.K_1:
            self._mode = "attack"
            self._reset_preview()
            return True
        if key == pygame.K_2:
            self._mode = "move"
            self._reset_preview()
            return True
        if key == pygame.K_RETURN or key == pygame.K_KP_ENTER:
            uid = self._selected_id()
            if uid:
                u = self.model.units[uid]
                if self._mode == "move" and self._preview_dest is not None:
                    prev = (u.pos, float(u.move_points), bool(u.on_highway))
                    if self.model.move_unit_to(uid, self._preview_dest):
                        # Single-step undo for the last confirmed move this turn.
                        self._undo_move = (
                            int(self.model.turn),
                            int(self.model.active_player),
                            uid,
                            prev[0],
                            prev[1],
                            prev[2],
                        )
                        self._any_action_this_turn = True
                    # Keep selection on the same unit after moving.
                    self._preview_dest = u.pos
                elif self._mode == "attack" and self._preview_dest is not None:
                    if self.model.act_on_target(uid, self._preview_dest):
                        self._any_action_this_turn = True
            return True
        if key == pygame.K_TAB:
            # Undo (last confirmed move this turn).
            if self._undo_move is None:
                return True
            turn, pid, uid, pos, mp, on_hw = self._undo_move
            if turn != int(self.model.turn) or pid != int(self.model.active_player):
                self._undo_move = None
                return True
            u = self.model.units.get(uid)
            if u is None:
                self._undo_move = None
                return True
            u.pos = pos
            u.move_points = mp
            u.on_highway = on_hw
            self._undo_move = None
            self._any_action_this_turn = False
            self._refresh_unit_list()
            self._reset_preview()
            return True
        if key == pygame.K_q:
            self._sel -= 1
            # Selecting a unit defaults to move range preview.
            self._mode = "move"
            self._reset_preview()
            return True
        if key == pygame.K_e:
            self._sel += 1
            # Selecting a unit defaults to move range preview.
            self._mode = "move"
            self._reset_preview()
            return True
        if key == pygame.K_c:
            uid = self._selected_id()
            if uid:
                if self.model.capture(uid):
                    self._any_action_this_turn = True
            return True

        if key in _KEY_TO_DIR:
            uid = self._selected_id()
            if uid:
                u = self.model.units[uid]
                if self._preview_dest is None:
                    self._preview_dest = u.pos
                nxt = self._preview_dest + _KEY_TO_DIR[key].delta()
                if not self.model.board.in_bounds(nxt):
                    return True

                if self._mode == "move":
                    reachable = self.model.reachable_positions(uid)
                    # Only allow previewing a destination the unit can actually reach this turn.
                    if nxt in reachable:
                        self._preview_dest = nxt
                else:
                    attack_tiles = self.model.valid_action_targets(uid)
                    if nxt in attack_tiles:
                        self._preview_dest = nxt
            return True
        return True

    def _on_mouse(self, event: pygame.event.Event) -> bool:
        if not self._confirm_skip:
            return True
        if event.button == 1:
            # Left click: confirm skip.
            self._confirm_skip = False
            self._end_turn()
        elif event.button == 3:
            # Right click: cancel dialog.
            self._confirm_skip = False
        return True

    def _refresh_unit_list(self) -> None:
        ap = self.model.active_player
        self._unit_ids = sorted([uid for uid, u in self.model.units.items() if u.owner == ap])
        self._sel = 0
        # When the active player changes, default back to move mode.
        self._mode = "move"

    def _end_turn(self) -> None:
        self.model.end_turn()
        if self.single_player:
            while self.model.active_player != PlayerId.P1:
                self.model.end_turn()
        self._refresh_unit_list()
        self._reset_preview()
        self._undo_move = None
        self._any_action_this_turn = False
        self._mode = "move"
        self._confirm_skip = False


def main() -> None:
    PVPController().run()


def main_solo_range_test() -> None:
    PVPController(
        model=build_solo_range_test(),
        title="Pixel Defense — Solo Range Test",
        single_player=True,
    ).run()
