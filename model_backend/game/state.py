from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Dict, List, Optional

import heapq

from .board import Board
from .entities import Attacker, CommandTower, Defender, EtherDrill, Obstacle, Pixel, Unit
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

    PIXELS_PER_PLAYER_DEFAULT = 35
    PIXELS_DESTROYED_TO_WIN = 20

    def __init__(self, seed: int = 1, board_width: int = 12, board_height: int = 12):
        self.rng = Random(seed)
        self.turn: int = 1
        self.active_player: PlayerId = PlayerId.P1
        self.game_over: bool = False
        self.winner: PlayerId | None = None
        self.last_action: str = "Ready"

        self.board = Board(board_width, board_height)
        self.players: Dict[PlayerId, PlayerState] = {
            PlayerId.P1: PlayerState(PlayerId.P1, ether=0, income_per_turn=0),
            PlayerId.P2: PlayerState(PlayerId.P2, ether=0, income_per_turn=0),
        }

        # Filled by level loader (or demos); pygame prototype uses ASCII maps.
        self.towers: Dict[PlayerId, CommandTower] = {}

        self.units: Dict[str, Unit] = {}
        self.drills: Dict[Pos, EtherDrill] = {}
        self.obstacles: Dict[Pos, Obstacle] = {}
        self.pixels: Dict[str, Pixel] = {}
        # How many enemy pixels each player has destroyed (win at PIXELS_DESTROYED_TO_WIN).
        self.pixels_destroyed_by: Dict[PlayerId, int] = {PlayerId.P1: 0, PlayerId.P2: 0}

    # --- Setup helpers ---
    def add_drill(self, pos: Pos, yield_per_turn: int = 1) -> None:
        self.drills[pos] = EtherDrill(pos=pos, owner=None, yield_per_turn=yield_per_turn)
        self.board.set_terrain(pos, TerrainType.ETHER_DRILL)

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
        for d in self.drills.values():
            if d.owner is not None:
                self.players[d.owner].income_per_turn += d.yield_per_turn

    def start_turn(self) -> None:
        if self.game_over:
            return
        self.recompute_income()
        # Ether / drill income disabled for pixel-win mode.
        for u in self.units.values():
            if u.owner == self.active_player:
                u.new_turn()
        self.last_action = f"Player {int(self.active_player)} turn started"

    def end_turn(self) -> None:
        if self.game_over:
            return
        self.active_player = PlayerId.P1 if self.active_player == PlayerId.P2 else PlayerId.P2
        self.turn += 1
        self.start_turn()
        self.end_game()

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
        self.last_action = f"{unit_id} moved to ({nxt.x}, {nxt.y})"
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
        self.last_action = f"{unit_id} moved to ({dest.x}, {dest.y})"
        return True

    def capture(self, unit_id: str) -> bool:
        self.last_action = "Ether/drill capture disabled (#)"
        return False

    def push(self, unit_id: str, direction: Direction) -> bool:
        u = self.units[unit_id]
        if u.owner != self.active_player or not u.can_act() or u.ap <= 0:
            return False
        enemy_pos = u.pos + direction.delta()
        enemy = self.unit_at(enemy_pos)
        if enemy is None or enemy.owner == u.owner:
            return False
        behind = enemy_pos + direction.delta()
        if self.is_blocked(behind) or self.unit_at(behind) is not None:
            return False
        u.ap -= 1
        enemy.pos = behind
        self.last_action = f"{unit_id} pushed {enemy.id} to ({behind.x}, {behind.y})"
        return True

    def tiles_in_action_range(self, unit_id: str) -> set[Pos]:
        u = self.units[unit_id]
        if u.owner != self.active_player or not u.can_act() or u.ap <= 0:
            return set()
        if u.on_highway:
            return set()

        rng = getattr(u, "range_base", getattr(u, "shield_range", 1))
        tiles: set[Pos] = set()
        for dy in range(-rng, rng + 1):
            for dx in range(-rng, rng + 1):
                if abs(dx) + abs(dy) > rng or (dx == 0 and dy == 0):
                    continue
                p = Pos(u.pos.x + dx, u.pos.y + dy)
                if self.board.in_bounds(p):
                    tiles.add(p)
        return tiles

    def valid_action_targets(self, unit_id: str) -> set[Pos]:
        u = self.units[unit_id]
        targets: set[Pos] = set()
        for pos in self.tiles_in_action_range(unit_id):
            unit = self.unit_at(pos)
            tower = self.tower_at(pos)
            obstacle = self.obstacle_at(pos)

            if isinstance(u, Attacker):
                pix = self.pixel_at(pos)
                if pix is not None and pix.owner != u.owner:
                    targets.add(pos)
                    continue
                if unit is not None and unit.owner != u.owner:
                    targets.add(pos)
                    continue
                if tower is not None and tower.owner != u.owner:
                    targets.add(pos)
                    continue
                if obstacle is not None and obstacle.owner != u.owner:
                    targets.add(pos)
                    continue

            if isinstance(u, Defender):
                if unit is not None and unit.owner == u.owner and unit.hp < unit.max_hp:
                    targets.add(pos)
                    continue
                if tower is not None and tower.owner == u.owner and tower.hp < tower.max_hp:
                    targets.add(pos)
                    continue

        return targets

    def act_on_target(self, unit_id: str, target: Pos) -> bool:
        u = self.units[unit_id]
        if u.owner != self.active_player or not u.can_act() or u.ap <= 0:
            self.last_action = f"{unit_id} cannot act right now"
            return False
        if u.on_highway:
            self.last_action = f"{unit_id} cannot act after moving onto a highway"
            return False
        if target not in self.valid_action_targets(unit_id):
            self.last_action = f"{unit_id} has no valid action on ({target.x}, {target.y})"
            return False

        success = False
        action_text = None
        if isinstance(u, Attacker):
            pix = self.pixel_at(target)
            if pix is not None and pix.owner != u.owner:
                del self.pixels[pix.id]
                self.pixels_destroyed_by[u.owner] += 1
                action_text = f"{unit_id} destroyed enemy pixel at ({target.x}, {target.y})"
                success = True
            enemy = self.unit_at(target)
            if not success and enemy is not None and enemy.owner != u.owner:
                enemy.hp -= 2
                if enemy.hp <= 0:
                    action_text = f"{unit_id} defeated {enemy.id}"
                    del self.units[enemy.id]
                else:
                    action_text = f"{unit_id} hit {enemy.id} ({enemy.hp}/{enemy.max_hp})"
                success = True
            if not success:
                tower = self.tower_at(target)
                if tower is not None and tower.owner != u.owner:
                    tower.hp = max(0, tower.hp - 2)
                    action_text = f"{unit_id} hit P{int(tower.owner)} tower ({tower.hp}/{tower.max_hp})"
                    success = True
                if not success:
                    obstacle = self.obstacle_at(target)
                    if obstacle is not None and obstacle.owner != u.owner:
                        obstacle.hp -= 2
                        if obstacle.hp <= 0:
                            del self.obstacles[target]
                            self.board.set_terrain(target, TerrainType.PLAIN)
                            action_text = f"{unit_id} destroyed obstacle at ({target.x}, {target.y})"
                        else:
                            action_text = f"{unit_id} damaged obstacle at ({target.x}, {target.y})"
                        success = True
        elif isinstance(u, Defender):
            ally = self.unit_at(target)
            if ally is not None and ally.owner == u.owner:
                ally.hp = min(ally.max_hp, ally.hp + 1)
                action_text = f"{unit_id} repaired {ally.id} ({ally.hp}/{ally.max_hp})"
                success = True
            else:
                tower = self.tower_at(target)
                if tower is not None and tower.owner == u.owner:
                    tower.hp = min(tower.max_hp, tower.hp + 1)
                    action_text = f"{unit_id} repaired P{int(tower.owner)} tower ({tower.hp}/{tower.max_hp})"
                    success = True

        if not success:
            return False

        u.ap -= 1
        self.last_action = action_text or f"{unit_id} acted on ({target.x}, {target.y})"
        self.end_game()
        return True

    def check_game_over(self) -> None:
        """Win when a player has destroyed PIXELS_DESTROYED_TO_WIN enemy pixels."""
        if self.game_over:
            return
        for pid in (PlayerId.P1, PlayerId.P2):
            if self.pixels_destroyed_by[pid] >= self.PIXELS_DESTROYED_TO_WIN:
                self.game_over = True
                self.winner = pid
                self.last_action = (
                    f"P{int(pid)} wins: destroyed {self.PIXELS_DESTROYED_TO_WIN} enemy pixels"
                )
                return

    def end_game(self) -> None:
        """Evaluate win/loss (pixel quota); call after a turn ends or after a decisive action."""
        self.check_game_over()
        self._update_game_over_towers()

    def _update_game_over_towers(self) -> None:
        if self.game_over:
            return
        defeated = [pid for pid, tower in self.towers.items() if tower.hp <= 0]
        if not defeated:
            return

        self.game_over = True
        if PlayerId.P1 in defeated and PlayerId.P2 in defeated:
            self.winner = None
            self.last_action = f"{self.last_action} | Draw"
            return

        loser = defeated[0]
        self.winner = PlayerId.P1 if loser == PlayerId.P2 else PlayerId.P2
        self.last_action = f"{self.last_action} | Player {int(self.winner)} wins"

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

