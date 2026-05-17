"""
Game model for Defend Your Pixels.

Tracks all mutable game state and exposes:
  new_game(terrain, seed)  → GameModel
  model.on_turn_change(turn, p1, p2)   → events   (camera mode)
  model.apply_action(action, data)     → events   (no-camera mode)
  model.augment_tokens(side, tokens)   → enriched token dict
  model.snapshot()                     → dict for state["game"]
  model.get_token_positions()          → (p1_dict, p2_dict)
"""

import random
from typing import Optional, Dict, List, Tuple

GRID_SIZE          = 12
HARD_HP            = 4
SOFT_HP            = 2
ACTIVE_TOTAL       = 24

UPGRADE_1_KILLS    = 5    # attack token 1st star threshold
UPGRADE_2_KILLS    = 8    # attack token 2nd star threshold
NUKE_THRESHOLD     = 12   # nuke unlocks when ≤ this many active cells remain
DEF_UPGRADE_THRESH = 12   # defense 2nd star at ≤ this many active cells

DIR_MAP: Dict[str, Tuple[int, int]] = {
    "E":  ( 1,  0), "SE": ( 1,  1), "S":  ( 0,  1), "SW": (-1,  1),
    "W":  (-1,  0), "NW": (-1, -1), "N":  ( 0, -1), "NE": ( 1, -1),
}


def _is_p1(col: int, row: int) -> bool:
    return col + row < GRID_SIZE - 1


def _is_p2(col: int, row: int) -> bool:
    return col + row >= GRID_SIZE - 1


def _empty_token() -> dict:
    return {"col": None, "row": None, "direction": None, "stale": False}


class GameModel:
    def __init__(self, terrain: dict, seed: int):
        self.seed         = seed
        self.terrain_data = terrain

        # ── Active cells ──────────────────────────────────────────────────────
        self.active_cells: Dict[str, List[Tuple[int, int]]] = {
            "p1": [(r["col"], r["row"]) for r in terrain.get("p1_resources", [])],
            "p2": [(r["col"], r["row"]) for r in terrain.get("p2_resources", [])],
        }

        # ── Terrain HP ────────────────────────────────────────────────────────
        self.terrain_hp: Dict[Tuple[int, int], int] = {}
        for t in terrain.get("p1_hard", []) + terrain.get("p2_hard", []):
            self.terrain_hp[(t["col"], t["row"])] = HARD_HP
        for t in terrain.get("p1_soft", []) + terrain.get("p2_soft", []):
            self.terrain_hp[(t["col"], t["row"])] = SOFT_HP

        # ── Destroyed active cells ────────────────────────────────────────────
        self.destroyed: set = set()

        # ── Defense absorbed cells (reset when token moves) ───────────────────
        self.absorbed: Dict[str, set]              = {"p1": set(), "p2": set()}
        self.prev_def_pos: Dict[str, Optional[Tuple]] = {"p1": None, "p2": None}

        # ── Per-attack-token kill counts ──────────────────────────────────────
        self.kills: Dict[str, int] = {
            "p1_atk_a": 0, "p1_atk_b": 0,
            "p2_atk_a": 0, "p2_atk_b": 0,
        }

        # ── Nuke ──────────────────────────────────────────────────────────────
        self.nuke_used: Dict[str, bool] = {"p1": False, "p2": False}

        # ── HQ positions ─────────────────────────────────────────────────────
        raw1 = terrain.get("hq_p1")
        raw2 = terrain.get("hq_p2")
        self.hq_p1: Optional[Tuple] = tuple(raw1) if raw1 else None
        self.hq_p2: Optional[Tuple] = tuple(raw2) if raw2 else None
        self.hq_revealed: Dict[str, List[int]] = {}

        # ── Win state ─────────────────────────────────────────────────────────
        self.winner:     Optional[str] = None
        self.win_reason: str           = ""

        # ── Turn tracking (camera mode + no-camera mode) ─────────────────────
        self.prev_turn:    Optional[int] = None
        self.current_turn: Optional[int] = 1   # P1 goes first by default

        # ── Stored token positions (no-camera mode) ───────────────────────────
        self.stored_tokens: Dict[str, Dict] = {
            "p1": {r: _empty_token() for r in ("atk_a", "atk_b", "def")},
            "p2": {r: _empty_token() for r in ("atk_a", "atk_b", "def")},
        }

        # ── Last resolved events (consumed by broadcast) ──────────────────────
        self.last_events: list = []

        # ── Tier (kept for legacy state compatibility) ────────────────────────
        self.tier_p1 = 0
        self.tier_p2 = 0

    # ══════════════════════════════════════════════════════════════════════════
    # Internal helpers
    # ══════════════════════════════════════════════════════════════════════════

    def active_remaining(self, side: str) -> int:
        return sum(1 for c in self.active_cells.get(side, []) if c not in self.destroyed)

    def _def_zone(self, col: int, row: int) -> List[Tuple[int, int]]:
        return [
            (col + dc, row + dr)
            for dc in range(-1, 2)
            for dr in range(-1, 2)
            if 0 <= col + dc < GRID_SIZE and 0 <= row + dr < GRID_SIZE
        ]

    def _protecting_count(self, side: str, def_tok: dict) -> int:
        if not def_tok or def_tok.get("col") is None:
            return 0
        zone    = set(self._def_zone(def_tok["col"], def_tok["row"]))
        absorbed = self.absorbed.get(side, set())
        active   = set(self.active_cells.get(side, []))
        return sum(
            1 for c in zone
            if c in active and c not in self.destroyed and c not in absorbed
        )

    def _upgrade_level(self, token_key: str) -> int:
        k = self.kills.get(token_key, 0)
        if k >= UPGRADE_2_KILLS: return 2
        if k >= UPGRADE_1_KILLS: return 1
        return 0

    def _upgrade_fill(self, token_key: str) -> float:
        k   = self.kills.get(token_key, 0)
        lvl = self._upgrade_level(token_key)
        if lvl == 0: return k / UPGRADE_1_KILLS
        if lvl == 1: return (k - UPGRADE_1_KILLS) / (UPGRADE_2_KILLS - UPGRADE_1_KILLS)
        return 1.0

    def _build_defense_shields(self, side: str, def_tok: dict) -> set:
        """Build the current set of shielded cells for a defending side.
        Resets absorbed memory if the defense token has moved."""
        if not def_tok or def_tok.get("col") is None:
            return set()
        pos  = (def_tok["col"], def_tok["row"])
        prev = self.prev_def_pos[side]
        if prev != pos:
            self.absorbed[side]    = set()
            self.prev_def_pos[side] = pos
        absorbed = self.absorbed[side]
        return {c for c in self._def_zone(pos[0], pos[1]) if c not in absorbed}

    def _cast_ray(
        self, col: int, row: int, direction: str,
        attacking: str, max_hits: int
    ) -> List[dict]:
        """
        Walk the ray and return a list of step dicts:
          {"col", "row", "hit": bool, "type": "path"|"territory"|"terrain"|"hq"}

        Continues past hits up to max_hits (upgrade multi-cell destruction).
        Own terrain is transparent; only enemy terrain blocks.
        """
        dc, dr = DIR_MAP.get(direction, (0, 0))
        defending      = "p2" if attacking == "p1" else "p1"
        is_enemy_terr  = _is_p2 if attacking == "p1" else _is_p1
        enemy_active   = set(self.active_cells.get(defending, []))
        enemy_hq       = self.hq_p1 if defending == "p1" else self.hq_p2

        path: List[dict] = []
        hits  = 0
        c, r  = col + dc, row + dr

        while 0 <= c < GRID_SIZE and 0 <= r < GRID_SIZE:
            pos      = (c, r)
            in_enemy = is_enemy_terr(c, r)

            if pos in self.terrain_hp and in_enemy:
                path.append({"col": c, "row": r, "hit": True, "type": "terrain"})
                hits += 1
                if hits >= max_hits:
                    break
            elif pos in enemy_active and pos not in self.destroyed:
                path.append({"col": c, "row": r, "hit": True, "type": "territory"})
                hits += 1
                if hits >= max_hits:
                    break
            elif enemy_hq and pos == enemy_hq and in_enemy:
                path.append({"col": c, "row": r, "hit": True, "type": "hq"})
                hits += 1
                break
            else:
                path.append({"col": c, "row": r, "hit": False, "type": "path"})

            c += dc
            r += dr

        return path

    # ══════════════════════════════════════════════════════════════════════════
    # Core resolution
    # ══════════════════════════════════════════════════════════════════════════

    def resolve_attacks(self, attacking: str, p_atk: dict, p_def: dict) -> list:
        """Resolve both attack tokens for the attacking side. Returns event list."""
        if self.winner:
            return []

        defending = "p2" if attacking == "p1" else "p1"
        def_tok   = p_def.get("def") or {}
        shields   = self._build_defense_shields(defending, def_tok)
        events    = []
        successful = 0

        for role in ("atk_a", "atk_b"):
            tok = p_atk.get(role) or {}
            if tok.get("col") is None or not tok.get("direction"):
                continue

            token_key = f"{attacking}_{role}"
            level     = self._upgrade_level(token_key)
            max_hits  = 1 + level            # base=1, upgrade1=2, upgrade2=3

            path = self._cast_ray(tok["col"], tok["row"], tok["direction"],
                                  attacking, max_hits)

            # ── Emit animation event first so frontend can play it ────────────
            events.append({
                "type":      "ray_complete",
                "token":     token_key,
                "start":     [tok["col"], tok["row"]],
                "direction": tok["direction"],
                "path":      path,
            })

            # ── Apply each hit ────────────────────────────────────────────────
            for step in (s for s in path if s["hit"]):
                pos      = (step["col"], step["row"])
                hit_type = step["type"]

                if hit_type == "terrain":
                    if pos in self.terrain_hp:
                        self.terrain_hp[pos] -= 1
                        if self.terrain_hp[pos] <= 0:
                            del self.terrain_hp[pos]
                            events.append({"type": "soft_destroyed", "cell": list(pos)})
                        else:
                            events.append({
                                "type": "blocked_hard", "cell": list(pos),
                                "hp_remaining": self.terrain_hp[pos],
                            })

                elif hit_type == "territory":
                    if pos in shields:
                        shields.discard(pos)
                        self.absorbed[defending].add(pos)
                        events.append({"type": "cell_shielded", "cell": list(pos)})
                    elif pos not in self.destroyed:
                        self.destroyed.add(pos)
                        self.kills[token_key] += 1
                        successful += 1
                        events.append({
                            "type":  "cell_destroyed",
                            "cell":  list(pos),
                            "by":    attacking,
                            "token": token_key,
                        })
                        # If HQ was on this cell → instant win
                        enemy_hq = self.hq_p1 if defending == "p1" else self.hq_p2
                        if enemy_hq and pos == tuple(enemy_hq):
                            self._trigger_hq_win(attacking, defending, list(pos), events)

                elif hit_type == "hq":
                    if pos in shields:
                        shields.discard(pos)
                        self.absorbed[defending].add(pos)
                        events.append({"type": "cell_shielded", "cell": list(pos)})
                    else:
                        self._trigger_hq_win(attacking, defending, list(pos), events)

        events.append({
            "type":       "attack_result",
            "by":         attacking,
            "successful": successful,
        })

        # ── Attrition win check ───────────────────────────────────────────────
        if not self.winner and self.active_remaining(defending) <= 0:
            self.winner     = attacking
            self.win_reason = "attrition"
            events.append({"type": "attrition_win", "winner": attacking})

        return events

    def _trigger_hq_win(self, attacking, defending, pos, events):
        self.winner     = attacking
        self.win_reason = "hq_destroyed"
        self.hq_revealed[defending] = pos
        events.append({"type": "hq_destroyed", "cell": pos, "winner": attacking})

    # ══════════════════════════════════════════════════════════════════════════
    # Camera-mode entry point
    # ══════════════════════════════════════════════════════════════════════════

    def on_turn_change(self, turn, p1: dict, p2: dict) -> list:
        """Called every camera frame. Resolves attacks when the turn marker
        physically changes to the other player."""
        if turn == self.prev_turn or self.winner:
            self.current_turn = turn
            return []

        events = []
        if self.prev_turn is not None:
            prev = self.prev_turn
            p_atk = p1 if prev == 1 else p2
            p_def = p2 if prev == 1 else p1
            events = self.resolve_attacks(f"p{prev}", p_atk, p_def)

        self.prev_turn    = turn
        self.current_turn = turn
        self.last_events  = events
        return events

    # ══════════════════════════════════════════════════════════════════════════
    # No-camera action handler
    # ══════════════════════════════════════════════════════════════════════════

    def apply_action(self, action: str, data: dict) -> list:
        events = []

        if action == "place_token":
            side = data.get("side")
            role = data.get("role")
            if side in ("p1", "p2") and role in ("atk_a", "atk_b", "def"):
                self.stored_tokens[side][role] = {
                    "col":       data.get("col"),
                    "row":       data.get("row"),
                    "direction": data.get("direction"),
                    "stale":     False,
                }

        elif action == "rotate_token":
            side = data.get("side")
            role = data.get("role")
            if side in ("p1", "p2") and role in ("atk_a", "atk_b"):
                self.stored_tokens[side][role]["direction"] = data.get("direction")

        elif action == "end_turn":
            turn = data.get("player")
            if turn and not self.winner:
                other = 2 if turn == 1 else 1
                p_atk = self.stored_tokens[f"p{turn}"]
                p_def = self.stored_tokens[f"p{other}"]
                events = self.resolve_attacks(f"p{turn}", p_atk, p_def)
                self.current_turn = other
                self.prev_turn    = turn

        elif action in ("fire_nuke", "trigger_nuke"):
            side = data.get("side")
            # Support both {col, row} and {position: {x, y}} shapes
            pos  = data.get("position") or {}
            col  = data.get("col") if data.get("col") is not None else pos.get("x")
            row  = data.get("row") if data.get("row") is not None else pos.get("y")
            if side and col is not None and row is not None:
                events = self._fire_nuke(side, int(col), int(row))

        elif action == "set_hq":
            side = data.get("side")
            col  = data.get("col")
            row  = data.get("row")
            if col is not None and row is not None:
                if side == "p1": self.hq_p1 = (col, row)
                if side == "p2": self.hq_p2 = (col, row)

        self.last_events = events
        return events

    # ══════════════════════════════════════════════════════════════════════════
    # Nuke
    # ══════════════════════════════════════════════════════════════════════════

    def _fire_nuke(self, side: str, target_col: int, target_row: int) -> list:
        if self.nuke_used.get(side) or self.winner:
            return []
        if self.active_remaining(side) > NUKE_THRESHOLD:
            return []

        defending    = "p2" if side == "p1" else "p1"
        enemy_active = set(self.active_cells.get(defending, []))

        # Collect valid 3×3 blast candidates on enemy side
        candidates = [
            (c, r)
            for dc in range(-1, 2)
            for dr in range(-1, 2)
            for c, r in [(target_col + dc, target_row + dr)]
            if 0 <= c < GRID_SIZE and 0 <= r < GRID_SIZE
            and (c, r) in enemy_active and (c, r) not in self.destroyed
        ]
        if not candidates:
            return []

        rng   = random.Random(self.seed + len(self.destroyed))
        count = rng.randint(1, len(candidates))
        nuked = rng.sample(candidates, count)

        for pos in nuked:
            self.destroyed.add(pos)

        self.nuke_used[side] = True
        events = [{
            "type":   "nuke_triggered",
            "by":     side,
            "center": [target_col, target_row],
            "cells":  [list(p) for p in nuked],
        }]

        if not self.winner and self.active_remaining(defending) <= 0:
            self.winner     = side
            self.win_reason = "attrition"
            events.append({"type": "attrition_win", "winner": side})

        return events

    # ══════════════════════════════════════════════════════════════════════════
    # Token augmentation (merges camera/stored positions with model data)
    # ══════════════════════════════════════════════════════════════════════════

    def augment_tokens(self, side: str, tokens: dict) -> dict:
        result = {}

        for role in ("atk_a", "atk_b"):
            tok       = dict(tokens.get(role) or {})
            token_key = f"{side}_{role}"
            tok["kills"]        = self.kills.get(token_key, 0)
            tok["upgrade"]      = self._upgrade_level(token_key)
            tok["upgrade_fill"] = self._upgrade_fill(token_key)
            result[role] = tok

        def_tok = dict(tokens.get("def") or {})
        active_rem    = self.active_remaining(side)
        def_upgrade   = 1 if active_rem <= DEF_UPGRADE_THRESH else 0
        def_fill      = min(1.0, (ACTIVE_TOTAL - active_rem) / 12.0)
        def_tok["protecting"]   = self._protecting_count(side, def_tok)
        def_tok["upgrade"]      = def_upgrade
        def_tok["upgrade_fill"] = def_fill
        result["def"] = def_tok

        result["active_remaining"] = active_rem
        result["active_total"]     = ACTIVE_TOTAL
        result["nuke_available"]   = (
            active_rem <= NUKE_THRESHOLD and not self.nuke_used.get(side, False)
        )
        result["nuke_used"] = self.nuke_used.get(side, False)
        return result

    def get_token_positions(self):
        """Return stored (p1, p2) token dicts for no-camera broadcast."""
        return self.stored_tokens["p1"], self.stored_tokens["p2"]

    # ══════════════════════════════════════════════════════════════════════════
    # State snapshot  (goes into state["game"])
    # ══════════════════════════════════════════════════════════════════════════

    def snapshot(self) -> dict:
        # Soft terrain that's been fully destroyed
        orig_soft = {
            (t["col"], t["row"])
            for t in self.terrain_data.get("p1_soft", []) +
                      self.terrain_data.get("p2_soft", [])
        }
        soft_gone = [list(p) for p in orig_soft if p not in self.terrain_hp]

        # Terrain damage dict: only cells that took partial damage
        orig_hp = {}
        for t in self.terrain_data.get("p1_hard", []) + self.terrain_data.get("p2_hard", []):
            orig_hp[(t["col"], t["row"])] = HARD_HP
        for t in self.terrain_data.get("p1_soft", []) + self.terrain_data.get("p2_soft", []):
            orig_hp[(t["col"], t["row"])] = SOFT_HP
        damage = {
            f"{p[0]},{p[1]}": hp
            for p, hp in self.terrain_hp.items()
            if hp < orig_hp.get(p, 0)
        }

        return {
            "winner":     self.winner,
            "win_reason": self.win_reason,
            "hq_revealed": self.hq_revealed,
            "destroyed":  [list(p) for p in self.destroyed],
            "damage":     damage,
            "soft_gone":  soft_gone,
            "active_cells": {
                "p1": [list(c) for c in self.active_cells.get("p1", [])],
                "p2": [list(c) for c in self.active_cells.get("p2", [])],
            },
            "tier_p1": self.tier_p1,
            "tier_p2": self.tier_p2,
            "kills":   dict(self.kills),
            "score_p1_attrition": ACTIVE_TOTAL - self.active_remaining("p1"),
            "score_p2_attrition": ACTIVE_TOTAL - self.active_remaining("p2"),
            "attrition_threshold": ACTIVE_TOTAL,
        }


def new_game(terrain: dict, seed: int = 0) -> GameModel:
    return GameModel(terrain, seed)
