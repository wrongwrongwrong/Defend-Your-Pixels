"""
Authoritative game state for Old Mick Against the Mob.

Tracks per-cell damage, hidden HQs, scored resource destruction, tier levels, and
win conditions. Turn-resolution is triggered externally — the server calls
`on_turn_change(new_turn)` whenever the physical turn marker flips.
"""

import random
from dataclasses import dataclass, field

GRID_COLS, GRID_ROWS = 12, 12
ATTRITION_THRESHOLD = 40
TIER_THRESHOLDS = (6, 14, 22, 32)
DEF_ZONE_RADIUS_T1 = 1
DEF_ZONE_RADIUS_T2 = 2

DIR_VEC = {
    "E": (1, 0), "SE": (1, 1), "S": (0, 1), "SW": (-1, 1),
    "W": (-1, 0), "NW": (-1, -1), "N": (0, -1), "NE": (1, -1),
}


def _side_of(c, r):
    """Which player's territory a cell belongs to. None = fence line."""
    if c + r < 11:
        return "p1"
    if c + r > 11:
        return "p2"
    return None


@dataclass
class GameModel:
    terrain: dict
    hq_p1: tuple
    hq_p2: tuple
    rng: random.Random = field(default_factory=random.Random)
    tier_p1: int = 0
    tier_p2: int = 0
    damage: dict = field(default_factory=dict)
    destroyed: set = field(default_factory=set)
    soft_damage: dict = field(default_factory=dict)
    soft_gone: set = field(default_factory=set)
    last_turn: int | None = None
    winner: str | None = None
    win_reason: str | None = None
    hq_reveal: dict = field(default_factory=dict)
    nuke_used_p1: bool = False
    nuke_used_p2: bool = False

    def _def_zone(self, player: str, def_pos):
        if def_pos is None or def_pos[0] is None:
            return set()
        tier = self.tier_p1 if player == "p1" else self.tier_p2
        rad = DEF_ZONE_RADIUS_T2 if tier >= 2 else DEF_ZONE_RADIUS_T1
        dc, dr = def_pos
        return {
            (dc + x, dr + y)
            for x in range(-rad, rad + 1)
            for y in range(-rad, rad + 1)
            if 0 <= dc + x < GRID_COLS and 0 <= dr + y < GRID_ROWS
        }

    def _resource_by_cell(self, side: str, cell: tuple[int, int]) -> dict | None:
        for resource in self.terrain.get(f"{side}_resources", []):
            if (resource["col"], resource["row"]) == cell:
                return resource
        return None

    def _resource_value(self, side: str, cell: tuple[int, int]) -> int:
        resource = self._resource_by_cell(side, cell)
        return int(resource.get("value", 1)) if resource is not None else 0

    def _resource_base_hp(self, side: str, cell: tuple[int, int]) -> int:
        resource = self._resource_by_cell(side, cell)
        return int(resource.get("max_hp", 1)) if resource is not None else 1

    def _cell_required_hp(self, cell, defender, def_pos):
        base_hp = self._resource_base_hp(defender, cell)
        zone_bonus = 1 if cell in self._def_zone(defender, def_pos) else 0
        return base_hp + zone_bonus

    def _cell_is_hard(self, cell):
        for group in ("p1_hard", "p2_hard"):
            for tile in self.terrain[group]:
                if (tile["col"], tile["row"]) == cell:
                    return True
        return False

    def _cell_is_soft(self, cell):
        for group in ("p1_soft", "p2_soft"):
            for tile in self.terrain[group]:
                if (tile["col"], tile["row"]) == cell and tuple(cell) not in self.soft_gone:
                    return True
        return False

    def _is_hq_cell(self, side: str, cell: tuple[int, int]) -> bool:
        hq = self.hq_p1 if side == "p1" else self.hq_p2
        return tuple(cell) == tuple(hq)

    def _is_resource_cell(self, cell, side):
        return self._resource_by_cell(side, cell) is not None

    def _cell_is_attackable_target(self, cell: tuple[int, int], side: str) -> bool:
        return self._is_hq_cell(side, cell) or self._is_resource_cell(cell, side)

    def _enemy_destroyed_count(self, side):
        return sum(1 for cell in self.destroyed if _side_of(*cell) == side)

    def _enemy_destroyed_resource_count(self, side):
        return sum(1 for cell in self.destroyed if self._is_resource_cell(cell, side))

    def _destroyed_resource_score(self, side: str) -> int:
        return sum(self._resource_value(side, cell) for cell in self.destroyed if self._is_resource_cell(cell, side))

    def _progress_points(self, player: str) -> int:
        enemy_side = "p2" if player == "p1" else "p1"
        return self._destroyed_resource_score(enemy_side)

    def _tier_from_progress(self, progress: int) -> int:
        tier = 0
        for index, threshold in enumerate(TIER_THRESHOLDS, start=1):
            if progress >= threshold:
                tier = index
        return tier

    def _sync_tiers_from_progress(self) -> None:
        self.tier_p1 = max(self.tier_p1, self._tier_from_progress(self._progress_points("p1")))
        self.tier_p2 = max(self.tier_p2, self._tier_from_progress(self._progress_points("p2")))

    def _attacker_splash_count(self, attacker: str) -> int:
        tier = self.tier_p1 if attacker == "p1" else self.tier_p2
        if tier >= 3:
            return 2
        if tier >= 1:
            return 1
        return 0

    def _nuke_used(self, player: str) -> bool:
        return self.nuke_used_p1 if player == "p1" else self.nuke_used_p2

    def _set_nuke_used(self, player: str) -> None:
        if player == "p1":
            self.nuke_used_p1 = True
        else:
            self.nuke_used_p2 = True

    def _valid_splash_targets(self, enemy_side: str, primary_cell: tuple[int, int]) -> list[tuple[int, int]]:
        c, r = primary_cell
        candidates: list[tuple[int, int]] = []
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            cell = (c + dc, r + dr)
            if not (0 <= cell[0] < GRID_COLS and 0 <= cell[1] < GRID_ROWS):
                continue
            if _side_of(*cell) != enemy_side:
                continue
            if cell in self.destroyed:
                continue
            if self._is_hq_cell(enemy_side, cell):
                continue
            if not self._is_resource_cell(cell, enemy_side):
                continue
            candidates.append(cell)
        return candidates

    def _apply_hit(self, attacker: str, enemy_side: str, cell: tuple[int, int], defender_def_pos, *, splash: bool = False) -> list[dict]:
        req = self._cell_required_hp(cell, enemy_side, defender_def_pos)
        self.damage[cell] = self.damage.get(cell, 0) + 1
        resource_value = self._resource_value(enemy_side, cell)
        if self.damage[cell] >= req:
            self.destroyed.add(cell)
            events = [{
                "type": "cell_destroyed",
                "cell": cell,
                "side": enemy_side,
                "value": resource_value,
                "splash": splash,
            }]
            if self._is_hq_cell(enemy_side, cell):
                self.hq_reveal[enemy_side] = list(cell)
                self.winner = attacker
                self.win_reason = ("homestead" if enemy_side == "p1" else "nest") + "_destroyed"
                events.append({"type": "hq_destroyed", "side": enemy_side})
            else:
                self._sync_tiers_from_progress()
                if self._destroyed_resource_score(enemy_side) >= ATTRITION_THRESHOLD:
                    self.winner = attacker
                    self.win_reason = "attrition"
                    events.append({"type": "attrition_win", "side": enemy_side})
            return events

        return [{
            "type": "cell_damaged",
            "cell": cell,
            "remaining_hp": req - self.damage[cell],
            "required_hp": req,
            "value": resource_value,
            "splash": splash,
        }]

    def _apply_splash_hits(self, attacker: str, enemy_side: str, primary_cell: tuple[int, int], defender_def_pos) -> list[dict]:
        splash_count = self._attacker_splash_count(attacker)
        if splash_count <= 0 or self.winner:
            return []
        candidates = self._valid_splash_targets(enemy_side, primary_cell)
        if not candidates:
            return []
        chosen = self.rng.sample(candidates, k=min(splash_count, len(candidates)))
        events: list[dict] = []
        for cell in chosen:
            events.extend(self._apply_hit(attacker, enemy_side, cell, defender_def_pos, splash=True))
            if self.winner:
                break
        return events

    def trigger_nuke(self, attacker: str, center: tuple[int, int]) -> list[dict]:
        if self.winner:
            return []
        if attacker not in {"p1", "p2"}:
            return []
        if (self.tier_p1 if attacker == "p1" else self.tier_p2) < 4:
            return []
        if self._nuke_used(attacker):
            return []

        enemy_side = "p2" if attacker == "p1" else "p1"
        if _side_of(*center) != enemy_side:
            return []

        self._set_nuke_used(attacker)
        events: list[dict] = [{"type": "nuke_triggered", "side": attacker, "center": list(center)}]

        cx, cy = center
        for row in range(cy - 1, cy + 2):
            for col in range(cx - 1, cx + 2):
                if not (0 <= col < GRID_COLS and 0 <= row < GRID_ROWS):
                    continue
                cell = (col, row)
                if _side_of(col, row) != enemy_side:
                    continue
                if self._cell_is_soft(cell):
                    self.soft_damage[cell] = max(self.soft_damage.get(cell, 0), 2)
                    self.soft_gone.add(cell)
                    events.append({"type": "soft_destroyed", "cell": cell, "nuke": True})
                    continue
                if cell in self.destroyed:
                    continue
                if not self._cell_is_attackable_target(cell, enemy_side):
                    continue
                if self._is_hq_cell(enemy_side, cell):
                    self.destroyed.add(cell)
                    self.hq_reveal[enemy_side] = list(cell)
                    self.winner = attacker
                    self.win_reason = ("homestead" if enemy_side == "p1" else "nest") + "_destroyed"
                    events.append({"type": "cell_destroyed", "cell": cell, "side": enemy_side, "value": 0, "nuke": True})
                    events.append({"type": "hq_destroyed", "side": enemy_side})
                    return events
                self.damage[cell] = max(self.damage.get(cell, 0), self._cell_required_hp(cell, enemy_side, (None, None)))
                self.destroyed.add(cell)
                events.append({
                    "type": "cell_destroyed",
                    "cell": cell,
                    "side": enemy_side,
                    "value": self._resource_value(enemy_side, cell),
                    "nuke": True,
                })

        self._sync_tiers_from_progress()
        if self._destroyed_resource_score(enemy_side) >= ATTRITION_THRESHOLD:
            self.winner = attacker
            self.win_reason = "attrition"
            events.append({"type": "attrition_win", "side": enemy_side})
        return events

    def _resolve_shot(self, attacker: str, start, direction: str, defender_def_pos):
        """Fire one ray. Returns list of events for this shot."""
        if start[0] is None or direction not in DIR_VEC:
            return []
        enemy_side = "p2" if attacker == "p1" else "p1"
        dc, dr = DIR_VEC[direction]
        c, r = start[0] + dc, start[1] + dr
        events = []

        while 0 <= c < GRID_COLS and 0 <= r < GRID_ROWS:
            cell = (c, r)

            if self._cell_is_hard(cell):
                events.append({"type": "blocked_hard", "cell": cell})
                return events
            if self._cell_is_soft(cell):
                self.soft_damage[cell] = self.soft_damage.get(cell, 0) + 1
                if self.soft_damage[cell] >= 2:
                    self.soft_gone.add(cell)
                    events.append({"type": "soft_destroyed", "cell": cell})
                else:
                    events.append({"type": "soft_hit", "cell": cell})
                return events

            if (
                _side_of(c, r) == enemy_side
                and cell not in self.destroyed
                and self._cell_is_attackable_target(cell, enemy_side)
            ):
                events.extend(self._apply_hit(attacker, enemy_side, cell, defender_def_pos, splash=False))
                if not self._is_hq_cell(enemy_side, cell):
                    events.extend(self._apply_splash_hits(attacker, enemy_side, cell, defender_def_pos))
                return events
            c += dc
            r += dr
        return events

    def on_turn_change(self, new_turn, tokens_p1, tokens_p2):
        """Resolve the outgoing player's shots, then advance."""
        if new_turn not in (1, 2):
            return []
        if self.last_turn is None:
            self.last_turn = new_turn
            return []
        if new_turn == self.last_turn or self.winner:
            return []

        attacker = "p1" if self.last_turn == 1 else "p2"
        attacker_toks = tokens_p1 if attacker == "p1" else tokens_p2
        defender_toks = tokens_p2 if attacker == "p1" else tokens_p1
        def_pos = (
            defender_toks.get("def", {}).get("col"),
            defender_toks.get("def", {}).get("row"),
        )

        events = []
        print(f"\n[TURN] Resolving {attacker.upper()}'s attack:")
        for role in ("atk_a", "atk_b"):
            tok = attacker_toks.get(role) or {}
            start = (tok.get("col"), tok.get("row"))
            direction = tok.get("direction")
            print(f"  {role}: pos={start}  dir={direction}")
            if start[0] is None or direction is None:
                print("    → skipped (marker not visible / no direction)")
                continue
            shot_events = self._resolve_shot(attacker, start, direction, def_pos)
            for event in shot_events:
                print(f"    → {event['type']} {event.get('cell', '')}")
            events += shot_events

        self.last_turn = new_turn
        return events

    def snapshot(self):
        progress_p1 = self._progress_points("p1")
        progress_p2 = self._progress_points("p2")
        return {
            "destroyed": [list(c) for c in self.destroyed],
            "damage": {f"{c},{r}": v for (c, r), v in self.damage.items()},
            "soft_damage": {f"{c},{r}": v for (c, r), v in self.soft_damage.items()},
            "soft_gone": [list(c) for c in self.soft_gone],
            "score_p1_destroyed": self._enemy_destroyed_count("p1"),
            "score_p2_destroyed": self._enemy_destroyed_count("p2"),
            "score_p1_attrition": self._destroyed_resource_score("p1"),
            "score_p2_attrition": self._destroyed_resource_score("p2"),
            "progress_p1": progress_p1,
            "progress_p2": progress_p2,
            "attrition_threshold": ATTRITION_THRESHOLD,
            "tier_thresholds": list(TIER_THRESHOLDS),
            "tier_p1": self.tier_p1,
            "tier_p2": self.tier_p2,
            "nuke_used_p1": self.nuke_used_p1,
            "nuke_used_p2": self.nuke_used_p2,
            "winner": self.winner,
            "win_reason": self.win_reason,
            "hq_revealed": {k: list(v) for k, v in self.hq_reveal.items()},
        }


def make_hq(side: str, terrain: dict, rng: random.Random) -> tuple:
    """Pick a random resource cell as HQ for non-setup callers."""
    resources = terrain.get(f"{side}_resources", [])
    if not resources:
        raise RuntimeError(f"No resource cells defined for {side}")
    pick = rng.choice(resources)
    return (pick["col"], pick["row"])


def new_game(
    terrain: dict,
    seed: int | None = None,
    *,
    hq_p1: tuple[int, int] | None = None,
    hq_p2: tuple[int, int] | None = None,
) -> GameModel:
    rng = random.Random(seed)
    return GameModel(
        terrain=terrain,
        hq_p1=tuple(hq_p1) if hq_p1 is not None else make_hq("p1", terrain, rng),
        hq_p2=tuple(hq_p2) if hq_p2 is not None else make_hq("p2", terrain, rng),
        rng=rng,
    )
