"""
4.2-style view. Cells show the same symbols as the level file:
  # wall   E drill   H HQ   A / D attacker & defender (P1 uppercase, P2 tinted).
"""

from __future__ import annotations

import pygame

from model_backend.game import GameState
from model_backend.game.entities import UnitKind
from model_backend.game.types import PlayerId, Pos, TerrainType

from .support_grid import (
    CELL,
    COLOUR_BG,
    COLOUR_BLOCKED,
    COLOUR_DRILL,
    COLOUR_GRID,
    COLOUR_HIGHWAY,
    COLOUR_HUD_BG,
    COLOUR_P1,
    COLOUR_P2,
    COLOUR_PLAIN,
    COLOUR_TEXT,
    COLOUR_TOWER_P1,
    COLOUR_TOWER_P2,
    cell_rect_px,
    compute_screen_size,
)

_COLOUR_REACHABLE = (40, 190, 120)
_COLOUR_PREVIEW = (255, 240, 120)
_COLOUR_SELECTED_OUTLINE = (255, 240, 120)
_COLOUR_ATTACK = (220, 80, 80)
_COLOUR_ATTACK_PREVIEW = (255, 120, 120)


class BoardView:
    def __init__(self) -> None:
        pygame.font.init()
        self._font = pygame.font.SysFont("Menlo", 22, bold=True)
        self._font_small = pygame.font.SysFont("Menlo", 13)

    def draw(
        self,
        surf: pygame.Surface,
        game: GameState,
        selected_unit_id: str | None,
        *,
        reachable: dict[Pos, float] | None = None,
        preview_dest: Pos | None = None,
        mode: str = "move",
        attack_tiles: set[Pos] | None = None,
        confirm_skip: bool = False,
    ) -> None:
        surf.fill(COLOUR_BG)
        ox, oy = 8, 8
        gw, gh = game.board.width, game.board.height
        reachable = reachable or {}
        attack_tiles = attack_tiles or set()

        overlay = pygame.Surface((gw * CELL, gh * CELL), pygame.SRCALPHA)
        if mode == "move":
            for p, cost in reachable.items():
                if cost <= 0:
                    continue
                rect = pygame.Rect(cell_rect_px(p.x, p.y))
                # Slightly stronger alpha near the unit, lighter further away.
                alpha = 80 if cost <= 1.0 else 55 if cost <= 1.5 else 40
                overlay.fill((*_COLOUR_REACHABLE, alpha), rect)
        elif mode == "attack":
            for p in attack_tiles:
                rect = pygame.Rect(cell_rect_px(p.x, p.y))
                overlay.fill((*_COLOUR_ATTACK, 70), rect)

        for y in range(gh):
            for x in range(gw):
                rect = pygame.Rect(cell_rect_px(x, y)).move(ox, oy)
                pos = Pos(x, y)
                tile = game.board.get(pos)
                t = tile.terrain

                if t == TerrainType.BLOCKED:
                    bg = COLOUR_BLOCKED
                elif t == TerrainType.ETHER_DRILL:
                    drill = game.drills.get(pos)
                    if drill is not None and drill.owner is not None:
                        team = COLOUR_P1 if drill.owner == PlayerId.P1 else COLOUR_P2
                        # Mix base drill green with team colour.
                        bg = (
                            int(COLOUR_DRILL[0] * 0.45 + team[0] * 0.55),
                            int(COLOUR_DRILL[1] * 0.45 + team[1] * 0.55),
                            int(COLOUR_DRILL[2] * 0.45 + team[2] * 0.55),
                        )
                    else:
                        bg = COLOUR_DRILL
                elif t == TerrainType.HIGHWAY:
                    bg = COLOUR_HIGHWAY
                else:
                    bg = COLOUR_PLAIN

                pygame.draw.rect(surf, bg, rect)
                pygame.draw.rect(surf, COLOUR_GRID, rect, 1)

                glyph, fg = self._glyph_and_color(game, pos, selected_unit_id)
                if glyph:
                    surf.blit(
                        self._font.render(glyph, True, fg),
                        (rect.x + CELL // 2 - 7, rect.y + CELL // 2 - 12),
                    )

        surf.blit(overlay, (ox, oy))

        # Strong selection outline around the selected unit.
        if selected_unit_id and selected_unit_id in game.units:
            upos = game.units[selected_unit_id].pos
            srect = pygame.Rect(cell_rect_px(upos.x, upos.y)).move(ox, oy)
            pygame.draw.rect(surf, _COLOUR_SELECTED_OUTLINE, srect, 4, border_radius=6)

        # Preview destination outline (Enter to confirm move / pick attack tile).
        if mode == "move" and preview_dest is not None and preview_dest in reachable:
            prect = pygame.Rect(cell_rect_px(preview_dest.x, preview_dest.y)).move(ox, oy)
            pygame.draw.rect(surf, _COLOUR_PREVIEW, prect, 3, border_radius=6)
        if mode == "attack" and preview_dest is not None and preview_dest in attack_tiles:
            prect = pygame.Rect(cell_rect_px(preview_dest.x, preview_dest.y)).move(ox, oy)
            pygame.draw.rect(surf, _COLOUR_ATTACK_PREVIEW, prect, 3, border_radius=6)

        self._draw_hud(surf, game, ox, oy, gw, gh)
        if confirm_skip:
            self._draw_skip_dialog(surf, game, ox, oy, gw, gh)

    def _glyph_and_color(
        self, game: GameState, pos: Pos, selected_unit_id: str | None
    ) -> tuple[str, tuple[int, int, int]]:
        u = game.unit_at(pos)
        if u:
            g = "A" if u.kind == UnitKind.ATTACKER else "D"
            col = COLOUR_P1 if u.owner == PlayerId.P1 else COLOUR_P2
            if u.id == selected_unit_id:
                col = (min(255, col[0] + 40), min(255, col[1] + 40), col[2])
            return g, col

        for pid, tower in game.towers.items():
            if tower.pos == pos:
                # HQ tinted by team colour (not neutral gold).
                col = COLOUR_P1 if pid == PlayerId.P1 else COLOUR_P2
                return "H", col

        pix = game.pixel_at(pos)
        if pix is not None:
            col = COLOUR_P1 if pix.owner == PlayerId.P1 else COLOUR_P2
            if pix.guarded_turns > 0:
                col = (min(255, col[0] + 60), min(255, col[1] + 50), 120)
            return "*", col

        t = game.board.get(pos).terrain
        if t == TerrainType.BLOCKED:
            return "#", COLOUR_TEXT
        if t == TerrainType.ETHER_DRILL:
            drill = game.drills.get(pos)
            if drill is not None and drill.owner is not None:
                col = COLOUR_P1 if drill.owner == PlayerId.P1 else COLOUR_P2
                return "E", col
            return "E", (180, 255, 160)

        return ".", (80, 90, 110)

    def _draw_hud(
        self, surf: pygame.Surface, game: GameState, ox: int, oy: int, gw: int, gh: int
    ) -> None:
        hx = gw * CELL + ox + 12
        _, screen_h = compute_screen_size(gw, gh)
        pygame.draw.rect(surf, COLOUR_HUD_BG, (hx - 4, 0, 300, screen_h))

        y = 12
        p1 = game.players[PlayerId.P1]
        p2 = game.players[PlayerId.P2]
        k1 = game.pixels_destroyed_by[PlayerId.P1]
        k2 = game.pixels_destroyed_by[PlayerId.P2]
        rem1 = sum(1 for px in game.pixels.values() if px.owner == PlayerId.P1)
        rem2 = sum(1 for px in game.pixels.values() if px.owner == PlayerId.P2)
        win_n = game.PIXELS_DESTROYED_TO_WIN
        lines = [
            "Map: prototype scenario",
            "# wall   * pixel (bright = guarded)   H HQ",
            "A/D by colour: P1 blue, P2 red",
            "",
            f"Turn {game.turn}  |  Active P{int(game.active_player)}",
            "",
            "Ether: # (disabled)   Income: #",
            f"Pixels destroyed: P1→{k1}  P2→{k2}  (win {win_n})",
            f"Pixels left: P1={rem1}  P2={rem2}",
            "",
            "Towers:",
        ]
        for pid, tw in game.towers.items():
            lines.append(f"  P{int(pid)}: {tw.hp}/{tw.max_hp}")

        lines += [
            "",
            f"Status: {game.last_action}",
            "",
            "Q/E cycle | Tab undo move | C disabled",
            "1 action (red)  2 move (green)",
            "Atk: shoot pixels/units | Def: self=3×3 guard",
            "WASD preview | Enter confirm | Space end turn | Esc quit",
        ]

        if game.game_over:
            lines += [
                "",
                "Game Over",
                f"Winner: {'Draw' if game.winner is None else f'P{int(game.winner)}'}",
            ]

        for line in lines:
            surf.blit(self._font_small.render(line, True, COLOUR_TEXT), (hx, y))
            y += 17

    def _draw_skip_dialog(
        self, surf: pygame.Surface, game: GameState, ox: int, oy: int, gw: int, gh: int
    ) -> None:
        msg = "Skip this round?"
        sub = "Yes: Enter / Left click   No: Right click"
        w, h = 360, 90
        _, screen_h = compute_screen_size(gw, gh)
        x = gw * CELL // 2 - w // 2 + ox
        y = screen_h // 2 - h // 2
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(surf, (20, 28, 48), rect)
        pygame.draw.rect(surf, _COLOUR_PREVIEW, rect, 2)
        surf.blit(self._font_small.render(msg, True, COLOUR_TEXT), (x + 16, y + 18))
        surf.blit(self._font_small.render(sub, True, COLOUR_TEXT), (x + 16, y + 48))
