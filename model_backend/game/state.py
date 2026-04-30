from __future__ import annotations

"""Authoritative game state and rules implementation.

`GameState` is the rules engine used by the live tracker runtime (via the bridge layer).

This module intentionally contains the validation and state transitions that define
"what is legal" in the game. Adapters/transports should not replicate these rules;
they should call into `GameState` methods and surface `last_action` to the UI.
"""

from dataclasses import dataclass
from random import Random
import os
import time
from typing import Dict, Optional

import heapq

from .board import Board
from .entities import Attacker, CommandTower, Defender, Obstacle, Pixel, Unit
from .types import AttackDirection, Direction, PlayerId, Pos, TerrainType


@dataclass(slots=True)
class PlayerState:
    player: PlayerId
    # Placeholder contract fields kept for later resource/economy work.
    ether: int = 0
    income_per_turn: int = 0


class GameState:
    """
    Authoritative rules engine shared by both runtime paths.

    Bridge/tracker code may propose actions, but only this class decides whether an
    action is legal and how it mutates turn state, unit state, and win conditions.
    """

    PIXELS_PER_PLAYER_DEFAULT = 35
    MOVE_COUNTDOWN_SECONDS = 10.0
    # Testing toggle: allow placing units without pathfinding constraints.
    FREE_MOVE = os.environ.get("DYP_FREE_MOVE", "").strip().lower() in ("1", "true", "yes", "on")

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
            PlayerId.P1: PlayerState(PlayerId.P1, ether=0, income_per_turn=0),
            PlayerId.P2: PlayerState(PlayerId.P2, ether=0, income_per_turn=0),
        }

        # Filled by level loaders or demo setups.
        self.towers: Dict[PlayerId, CommandTower] = {}

        self.units: Dict[str, Unit] = {}
        self.obstacles: Dict[Pos, Obstacle] = {}
        self.pixels: Dict[str, Pixel] = {}

    # --- Setup helpers ---
    def add_unit(self, unit: Unit) -> None:
        self.units[unit.id] = unit

    def add_obstacle(self, obs: Obstacle) -> None:
        self.obstacles[obs.pos] = obs
        self.board.set_terrain(obs.pos, TerrainType.BLOCKED)

    def add_pixel(self, pixel: Pixel) -> None:
        self.pixels[pixel.id] = pixel

    def spawn_default_pixels(self, per_player: int | None = None) -> None:
        """Place pixels on empty plain tiles; left half → P1, right half → P2."""
        n = per_player if per_player is not None else self.PIXELS_PER_PLAYER_DEFAULT
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
        mid_x = self.board.width // 2
        left = sorted([p for p in candidates if p.x < mid_x], key=lambda q: (q.y, q.x))
        right = sorted([p for p in candidates if p.x >= mid_x], key=lambda q: (q.y, q.x))

        p1_pos = left[:n]
        p2_pos = right[:n]
        short1 = n - len(p1_pos)
        short2 = n - len(p2_pos)
        used = set(p1_pos) | set(p2_pos)
        spill = sorted([p for p in candidates if p not in used], key=lambda q: (q.y, q.x))
        for p in spill:
            if short1 > 0:
                p1_pos.append(p)
                short1 -= 1
                used.add(p)
            elif short2 > 0:
                p2_pos.append(p)
                short2 -= 1
                used.add(p)
            if short1 == 0 and short2 == 0:
                break

        pi = 0
        for pos in p1_pos:
            pid = f"px{pi}"
            pi += 1
            self.add_pixel(Pixel(id=pid, owner=PlayerId.P1, pos=pos))
        for pos in p2_pos:
            pid = f"px{pi}"
            pi += 1
            self.add_pixel(Pixel(id=pid, owner=PlayerId.P2, pos=pos))

    # --- Economy / turns ---
    def recompute_income(self) -> None:
        for p in self.players.values():
            p.income_per_turn = 0

    def start_turn(self) -> None:
        if self.game_over:
            return
        self.clear_move_countdown()
        self.recompute_income()
        # Economy is currently out of scope for the Old Mick MVP.
        for u in self.units.values():
            if u.owner == self.active_player:
                u.new_turn()
        self._sync_defender_protection()
        base = f"Player {int(self.active_player)} turn started"
        auto = self._auto_attack_at_turn_start()
        self.last_action = f"{base} | {auto}" if auto else base

    def end_turn(self) -> None:
        if self.game_over:
            return
        self.clear_move_countdown()
        self.active_player = PlayerId.P1 if self.active_player == PlayerId.P2 else PlayerId.P2
        self.turn += 1
        self.start_turn()
        self.end_game()

    def _require_active_unit(self, unit_id: str, *, action_name: str) -> Unit | None:
        if self.game_over:
            self.last_action = f"Cannot {action_name}; game is already over"
            return None

        u = self.units[unit_id]
        if u.owner != self.active_player:
            self.last_action = (
                f"{unit_id} belongs to Player {int(u.owner)}; "
                f"waiting for Player {int(self.active_player)}"
            )
            return None
        if not u.can_act():
            self.last_action = f"{unit_id} cannot act this turn"
            return None
        return u

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
        # The live tracker loop calls this every tick so turn-ending countdowns remain
        # authoritative on the Python side rather than relying on the frontend timer.
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

    # --- Core rules ---
    def is_blocked(self, p: Pos) -> bool:
        if not self.board.in_bounds(p):
            return True
        if self.board.get(p).terrain == TerrainType.BLOCKED:
            return True
        if self.tower_at(p) is not None:
            return True
        if p in self.obstacles:
            return True
        if self.pixel_at(p) is not None:
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

    def defender_protection_tiles(self, owner: PlayerId) -> set[Pos]:
        protected: set[Pos] = set()
        for unit in self.units.values():
            if not isinstance(unit, Defender) or unit.owner != owner:
                continue
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    pos = Pos(unit.pos.x + dx, unit.pos.y + dy)
                    if self.board.in_bounds(pos):
                        protected.add(pos)
        return protected

    def _sync_defender_protection(self) -> None:
        protected_by_owner = {
            PlayerId.P1: self.defender_protection_tiles(PlayerId.P1),
            PlayerId.P2: self.defender_protection_tiles(PlayerId.P2),
        }
        for pixel in self.pixels.values():
            pixel.protection_layers = 1 if pixel.pos in protected_by_owner[pixel.owner] else 0

    def attack_target_at(self, p: Pos, attacker_owner: PlayerId) -> Pixel | CommandTower | None:
        pixel = self.pixel_at(p)
        if pixel is not None and pixel.owner != attacker_owner:
            return pixel

        tower = self.tower_at(p)
        if tower is not None and tower.owner != attacker_owner:
            return tower

        return None

    def hard_terrain_blocks_attack(self, p: Pos) -> bool:
        if not self.board.in_bounds(p):
            return False
        if self.board.get(p).terrain == TerrainType.BLOCKED:
            return True
        return self.obstacle_at(p) is not None

    def move_cost(self, p: Pos) -> float:
        t = self.board.get(p).terrain
        if t == TerrainType.HIGHWAY:
            return 0.5
        if t in (TerrainType.FORTRESS, TerrainType.MOUNTAIN):
            return 2.0
        return 1.0

    def reachable_positions(self, unit_id: str) -> Dict[Pos, float]:
        """
        Returns minimal move cost to reach each position this turn.
        Includes the unit's current position with cost 0.
        """
        u = self.units[unit_id]
        # Movement is governed by move_points and legality; AP is reserved for attacks/acts.
        if u.owner != self.active_player or not u.can_act() or u.move_points <= 0:
            return {u.pos: 0.0}

        start = u.pos
        budget = float(u.move_points)
        best: Dict[Pos, float] = {start: 0.0}
        pq: list[tuple[float, int, int]] = [(0.0, start.x, start.y)]

        while pq:
            cost, x, y = heapq.heappop(pq)
            p = Pos(x, y)
            if cost != best.get(p, float("inf")):
                continue
            if cost > budget:
                continue

            for d in (Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT):
                nxt = p + d.delta()
                if self.is_blocked(nxt):
                    continue
                # Can't move through/onto other units (except our starting tile).
                occ = self.unit_at(nxt)
                if occ is not None and nxt != start:
                    continue
                step = self.move_cost(nxt)
                ncost = cost + step
                if ncost > budget:
                    continue
                if ncost < best.get(nxt, float("inf")):
                    best[nxt] = ncost
                    heapq.heappush(pq, (ncost, nxt.x, nxt.y))

        return best

    def move_unit_to(self, unit_id: str, dest: Pos) -> bool:
        """
        Commits a move to a chosen destination, consuming move_points based on
        minimal reachable cost this turn.
        """
        u = self._require_active_unit(unit_id, action_name="move that unit")
        if u is None:
            return False
        # Movement consumes move_points; AP is reserved for attacks/acts.
        if u.move_points <= 0:
            self.last_action = f"{unit_id} cannot move any farther this turn"
            return False
        if dest == u.pos:
            return True
        if not self.board.in_bounds(dest) or self.is_blocked(dest) or self.unit_at(dest) is not None:
            self.last_action = f"{unit_id} could not move to ({dest.x}, {dest.y})"
            return False
        if self.FREE_MOVE:
            cost = 1.0
        else:
            costs = self.reachable_positions(unit_id)
            cost = costs.get(dest)
            if cost is None or cost > u.move_points:
                self.last_action = f"{unit_id} does not have a legal path to ({dest.x}, {dest.y})"
                return False

        u.move_points -= cost
        u.pos = dest
        if self.board.get(dest).terrain == TerrainType.HIGHWAY:
            u.on_highway = True
        self._sync_defender_protection()
        moved_text = f"{unit_id} moved to ({dest.x}, {dest.y})"
        auto_text = self._auto_attack_if_adjacent(u, prefix="auto-attack")
        self.last_action = f"{moved_text} | {auto_text}" if auto_text else moved_text
        self.start_move_countdown(unit_id)
        self.end_game()
        return True

    def _adjacent_positions_4(self, p: Pos) -> list[Pos]:
        # Deterministic neighbor order for predictable auto-attack resolution.
        return [
            p + Direction.UP.delta(),
            p + Direction.RIGHT.delta(),
            p + Direction.DOWN.delta(),
            p + Direction.LEFT.delta(),
        ]

    def _auto_attack_at_turn_start(self) -> str | None:
        """
        At the start of the active player's turn, any adjacent enemy target may be
        auto-attacked once per attacker (consumes AP).
        """
        if self.game_over:
            return None

        events: list[str] = []
        # Deterministic ordering for tests and debugging.
        for u in sorted(self.units.values(), key=lambda x: x.id):
            if u.owner != self.active_player:
                continue
            if not isinstance(u, Attacker):
                continue
            text = self._auto_attack_if_adjacent(u, prefix="auto-attack")
            if text:
                events.append(text)
                self.end_game()
                if self.game_over:
                    break

        if not events:
            return None
        if len(events) == 1:
            return events[0]
        return f"{len(events)} auto-attacks: " + "; ".join(events)

    def _auto_attack_if_adjacent(self, unit: Unit, *, prefix: str) -> str | None:
        """
        If `unit` is an attacker adjacent (Manhattan distance 1) to an enemy target,
        automatically perform a single attack.

        Priority: enemy HQ > enemy resource tile > enemy unit.
        """
        if self.game_over:
            return None
        if not isinstance(unit, Attacker):
            return None
        if unit.ap <= 0:
            return None
        # Keep parity with the current directional-attack constraint.
        if unit.on_highway:
            return None

        adjacent = [p for p in self._adjacent_positions_4(unit.pos) if self.board.in_bounds(p)]

        hq: CommandTower | None = None
        px: Pixel | None = None
        enemy_unit: Unit | None = None

        for p in adjacent:
            tower = self.tower_at(p)
            if tower is not None and tower.owner != unit.owner:
                hq = tower
                break

        if hq is None:
            for p in adjacent:
                pixel = self.pixel_at(p)
                if pixel is not None and pixel.owner != unit.owner:
                    px = pixel
                    break

        if hq is None and px is None:
            for p in adjacent:
                other = self.unit_at(p)
                if other is not None and other.owner != unit.owner:
                    enemy_unit = other
                    break

        target: Pixel | CommandTower | Unit | None = hq or px or enemy_unit
        if target is None:
            return None

        action_text = None
        if isinstance(target, Pixel):
            if target.protection_layers > 0:
                target.protection_layers = 0
                action_text = (
                    f"{unit.id} {prefix} stripped protection from enemy {target.theme_name} "
                    f"at ({target.pos.x}, {target.pos.y})"
                )
            else:
                del self.pixels[target.id]
                action_text = (
                    f"{unit.id} {prefix} destroyed enemy {target.theme_name} "
                    f"at ({target.pos.x}, {target.pos.y})"
                )
        elif isinstance(target, CommandTower):
            target.hp = max(0, target.hp - 2)
            action_text = f"{unit.id} {prefix} hit enemy {target.theme_name} ({target.hp}/{target.max_hp})"
        else:
            target.hp = max(0, target.hp - 2)
            if target.hp <= 0:
                del self.units[target.id]
                action_text = f"{unit.id} {prefix} destroyed enemy unit {target.id}"
            else:
                action_text = f"{unit.id} {prefix} hit enemy unit {target.id} ({target.hp}/{target.max_hp})"

        unit.ap -= 1
        return action_text

    def trace_attack_line(
        self, unit_id: str, direction: AttackDirection
    ) -> tuple[Pixel | CommandTower | None, str | None]:
        attacker = self.units[unit_id]
        step = direction.delta()
        current = attacker.pos + step

        while self.board.in_bounds(current):
            if self.hard_terrain_blocks_attack(current):
                return None, f"{unit_id} line attack blocked at ({current.x}, {current.y})"

            target = self.attack_target_at(current, attacker.owner)
            if target is not None:
                return target, None

            current = current + step

        return None, f"{unit_id} found no enemy target on the {direction.value} line"

    def attack_in_direction(self, unit_id: str, direction: AttackDirection) -> bool:
        attacker = self._require_active_unit(unit_id, action_name="attack with that unit")
        if attacker is None:
            return False
        if not isinstance(attacker, Attacker):
            self.last_action = f"{unit_id} cannot perform directional attacks"
            return False
        if attacker.ap <= 0:
            self.last_action = f"{unit_id} cannot act right now"
            return False
        if attacker.on_highway:
            self.last_action = f"{unit_id} cannot attack after moving onto a highway"
            return False

        target, error = self.trace_attack_line(unit_id, direction)
        if target is None:
            self.last_action = error or f"{unit_id} attack failed"
            return False

        action_text = None
        if isinstance(target, Pixel):
            if target.protection_layers > 0:
                target.protection_layers = 0
                action_text = (
                    f"{unit_id} stripped protection from enemy {target.theme_name} at ({target.pos.x}, {target.pos.y})"
                )
            else:
                del self.pixels[target.id]
                action_text = (
                    f"{unit_id} destroyed enemy {target.theme_name} at ({target.pos.x}, {target.pos.y})"
                )
        else:
            target.hp = max(0, target.hp - 2)
            action_text = (
                f"{unit_id} hit enemy {target.theme_name} ({target.hp}/{target.max_hp})"
            )

        attacker.ap -= 1
        self._finish_turn_after_action(action_text)
        return True

    def _finish_turn_after_action(self, action_text: str) -> None:
        self.last_action = action_text
        self.end_game()

    def end_game(self) -> None:
        """Evaluate win/loss; call after a turn ends or after a decisive action."""
        self._update_game_over_towers()
        if self.game_over:
            self.clear_move_countdown()

    def _update_game_over_towers(self) -> None:
        if self.game_over:
            return
        defeated = [pid for pid, tower in self.towers.items() if tower.hp <= 0]
        if not defeated:
            return

        self.game_over = True
        if PlayerId.P1 in defeated and PlayerId.P2 in defeated:
            self.winner = None
            self.last_action = f"{self.last_action} | Both HQs destroyed: Draw"
            return

        loser = defeated[0]
        self.winner = PlayerId.P1 if loser == PlayerId.P2 else PlayerId.P2
        self.last_action = f"{self.last_action} | Player {int(self.winner)} wins by destroying the enemy HQ"

    # Heat / overload resolution (prototype)
    def overload_check(self, unit: Unit) -> bool:
        """
        Returns True if overload attempt succeeds, False if it fails (paralyzes 2 turns).
        Fail threshold grows with consecutive overload attempts:
          attempt 1 fails on 1-2
          attempt 2 fails on 1-3
          attempt 3 fails on 1-4, etc.
        """
        fail_max = 2 + unit.overload_streak
        roll = self.rng.randint(1, 6)
        if roll <= fail_max:
            unit.paralyzed_turns = 2
            unit.overload_streak = 0
            return False
        unit.overload_streak += 1
        return True

