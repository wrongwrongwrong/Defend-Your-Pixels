from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Dict, List, Optional

import heapq

from .board import Board
from .entities import Attacker, CommandTower, Defender, EtherDrill, Obstacle, Unit
from .types import Direction, PlayerId, Pos, TerrainType


@dataclass(slots=True)
class PlayerState:
    player: PlayerId
    ether: int = 0
    income_per_turn: int = 0


class GameState:
    """
    Minimal rules engine for playability testing (no AR integration yet).
    """

    def __init__(self, seed: int = 1, board_width: int = 12, board_height: int = 12):
        self.rng = Random(seed)
        self.turn: int = 1
        self.active_player: PlayerId = PlayerId.P1

        self.board = Board(board_width, board_height)
        self.players: Dict[PlayerId, PlayerState] = {
            PlayerId.P1: PlayerState(PlayerId.P1, ether=10, income_per_turn=0),
            PlayerId.P2: PlayerState(PlayerId.P2, ether=10, income_per_turn=0),
        }

        # Filled by level loader (or demos); pygame prototype uses ASCII maps.
        self.towers: Dict[PlayerId, CommandTower] = {}

        self.units: Dict[str, Unit] = {}
        self.drills: Dict[Pos, EtherDrill] = {}
        self.obstacles: Dict[Pos, Obstacle] = {}

    # --- Setup helpers ---
    def add_drill(self, pos: Pos, yield_per_turn: int = 1) -> None:
        self.drills[pos] = EtherDrill(pos=pos, owner=None, yield_per_turn=yield_per_turn)
        self.board.set_terrain(pos, TerrainType.ETHER_DRILL)

    def add_unit(self, unit: Unit) -> None:
        self.units[unit.id] = unit

    def add_obstacle(self, obs: Obstacle) -> None:
        self.obstacles[obs.pos] = obs
        self.board.set_terrain(obs.pos, TerrainType.BLOCKED)

    # --- Economy / turns ---
    def recompute_income(self) -> None:
        for p in self.players.values():
            p.income_per_turn = 0
        for d in self.drills.values():
            if d.owner is not None:
                self.players[d.owner].income_per_turn += d.yield_per_turn

    def start_turn(self) -> None:
        self.recompute_income()
        ps = self.players[self.active_player]
        ps.ether += ps.income_per_turn
        for u in self.units.values():
            if u.owner == self.active_player:
                u.new_turn()

    def end_turn(self) -> None:
        self.active_player = PlayerId.P1 if self.active_player == PlayerId.P2 else PlayerId.P2
        self.turn += 1
        self.start_turn()

    # --- Core rules ---
    def is_blocked(self, p: Pos) -> bool:
        if not self.board.in_bounds(p):
            return True
        if self.board.get(p).terrain == TerrainType.BLOCKED:
            return True
        if p in self.obstacles:
            return True
        return False

    def unit_at(self, p: Pos) -> Optional[Unit]:
        for u in self.units.values():
            if u.pos == p:
                return u
        return None

    def move_cost(self, p: Pos) -> float:
        t = self.board.get(p).terrain
        if t == TerrainType.HIGHWAY:
            return 0.5
        if t in (TerrainType.FORTRESS, TerrainType.MOUNTAIN):
            return 2.0
        return 1.0

    def move_unit(self, unit_id: str, direction: Direction) -> bool:
        u = self.units[unit_id]
        if u.owner != self.active_player or not u.can_act():
            return False
        if u.ap <= 0:
            return False
        nxt = u.pos + direction.delta()
        if self.is_blocked(nxt) or self.unit_at(nxt) is not None:
            return False
        cost = self.move_cost(nxt)
        if u.move_points < cost:
            return False
        u.move_points -= cost
        u.pos = nxt
        if self.board.get(nxt).terrain == TerrainType.HIGHWAY:
            u.on_highway = True
        return True

    def reachable_positions(self, unit_id: str) -> Dict[Pos, float]:
        """
        Returns minimal move cost to reach each position this turn.
        Includes the unit's current position with cost 0.
        """
        u = self.units[unit_id]
        if u.owner != self.active_player or not u.can_act() or u.ap <= 0 or u.move_points <= 0:
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
        u = self.units[unit_id]
        if u.owner != self.active_player or not u.can_act():
            return False
        if u.ap <= 0 or u.move_points <= 0:
            return False
        if dest == u.pos:
            return True
        if not self.board.in_bounds(dest) or self.is_blocked(dest) or self.unit_at(dest) is not None:
            return False

        costs = self.reachable_positions(unit_id)
        cost = costs.get(dest)
        if cost is None or cost > u.move_points:
            return False

        u.move_points -= cost
        u.pos = dest
        if self.board.get(dest).terrain == TerrainType.HIGHWAY:
            u.on_highway = True
        return True

    def capture(self, unit_id: str) -> bool:
        u = self.units[unit_id]
        if u.owner != self.active_player or not u.can_act() or u.ap <= 0:
            return False
        ps = self.players[self.active_player]
        if ps.ether < 1:
            return False
        drill = self.drills.get(u.pos)
        if drill is None:
            return False
        ps.ether -= 1
        u.ap -= 1
        drill.owner = u.owner
        # Update income display immediately; ether is still granted on start_turn().
        self.recompute_income()
        return True

    def push(self, unit_id: str, direction: Direction) -> bool:
        u = self.units[unit_id]
        if u.owner != self.active_player or not u.can_act() or u.ap <= 0:
            return False
        ps = self.players[self.active_player]
        if ps.ether < 1:
            return False
        enemy_pos = u.pos + direction.delta()
        enemy = self.unit_at(enemy_pos)
        if enemy is None or enemy.owner == u.owner:
            return False
        behind = enemy_pos + direction.delta()
        if self.is_blocked(behind) or self.unit_at(behind) is not None:
            return False
        ps.ether -= 1
        u.ap -= 1
        enemy.pos = behind
        return True

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

