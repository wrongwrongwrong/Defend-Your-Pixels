"""
Authoritative game state for Old Mick Against the Mob.

Tracks per-cell damage, hidden HQs, scored resource destruction, tier levels, and
win conditions. Shot resolution is triggered externally when the live runtime
submits one side's turn.
"""

import random
from dataclasses import dataclass, field

GRID_COLS, GRID_ROWS = 12, 12
TIER_THRESHOLDS = (4, 8, 12, 16)
ATK_TIER_THRESHOLDS = (4, 8)
DEF_ZONE_RADIUS_T1 = 1
DEF_ZONE_RADIUS_T2 = 2
DEF_UPGRADE_REMAINING_CELLS = 12
NUKE_UNLOCK_REMAINING_CELLS = 8
NUKE_RESOURCE_HITS = 5
SOFT_TERRAIN_HP = 2
HARD_TERRAIN_HP = 5

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
    hard_damage: dict = field(default_factory=dict)
    hard_gone: set = field(default_factory=set)
    soft_damage: dict = field(default_factory=dict)
    soft_gone: set = field(default_factory=set)
    atk_destroyed_counts: dict = field(default_factory=lambda: {
        "p1": {"atk_a": 0, "atk_b": 0},
        "p2": {"atk_a": 0, "atk_b": 0},
    })
    last_turn: int | None = None
    winner: str | None = None
    win_reason: str | None = None
    hq_reveal: dict = field(default_factory=dict)
    nuke_used_p1: bool = False
    nuke_used_p2: bool = False
    def_anchor_cells: dict = field(default_factory=lambda: {"p1": None, "p2": None})
    def_consumed_cells: dict = field(default_factory=lambda: {"p1": set(), "p2": set()})

    def _def_zone(self, player: str, def_pos):
        if def_pos is None or def_pos[0] is None:
            return set()
        rad = DEF_ZONE_RADIUS_T2 if self._def_tier(player) >= 1 else DEF_ZONE_RADIUS_T1
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

    def _cell_required_hp(self, cell, defender, *, def_protection_active: bool = False):
        base_hp = self._resource_base_hp(defender, cell)
        return base_hp + (1 if def_protection_active else 0)

    def _normalize_def_anchor(self, def_pos) -> tuple[int, int] | None:
        if def_pos is None:
            return None
        col, row = def_pos
        if not isinstance(col, int) or not isinstance(row, int):
            return None
        return (col, row)

    def _consume_def_protection(self, side: str, cell: tuple[int, int], def_pos) -> bool:
        anchor = self._normalize_def_anchor(def_pos)
        current_anchor = self.def_anchor_cells.get(side)
        if anchor != current_anchor:
            self.def_anchor_cells[side] = anchor
            self.def_consumed_cells[side] = set()

        if anchor is None or cell not in self._def_zone(side, anchor):
            return False

        consumed = self.def_consumed_cells.setdefault(side, set())
        if cell in consumed:
            return False

        consumed.add(cell)
        return True

    def _cell_is_hard(self, cell):
        for group in ("p1_hard", "p2_hard"):
            for tile in self.terrain[group]:
                if (tile["col"], tile["row"]) == cell and tuple(cell) not in self.hard_gone:
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

    def _resource_cell_total(self, side: str) -> int:
        return len(self.terrain.get(f"{side}_resources", []))

    def _destroyed_resource_cells(self, side: str) -> int:
        return self._enemy_destroyed_resource_count(side)

    def _remaining_resource_cells(self, side: str) -> int:
        return max(0, self._resource_cell_total(side) - self._destroyed_resource_cells(side))

    def _def_tier(self, side: str) -> int:
        return 1 if self._remaining_resource_cells(side) <= DEF_UPGRADE_REMAINING_CELLS else 0

    def _attrition_threshold(self, side: str) -> int:
        return self._resource_cell_total(side)

    def _progress_points(self, player: str) -> int:
        enemy_side = "p2" if player == "p1" else "p1"
        return self._destroyed_resource_cells(enemy_side)

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

    def _atk_destroyed_count(self, attacker: str, role: str) -> int:
        return int(self.atk_destroyed_counts.get(attacker, {}).get(role, 0))

    def _atk_tier(self, attacker: str, role: str) -> int:
        destroyed_count = self._atk_destroyed_count(attacker, role)
        tier = 0
        for index, threshold in enumerate(ATK_TIER_THRESHOLDS, start=1):
            if destroyed_count >= threshold:
                tier = index
        return tier

    def _record_atk_destroyed(self, attacker: str, role: str, cell: tuple[int, int], enemy_side: str) -> None:
        if role not in {"atk_a", "atk_b"} or self._is_hq_cell(enemy_side, cell) or not self._is_resource_cell(cell, enemy_side):
            return
        side_counts = self.atk_destroyed_counts.setdefault(attacker, {"atk_a": 0, "atk_b": 0})
        side_counts[role] = int(side_counts.get(role, 0)) + 1

    def _nuke_used(self, player: str) -> bool:
        return self.nuke_used_p1 if player == "p1" else self.nuke_used_p2

    def _nuke_available(self, player: str) -> bool:
        return self._remaining_resource_cells(player) <= NUKE_UNLOCK_REMAINING_CELLS and not self._nuke_used(player)

    def _set_nuke_used(self, player: str) -> None:
        if player == "p1":
            self.nuke_used_p1 = True
        else:
            self.nuke_used_p2 = True

    def _valid_splash_targets(self, enemy_side: str, primary_cell: tuple[int, int]) -> list[tuple[int, int]]:
        c, r = primary_cell
        candidates: list[tuple[int, int]] = []
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if dc == 0 and dr == 0:
                    continue
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

    def _apply_hit(self, attacker: str, attacker_role: str | None, enemy_side: str, cell: tuple[int, int], defender_def_pos, *, splash: bool = False) -> list[dict]:
        def_protection_active = self._consume_def_protection(enemy_side, cell, defender_def_pos)
        req = self._cell_required_hp(cell, enemy_side, def_protection_active=def_protection_active)
        self.damage[cell] = self.damage.get(cell, 0) + 1
        resource_value = self._resource_value(enemy_side, cell)
        if self.damage[cell] >= req:
            self.destroyed.add(cell)
            if attacker_role is not None:
                self._record_atk_destroyed(attacker, attacker_role, cell, enemy_side)
            events = [{
                "type": "cell_destroyed",
                "cell": cell,
                "side": enemy_side,
                "value": resource_value,
                "splash": splash,
                "attacker_role": attacker_role,
            }]
            if self._is_hq_cell(enemy_side, cell):
                self.hq_reveal[enemy_side] = list(cell)
                self.winner = attacker
                self.win_reason = ("homestead" if enemy_side == "p1" else "nest") + "_destroyed"
                events.append({"type": "hq_destroyed", "side": enemy_side})
            else:
                self._sync_tiers_from_progress()
                if self._destroyed_resource_cells(enemy_side) >= self._attrition_threshold(enemy_side):
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

    def _apply_splash_hits(self, attacker: str, attacker_role: str, enemy_side: str, primary_cell: tuple[int, int], defender_def_pos) -> list[dict]:
        splash_count = self._atk_tier(attacker, attacker_role)
        if splash_count <= 0 or self.winner:
            return []
        candidates = self._valid_splash_targets(enemy_side, primary_cell)
        if not candidates:
            return []
        chosen = self.rng.sample(candidates, k=min(splash_count, len(candidates)))
        events: list[dict] = []
        for cell in chosen:
            events.extend(self._apply_hit(attacker, attacker_role, enemy_side, cell, defender_def_pos, splash=True))
            if self.winner:
                break
        return events

    def trigger_nuke(self, attacker: str, center: tuple[int, int]) -> list[dict]:
        if self.winner:
            return []
        if attacker not in {"p1", "p2"}:
            return []
        if not self._nuke_available(attacker):
            return []

        enemy_side = "p2" if attacker == "p1" else "p1"
        if _side_of(*center) != enemy_side:
            return []

        self._set_nuke_used(attacker)
        events: list[dict] = [{"type": "nuke_triggered", "side": attacker, "center": list(center)}]

        cx, cy = center
        resource_candidates: list[tuple[int, int]] = []
        for row in range(cy - 1, cy + 2):
            for col in range(cx - 1, cx + 2):
                if not (0 <= col < GRID_COLS and 0 <= row < GRID_ROWS):
                    continue
                cell = (col, row)
                if _side_of(col, row) != enemy_side:
                    continue
                if self._cell_is_hard(cell):
                    self.hard_damage[cell] = max(self.hard_damage.get(cell, 0), HARD_TERRAIN_HP)
                    self.hard_gone.add(cell)
                    events.append({"type": "hard_destroyed", "cell": cell, "nuke": True})
                    continue
                if self._cell_is_soft(cell):
                    self.soft_damage[cell] = max(self.soft_damage.get(cell, 0), SOFT_TERRAIN_HP)
                    self.soft_gone.add(cell)
                    events.append({"type": "soft_destroyed", "cell": cell, "nuke": True})
                    continue
                if cell in self.destroyed:
                    continue
                if self._is_hq_cell(enemy_side, cell):
                    continue
                if self._is_resource_cell(cell, enemy_side):
                    resource_candidates.append(cell)

        for cell in self.rng.sample(resource_candidates, k=min(NUKE_RESOURCE_HITS, len(resource_candidates))):
            self.damage[cell] = max(self.damage.get(cell, 0), self._cell_required_hp(cell, enemy_side, def_protection_active=False))
            self.destroyed.add(cell)
            events.append({
                "type": "cell_destroyed",
                "cell": cell,
                "side": enemy_side,
                "value": self._resource_value(enemy_side, cell),
                "nuke": True,
            })

        self._sync_tiers_from_progress()
        if self._destroyed_resource_cells(enemy_side) >= self._attrition_threshold(enemy_side):
            self.winner = attacker
            self.win_reason = "attrition"
            events.append({"type": "attrition_win", "side": enemy_side})
        return events

    def _resolve_shot(self, attacker: str, attacker_role: str, start, direction: str, defender_def_pos):
        """Fire one ray. Returns (events, path) for this shot."""
        if start[0] is None or direction not in DIR_VEC:
            return [], []
        enemy_side = "p2" if attacker == "p1" else "p1"
        dc, dr = DIR_VEC[direction]
        c, r = start[0] + dc, start[1] + dr
        events = []
        path = []

        while 0 <= c < GRID_COLS and 0 <= r < GRID_ROWS:
            cell = (c, r)

            if self._cell_is_hard(cell):
                path.append({"col": c, "row": r, "hit": True, "type": "terrain"})
                self.hard_damage[cell] = self.hard_damage.get(cell, 0) + 1
                if self.hard_damage[cell] >= HARD_TERRAIN_HP:
                    self.hard_gone.add(cell)
                    events.append({"type": "hard_destroyed", "cell": cell})
                else:
                    events.append({
                        "type": "hard_hit",
                        "cell": cell,
                        "remaining_hp": HARD_TERRAIN_HP - self.hard_damage[cell],
                        "required_hp": HARD_TERRAIN_HP,
                    })
                return events, path
            if self._cell_is_soft(cell):
                path.append({"col": c, "row": r, "hit": True, "type": "terrain"})
                self.soft_damage[cell] = self.soft_damage.get(cell, 0) + 1
                if self.soft_damage[cell] >= SOFT_TERRAIN_HP:
                    self.soft_gone.add(cell)
                    events.append({"type": "soft_destroyed", "cell": cell})
                else:
                    events.append({
                        "type": "soft_hit",
                        "cell": cell,
                        "remaining_hp": SOFT_TERRAIN_HP - self.soft_damage[cell],
                        "required_hp": SOFT_TERRAIN_HP,
                    })
                return events, path

            if (
                _side_of(c, r) == enemy_side
                and cell not in self.destroyed
                and self._cell_is_attackable_target(cell, enemy_side)
            ):
                path.append({"col": c, "row": r, "hit": True, "type": "territory"})
                events.extend(self._apply_hit(attacker, attacker_role, enemy_side, cell, defender_def_pos, splash=False))
                if any(event.get("type") == "hq_destroyed" for event in events):
                    path[-1]["type"] = "hq"
                if not self._is_hq_cell(enemy_side, cell):
                    events.extend(self._apply_splash_hits(attacker, attacker_role, enemy_side, cell, defender_def_pos))
                return events, path
            path.append({"col": c, "row": r, "hit": False, "type": "path"})
            c += dc
            r += dr
        return events, path

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
        events = self.resolve_side_attack(attacker, tokens_p1, tokens_p2)

        self.last_turn = new_turn
        return events

    def resolve_side_attack(self, attacker: str, tokens_p1, tokens_p2):
        """Resolve one submitted side's attacks without relying on turn flips."""
        if attacker not in {"p1", "p2"} or self.winner:
            return []

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
            shot_events, path = self._resolve_shot(attacker, role, start, direction, def_pos)
            events.append({
                "type": "ray_complete",
                "token": f"{attacker}_{role}",
                "start": list(start),
                "direction": direction,
                "path": path,
            })
            for event in shot_events:
                print(f"    → {event['type']} {event.get('cell', '')}")
            events += shot_events

        events.append({
            "type": "attack_result",
            "by": attacker,
            "successful": sum(1 for event in events if event.get("type") == "cell_destroyed"),
        })
        return events

    def snapshot(self):
        progress_p1 = self._progress_points("p1")
        progress_p2 = self._progress_points("p2")
        atk_tiers = {
            side: {role: self._atk_tier(side, role) for role in ("atk_a", "atk_b")}
            for side in ("p1", "p2")
        }
        return {
            "destroyed": [list(c) for c in self.destroyed],
            "damage": {f"{c},{r}": v for (c, r), v in self.damage.items()},
            "def_anchor_cells": {
                side: list(anchor) if anchor is not None else None
                for side, anchor in self.def_anchor_cells.items()
            },
            "def_consumed_cells": {
                side: [list(cell) for cell in sorted(cells)]
                for side, cells in self.def_consumed_cells.items()
            },
            "hard_damage": {f"{c},{r}": v for (c, r), v in self.hard_damage.items()},
            "hard_terrain_hp": HARD_TERRAIN_HP,
            "hard_gone": [list(c) for c in self.hard_gone],
            "soft_damage": {f"{c},{r}": v for (c, r), v in self.soft_damage.items()},
            "soft_terrain_hp": SOFT_TERRAIN_HP,
            "soft_gone": [list(c) for c in self.soft_gone],
            "score_p1_destroyed": self._enemy_destroyed_count("p1"),
            "score_p2_destroyed": self._enemy_destroyed_count("p2"),
            "score_p1_attrition": self._destroyed_resource_score("p1"),
            "score_p2_attrition": self._destroyed_resource_score("p2"),
            "score_p1_destroyed_cells": self._destroyed_resource_cells("p1"),
            "score_p2_destroyed_cells": self._destroyed_resource_cells("p2"),
            "score_p1_remaining_cells": self._remaining_resource_cells("p1"),
            "score_p2_remaining_cells": self._remaining_resource_cells("p2"),
            "def_tier_p1": self._def_tier("p1"),
            "def_tier_p2": self._def_tier("p2"),
            "def_upgrade_remaining_cells": DEF_UPGRADE_REMAINING_CELLS,
            "atk_destroyed_counts": {
                side: {role: self._atk_destroyed_count(side, role) for role in ("atk_a", "atk_b")}
                for side in ("p1", "p2")
            },
            "atk_tiers": atk_tiers,
            "atk_tier_thresholds": list(ATK_TIER_THRESHOLDS),
            "progress_p1": progress_p1,
            "progress_p2": progress_p2,
            "attrition_threshold": self._attrition_threshold("p1"),
            "resource_cell_total": self._resource_cell_total("p1"),
            "tier_thresholds": list(TIER_THRESHOLDS),
            "tier_p1": self.tier_p1,
            "tier_p2": self.tier_p2,
            "nuke_used_p1": self.nuke_used_p1,
            "nuke_used_p2": self.nuke_used_p2,
            "nuke_available_p1": self._nuke_available("p1"),
            "nuke_available_p2": self._nuke_available("p2"),
            "nuke_unlock_remaining_cells": NUKE_UNLOCK_REMAINING_CELLS,
            "nuke_resource_hits": NUKE_RESOURCE_HITS,
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
