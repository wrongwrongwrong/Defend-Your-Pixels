from __future__ import annotations

"""Authoritative game state and rules implementation.

Aligned with ``prototype_pygame_version2`` mechanics:

- **Movement**: Chebyshev distance ≤ TOKEN_MOVE_RANGE from start-of-turn origin.
- **Attack**: ray-based (direction h/v/d); resolved on ``end_turn``.
- **Defence**: 3×3 (or 5×5 with DEF+ upgrade) shield on friendly pixels.
- **Terrain**: Wall (BLOCKED, indestructible) and Barricade (Obstacle HP=2, becomes PLAIN).
- **Win**: all enemy pixels destroyed *or* HQ pixel destroyed.
- **Upgrades**: Splash (3 kills), DEF+ (6), Bonus ATK (10).
"""

from dataclasses import dataclass
from random import Random
import time
from typing import Dict, Optional

from .board import Board
from .entities import Attacker, CommandTower, Defender, EtherDrill, Obstacle, Pixel, Unit
from .types import (
    ATK_DIRS, Direction, PlayerId, Pos, TerrainType, UPGRADES,
    CELLS_PER_PLAYER, TOKEN_MOVE_RANGE, BARRICADE_HP,
    chebyshev_distance,
)


@dataclass(slots=True)
class PlayerState:
    player: PlayerId
    ether: int = 0
    income_per_turn: int = 0


class GameState:
    """
    Authoritative rules engine shared by both runtime paths.

    Bridge/tracker code may propose actions, but only this class decides whether an
    action is legal and how it mutates turn state, unit state, and win conditions.
    """

    CELLS_PER_PLAYER = CELLS_PER_PLAYER
    BARRICADE_HP = BARRICADE_HP
    MOVE_COUNTDOWN_SECONDS = 10.0

    def __init__(self, seed: int = 1, board_width: int = 12, board_height: int = 12):
        self.rng = Random(seed)
        self.turn: int = 1
        self.active_player: PlayerId = PlayerId.P1
        self.game_over: bool = False
        self.winner: PlayerId | None = None
        self.last_action: str = "Ready"
        self.move_countdown_deadline: float | None = None
        self.move_countdown_unit_id: str | None = None

        self.board = Board(board_width, board_height)
        self.players: Dict[PlayerId, PlayerState] = {
            PlayerId.P1: PlayerState(PlayerId.P1),
            PlayerId.P2: PlayerState(PlayerId.P2),
        }

        self.towers: Dict[PlayerId, CommandTower] = {}
        self.units: Dict[str, Unit] = {}
        self.drills: Dict[Pos, EtherDrill] = {}
        self.obstacles: Dict[Pos, Obstacle] = {}
        self.pixels: Dict[str, Pixel] = {}

        self.kills: Dict[PlayerId, int] = {PlayerId.P1: 0, PlayerId.P2: 0}
        self.upg: Dict[PlayerId, set] = {PlayerId.P1: set(), PlayerId.P2: set()}
        self.new_upg: Dict[PlayerId, set] = {PlayerId.P1: set(), PlayerId.P2: set()}
        self.pixels_destroyed_by: Dict[PlayerId, int] = {PlayerId.P1: 0, PlayerId.P2: 0}

        self._start_positions: Dict[str, Pos] = {}
        self.log: list = []

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def add_drill(self, pos: Pos, yield_per_turn: int = 1) -> None:
        self.drills[pos] = EtherDrill(pos=pos, owner=None, yield_per_turn=yield_per_turn)

    def add_unit(self, unit: Unit) -> None:
        self.units[unit.id] = unit

    def add_obstacle(self, obs: Obstacle) -> None:
        self.obstacles[obs.pos] = obs
        self.board.set_terrain(obs.pos, TerrainType.BLOCKED)

    def add_pixel(self, pixel: Pixel) -> None:
        self.pixels[pixel.id] = pixel

    def spawn_default_pixels(self, per_player: int | None = None) -> None:
        """Place pixels on empty plain tiles using diagonal territory split."""
        n = per_player if per_player is not None else self.CELLS_PER_PLAYER
        threshold = self.board.width - 1

        candidates: list[Pos] = []
        for y in range(self.board.height):
            for x in range(self.board.width):
                p = Pos(x, y)
                if self.board.get(p).terrain != TerrainType.PLAIN:
                    continue
                if self.unit_at(p) is not None or self.tower_at(p) is not None:
                    continue
                if self.pixel_at(p) is not None:
                    continue
                candidates.append(p)

        p1_cands = sorted(
            [p for p in candidates if p.x + p.y < threshold],
            key=lambda q: (q.y, q.x),
        )
        p2_cands = sorted(
            [p for p in candidates if p.x + p.y > threshold],
            key=lambda q: (q.y, q.x),
        )

        p1_pos = p1_cands[:n]
        p2_pos = p2_cands[:n]

        pi = 0
        for pos in p1_pos:
            self.add_pixel(Pixel(id=f"px{pi}", owner=PlayerId.P1, pos=pos))
            pi += 1
        for pos in p2_pos:
            self.add_pixel(Pixel(id=f"px{pi}", owner=PlayerId.P2, pos=pos))
            pi += 1

    # ------------------------------------------------------------------
    # Territory
    # ------------------------------------------------------------------

    def in_territory(self, player: PlayerId, pos: Pos) -> bool:
        threshold = self.board.width - 1
        if player == PlayerId.P1:
            return pos.x + pos.y < threshold
        return pos.x + pos.y > threshold

    # ------------------------------------------------------------------
    # Turns
    # ------------------------------------------------------------------

    def recompute_income(self) -> None:
        for p in self.players.values():
            p.income_per_turn = 0
        for d in self.drills.values():
            if d.owner is not None:
                self.players[d.owner].income_per_turn += d.yield_per_turn

    def start_turn(self) -> None:
        if self.game_over:
            return
        self.clear_move_countdown()
        self.recompute_income()
        self._start_positions = {
            uid: u.pos for uid, u in self.units.items()
            if u.owner == self.active_player
        }
        for u in self.units.values():
            if u.owner == self.active_player:
                u.new_turn()
        self.last_action = f"Player {int(self.active_player)} turn started"

    def end_turn(self) -> None:
        if self.game_over:
            return
        self.clear_move_countdown()
        self.resolve()
        if self.game_over:
            return
        self.active_player = PlayerId.P1 if self.active_player == PlayerId.P2 else PlayerId.P2
        self.turn += 1
        self.start_turn()

    # ------------------------------------------------------------------
    # Timer / countdown (kept for live-tracker)
    # ------------------------------------------------------------------

    @property
    def move_countdown_active(self) -> bool:
        return self.move_countdown_deadline is not None

    def start_move_countdown(self, unit_id: str, now: float | None = None) -> None:
        if self.game_over:
            return
        current = time.monotonic() if now is None else now
        self.move_countdown_deadline = current + self.MOVE_COUNTDOWN_SECONDS
        self.move_countdown_unit_id = unit_id

    def clear_move_countdown(self) -> None:
        self.move_countdown_deadline = None
        self.move_countdown_unit_id = None

    def move_countdown_seconds_remaining(self, now: float | None = None) -> float:
        if self.move_countdown_deadline is None:
            return 0.0
        current = time.monotonic() if now is None else now
        return round(max(0.0, self.move_countdown_deadline - current), 1)

    def advance_timers(self, now: float | None = None) -> None:
        if self.game_over or self.move_countdown_deadline is None:
            return
        current = time.monotonic() if now is None else now
        if current < self.move_countdown_deadline:
            return
        unit_id = self.move_countdown_unit_id
        self.end_turn()
        if self.game_over:
            return
        if unit_id is not None:
            self.last_action = f"{unit_id} move timer expired; {self.last_action}"
        else:
            self.last_action = f"Move timer expired; {self.last_action}"

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def is_blocked(self, p: Pos) -> bool:
        if not self.board.in_bounds(p):
            return True
        if self.board.get(p).terrain == TerrainType.BLOCKED:
            return True
        if p in self.obstacles:
            return True
        return False

    def pixel_at(self, p: Pos) -> Optional[Pixel]:
        for px in self.pixels.values():
            if px.pos == p:
                return px
        return None

    def unit_at(self, p: Pos) -> Optional[Unit]:
        for u in self.units.values():
            if u.pos == p:
                return u
        return None

    def tower_at(self, p: Pos) -> Optional[CommandTower]:
        for tower in self.towers.values():
            if tower.pos == p:
                return tower
        return None

    def obstacle_at(self, p: Pos) -> Optional[Obstacle]:
        return self.obstacles.get(p)

    # ------------------------------------------------------------------
    # Movement (Chebyshev distance from start-of-turn origin)
    # ------------------------------------------------------------------

    def reachable_positions(self, unit_id: str) -> Dict[Pos, float]:
        """All tiles reachable this turn (Chebyshev ≤ TOKEN_MOVE_RANGE from origin)."""
        u = self.units[unit_id]
        if u.owner != self.active_player or not u.can_act():
            return {u.pos: 0.0}

        origin = self._start_positions.get(unit_id, u.pos)
        result: Dict[Pos, float] = {}
        rng = TOKEN_MOVE_RANGE

        for dy in range(-rng, rng + 1):
            for dx in range(-rng, rng + 1):
                p = Pos(origin.x + dx, origin.y + dy)
                if not self.board.in_bounds(p):
                    continue
                if self.is_blocked(p):
                    continue
                occ = self.unit_at(p)
                if occ is not None and occ.id != unit_id:
                    continue
                if not self.in_territory(u.owner, p):
                    continue
                result[p] = float(chebyshev_distance(origin, p))

        return result

    def move_unit_to(self, unit_id: str, dest: Pos) -> bool:
        """Move a unit to *dest* if it's within Chebyshev range of the start-of-turn origin."""
        u = self.units.get(unit_id)
        if u is None:
            self.last_action = f"Unknown unit: {unit_id}"
            return False
        if self.game_over:
            self.last_action = "Cannot move; game is over"
            return False
        if u.owner != self.active_player:
            self.last_action = (
                f"{unit_id} belongs to P{int(u.owner)}; "
                f"waiting for P{int(self.active_player)}"
            )
            return False
        if not u.can_act():
            self.last_action = f"{unit_id} cannot act this turn"
            return False
        if dest == u.pos:
            return True
        if not self.board.in_bounds(dest):
            self.last_action = f"{unit_id} could not move to ({dest.x}, {dest.y})"
            return False
        if self.is_blocked(dest):
            self.last_action = f"{unit_id} could not move to ({dest.x}, {dest.y})"
            return False
        occ = self.unit_at(dest)
        if occ is not None and occ.id != unit_id:
            self.last_action = f"{unit_id} could not move to ({dest.x}, {dest.y})"
            return False
        if not self.in_territory(u.owner, dest):
            self.last_action = f"{unit_id} cannot move outside territory"
            return False

        origin = self._start_positions.get(unit_id, u.pos)
        dist = chebyshev_distance(origin, dest)
        if dist > TOKEN_MOVE_RANGE:
            self.last_action = f"{unit_id} out of range (max {TOKEN_MOVE_RANGE} tiles)"
            return False

        u.pos = dest
        self.last_action = f"{unit_id} moved to ({dest.x}, {dest.y})"
        self.start_move_countdown(unit_id)
        return True

    def move_unit(self, unit_id: str, direction: Direction) -> bool:
        """Single-step directional move (kept for compatibility)."""
        u = self.units.get(unit_id)
        if u is None:
            return False
        nxt = u.pos + direction.delta()
        return self.move_unit_to(unit_id, nxt)

    def set_direction(self, unit_id: str, direction: str) -> bool:
        """Set attack direction ('h'/'v'/'d') for an attacker."""
        u = self.units.get(unit_id)
        if u is None or not isinstance(u, Attacker):
            self.last_action = f"{unit_id} is not an attacker"
            return False
        if u.owner != self.active_player:
            self.last_action = f"{unit_id} belongs to P{int(u.owner)}"
            return False
        if direction not in ("h", "v", "d"):
            self.last_action = f"Invalid direction: {direction}"
            return False
        u.atk_dir = direction
        self.last_action = f"{unit_id} direction set to {direction}"
        return True

    def capture(self, unit_id: str) -> bool:
        self.last_action = "Capture disabled"
        return False

    # ------------------------------------------------------------------
    # Combat resolution (called automatically by end_turn)
    # ------------------------------------------------------------------

    def resolve(self) -> None:
        """
        Resolve the active player's turn (mirrors prototype_pygame_version2/game/logic.py).

        Order:
            1. Clear own shields from previous round
            2. DEF shield (3×3 base, 5×5 with DEF+ upgrade)
            3. Fire ATK rays (stacked → AOE, separate → individual)
            4. T3 bonus attack from first ATK
            5. Win check
        """
        p = self.active_player
        enemy = PlayerId.P2 if p == PlayerId.P1 else PlayerId.P1
        king_hit = False
        self.new_upg = {PlayerId.P1: set(), PlayerId.P2: set()}

        # 1 — clear own shields
        for px in self.pixels.values():
            if px.owner == p:
                px.guarded_turns = 0

        # 2 — DEF shield
        for u in self.units.values():
            if u.owner != p or not isinstance(u, Defender):
                continue
            radius = 2 if "dt2" in self.upg[p] else 1
            shielded = 0
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    sp = Pos(u.pos.x + dx, u.pos.y + dy)
                    if not self.board.in_bounds(sp):
                        continue
                    px = self.pixel_at(sp)
                    if px is not None and px.owner == p:
                        px.guarded_turns = 1
                        shielded += 1
            size = "5×5" if radius == 2 else "3×3"
            self._log_event(
                f"DEF shields {shielded} pixels ({size} around ({u.pos.x},{u.pos.y}))"
            )

        # 3 — ATK rays
        attackers = sorted(
            [u for u in self.units.values() if u.owner == p and isinstance(u, Attacker)],
            key=lambda u: u.id,
        )

        stacked = (
            len(attackers) == 2
            and attackers[0].pos == attackers[1].pos
            and attackers[0].atk_dir is not None
            and attackers[1].atk_dir is not None
        )

        if stacked:
            a1 = attackers[0]
            target = self._fire_ray(a1.pos, p, a1.atk_dir or "h")
            if target is not None:
                res = self._hit_cell(target, p, "STACK")
                if res == "king":
                    king_hit = True
                if res and target not in self.obstacles:
                    for epos in self._adj_enemy(p, target):
                        if self._hit_cell(epos, p, "STACK-AOE") == "king":
                            king_hit = True
        else:
            for atk in attackers:
                if not atk.atk_dir:
                    self._log_event(f"{atk.id} has no direction — skip")
                    continue
                target = self._fire_ray(atk.pos, p, atk.atk_dir)
                if target is not None:
                    res = self._hit_cell(target, p, atk.id.upper())
                    if res == "king":
                        king_hit = True
                    elif res and "t2" in self.upg[p] and target not in self.obstacles:
                        for epos in self._adj_enemy(p, target)[:1]:
                            if self._hit_cell(epos, p, "SPLASH") == "king":
                                king_hit = True

        # 4 — T3 bonus attack from first attacker
        if "t3" in self.upg[p] and attackers and attackers[0].atk_dir:
            target = self._fire_ray(attackers[0].pos, p, attackers[0].atk_dir)
            if target is not None:
                if self._hit_cell(target, p, "T3-BONUS") == "king":
                    king_hit = True

        # 5 — win check
        self._check_win(king_hit)

    # ------------------------------------------------------------------
    # Ray casting
    # ------------------------------------------------------------------

    def _fire_ray(self, origin: Pos, player: PlayerId, direction: str) -> Pos | None:
        """Cast an attack ray; return first hittable position or None."""
        enemy = PlayerId.P2 if player == PlayerId.P1 else PlayerId.P1
        delta = ATK_DIRS[player][direction]
        nx, ny = origin.x + delta.x, origin.y + delta.y

        while self.board.in_bounds(Pos(nx, ny)):
            pos = Pos(nx, ny)
            terrain = self.board.get(pos).terrain

            # Wall — BLOCKED terrain without an obstacle
            if terrain == TerrainType.BLOCKED and pos not in self.obstacles:
                return None
            # Barricade — obstacle (hittable)
            if pos in self.obstacles:
                return pos
            # Enemy pixel
            px = self.pixel_at(pos)
            if px is not None and px.owner == enemy:
                return pos

            nx += delta.x
            ny += delta.y
        return None

    # ------------------------------------------------------------------
    # Hit resolution
    # ------------------------------------------------------------------

    def _hit_cell(self, pos: Pos, attacker: PlayerId, label: str = "ATK") -> object:
        """Apply one hit. Returns ``'king'``, ``True`` (destroyed), or ``False``."""
        enemy = PlayerId.P2 if attacker == PlayerId.P1 else PlayerId.P1

        obs = self.obstacles.get(pos)
        if obs is not None:
            obs.hp -= 1
            if obs.hp <= 0:
                del self.obstacles[pos]
                self.board.set_terrain(pos, TerrainType.PLAIN)
                self._log_event(f"{label} destroyed barricade at ({pos.x},{pos.y})")
                return True
            self._log_event(f"{label} hit barricade at ({pos.x},{pos.y}) (HP {obs.hp})")
            return False

        px = self.pixel_at(pos)
        if px is None:
            return False

        if px.guarded_turns > 0:
            self._log_event(f"{label} blocked by shield at ({pos.x},{pos.y})")
            px.guarded_turns = 0
            return False

        del self.pixels[px.id]
        self.kills[attacker] += 1
        self.pixels_destroyed_by[attacker] += 1
        self._check_upgrades(attacker)

        if enemy in self.towers and self.towers[enemy].pos == pos:
            self._log_event(f"HQ pixel at ({pos.x},{pos.y}) destroyed! P{int(attacker)} wins!")
            return "king"

        self._log_event(f"{label} destroyed pixel at ({pos.x},{pos.y})")
        return True

    def _adj_enemy(self, player: PlayerId, pos: Pos) -> list[Pos]:
        enemy = PlayerId.P2 if player == PlayerId.P1 else PlayerId.P1
        result: list[Pos] = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            p = Pos(pos.x + dx, pos.y + dy)
            if not self.board.in_bounds(p):
                continue
            px = self.pixel_at(p)
            if px is not None and px.owner == enemy:
                result.append(p)
        return result

    # ------------------------------------------------------------------
    # Upgrades
    # ------------------------------------------------------------------

    def _check_upgrades(self, player: PlayerId) -> None:
        k = self.kills[player]
        u = self.upg[player]
        for thresh, key, name, _ in UPGRADES:
            if k >= thresh and key not in u:
                u.add(key)
                self.new_upg[player].add(key)
                self._log_event(f"P{int(player)} unlocked {name}!")

    # ------------------------------------------------------------------
    # Win conditions
    # ------------------------------------------------------------------

    def _check_win(self, king_hit: bool = False) -> bool:
        if self.game_over:
            return True

        enemy = PlayerId.P2 if self.active_player == PlayerId.P1 else PlayerId.P1
        enemy_alive = any(px.owner == enemy for px in self.pixels.values())

        if king_hit or not enemy_alive:
            self.game_over = True
            self.winner = self.active_player
            self.last_action = f"P{int(self.active_player)} wins!"
            self.clear_move_countdown()
            return True
        return False

    def check_game_over(self) -> None:
        self._check_win()

    def end_game(self) -> None:
        self.check_game_over()
        if self.game_over:
            self.clear_move_countdown()

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log_event(self, msg: str, cls: str = "info") -> None:
        self.log.insert(0, {"msg": msg, "cls": cls})
        if len(self.log) > 40:
            self.log.pop()
