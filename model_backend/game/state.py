from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Dict, List, Optional

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

    def __init__(self, seed: int = 1):
        self.rng = Random(seed)
        self.turn: int = 1
        self.active_player: PlayerId = PlayerId.P1

        self.board = Board(12, 12)
        self.players: Dict[PlayerId, PlayerState] = {
            PlayerId.P1: PlayerState(PlayerId.P1, ether=10, income_per_turn=0),
            PlayerId.P2: PlayerState(PlayerId.P2, ether=10, income_per_turn=0),
        }

        self.towers: Dict[PlayerId, CommandTower] = {
            PlayerId.P1: CommandTower(PlayerId.P1, pos=Pos(0, 0)),
            PlayerId.P2: CommandTower(PlayerId.P2, pos=Pos(11, 11)),
        }

        self.units: Dict[str, Unit] = {}
        self.drills: Dict[Pos, EtherDrill] = {}
        self.obstacles: Dict[Pos, Obstacle] = {}

    # --- Setup helpers ---
    def add_drill(self, pos: Pos, yield_per_turn: int = 5) -> None:
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

