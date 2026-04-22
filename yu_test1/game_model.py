"""
Authoritative game state for Old Mick Against the Mob.

Tracks per-cell damage, the hidden HQs, turn number, tier levels, and
win conditions. Turn-resolution is triggered externally — the server
calls `on_turn_change(new_turn)` whenever the physical turn marker
flips.

Rules implemented:
  - Each cell has 1 HP by default (2 HP if inside owner's DEF zone).
  - ATK shot = straight line, hits first ENEMY-side cell, deals 1 dmg.
  - Soft terrain: 2 HP then disappears (no longer blocks).
  - Hard terrain: permanently blocks attacks (never destroyed).
  - Hidden HQ: one random cell per side, unknown to both players.
    Destroying the enemy HQ is an INSTANT WIN.
  - Attrition: destroy 30 enemy cells to win.
"""

import random
from dataclasses import dataclass, field

GRID_COLS, GRID_ROWS = 12, 12
ATTRITION_THRESHOLD  = 30
DEF_ZONE_RADIUS_T1   = 1   # 3×3
DEF_ZONE_RADIUS_T2   = 2   # 5×5 after tier 2

DIR_VEC = {
    "E":  ( 1,  0), "SE": ( 1,  1), "S":  ( 0,  1), "SW": (-1,  1),
    "W":  (-1,  0), "NW": (-1, -1), "N":  ( 0, -1), "NE": ( 1, -1),
}


def _side_of(c, r):
    """Which player's territory a cell belongs to. None = fence line."""
    if c + r <  11: return "p1"
    if c + r >  11: return "p2"
    return None


@dataclass
class GameModel:
    terrain:     dict                           # from terrain_gen
    hq_p1:       tuple                          # (col, row)
    hq_p2:       tuple                          # (col, row)
    tier_p1:     int = 1
    tier_p2:     int = 1
    damage:      dict = field(default_factory=dict)   # (c,r) → dmg count
    destroyed:   set  = field(default_factory=set)    # set of (c,r)
    soft_damage: dict = field(default_factory=dict)   # (c,r) → dmg count
    soft_gone:   set  = field(default_factory=set)    # destroyed soft terrain
    last_turn:   int | None = None
    winner:      str | None = None
    win_reason:  str | None = None
    hq_reveal:   dict = field(default_factory=dict)   # {"p1": (c,r)} when destroyed

    # ── HP / zone helpers ────────────────────────────────────────────────

    def _def_zone(self, player: str, def_pos):
        if def_pos is None or def_pos[0] is None:
            return set()
        tier = self.tier_p1 if player == "p1" else self.tier_p2
        rad  = DEF_ZONE_RADIUS_T2 if tier >= 2 else DEF_ZONE_RADIUS_T1
        dc, dr = def_pos
        return {(dc + x, dr + y)
                for x in range(-rad, rad + 1) for y in range(-rad, rad + 1)
                if 0 <= dc + x < GRID_COLS and 0 <= dr + y < GRID_ROWS}

    def _cell_required_hp(self, cell, defender, def_pos):
        return 2 if cell in self._def_zone(defender, def_pos) else 1

    def _cell_is_hard(self, cell):
        for g in ("p1_hard", "p2_hard"):
            for t in self.terrain[g]:
                if (t["col"], t["row"]) == cell: return True
        return False

    def _cell_is_soft(self, cell):
        for g in ("p1_soft", "p2_soft"):
            for t in self.terrain[g]:
                if (t["col"], t["row"]) == cell and tuple(cell) not in self.soft_gone:
                    return True
        return False

    def _is_target(self, cell, side):
        """Only cells flagged as targets for this side are attackable."""
        for t in self.terrain.get(f"{side}_targets", []):
            if (t["col"], t["row"]) == cell:
                return True
        return False

    # ── Attack resolution ────────────────────────────────────────────────

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

            # Only enemy-side cells take damage; own cells / fence line are skipped.
            # Non-target enemy cells let the ray pass through (safe zones).
            if (_side_of(c, r) == enemy_side and cell not in self.destroyed
                    and self._is_target(cell, enemy_side)):
                req = self._cell_required_hp(cell, enemy_side, defender_def_pos)
                self.damage[cell] = self.damage.get(cell, 0) + 1
                if self.damage[cell] >= req:
                    self.destroyed.add(cell)
                    events.append({"type": "cell_destroyed", "cell": cell, "side": enemy_side})
                    # HQ instant-win check
                    hq = self.hq_p1 if enemy_side == "p1" else self.hq_p2
                    if tuple(cell) == tuple(hq):
                        self.hq_reveal[enemy_side] = list(cell)
                        self.winner = attacker
                        self.win_reason = ("homestead" if enemy_side == "p1"
                                           else "nest") + "_destroyed"
                        events.append({"type": "hq_destroyed", "side": enemy_side})
                    elif self._enemy_destroyed_count(enemy_side) >= ATTRITION_THRESHOLD:
                        self.winner = attacker
                        self.win_reason = "attrition"
                        events.append({"type": "attrition_win", "side": enemy_side})
                else:
                    events.append({"type": "cell_damaged", "cell": cell})
                return events
            c += dc; r += dr
        return events

    def _enemy_destroyed_count(self, side):
        return sum(1 for cell in self.destroyed if _side_of(*cell) == side)

    # ── Turn handler (called by server when turn marker flips) ───────────

    def on_turn_change(self, new_turn, tokens_p1, tokens_p2):
        """Resolve the OUTGOING player's shots, then advance."""
        if new_turn not in (1, 2):
            return []
        if self.last_turn is None:
            self.last_turn = new_turn
            return []
        if new_turn == self.last_turn or self.winner:
            return []

        # Resolve the player whose turn just ended
        attacker       = "p1" if self.last_turn == 1 else "p2"
        attacker_toks  = tokens_p1 if attacker == "p1" else tokens_p2
        defender_toks  = tokens_p2 if attacker == "p1" else tokens_p1
        def_pos        = (defender_toks.get("def", {}).get("col"),
                          defender_toks.get("def", {}).get("row"))

        events = []
        print(f"\n[TURN] Resolving {attacker.upper()}'s attack:")
        for role in ("atk_a", "atk_b"):
            tok = attacker_toks.get(role) or {}
            start = (tok.get("col"), tok.get("row"))
            direction = tok.get("direction")
            print(f"  {role}: pos={start}  dir={direction}")
            if start[0] is None or direction is None:
                print(f"    → skipped (marker not visible / no direction)")
                continue
            shot_events = self._resolve_shot(attacker, start, direction, def_pos)
            for ev in shot_events:
                print(f"    → {ev['type']} {ev.get('cell', '')}")
            events += shot_events

        self.last_turn = new_turn
        return events

    # ── Serialisation for the client ─────────────────────────────────────

    def snapshot(self):
        return {
            "destroyed":    [list(c) for c in self.destroyed],
            "damage":       {f"{c},{r}": v for (c, r), v in self.damage.items()},
            "soft_damage":  {f"{c},{r}": v for (c, r), v in self.soft_damage.items()},
            "soft_gone":    [list(c) for c in self.soft_gone],
            "score_p1_destroyed": self._enemy_destroyed_count("p1"),  # cells P2 destroyed
            "score_p2_destroyed": self._enemy_destroyed_count("p2"),  # cells P1 destroyed
            "attrition_threshold": ATTRITION_THRESHOLD,
            "tier_p1":      self.tier_p1,
            "tier_p2":      self.tier_p2,
            "winner":       self.winner,
            "win_reason":   self.win_reason,
            "hq_revealed":  {k: list(v) for k, v in self.hq_reveal.items()},
            # Note: hq_p1 / hq_p2 NOT sent while hidden (Q3 choice C)
        }


# ─── Factory ─────────────────────────────────────────────────────────────────

def make_hq(side: str, terrain: dict, rng: random.Random) -> tuple:
    """Pick a random TARGET cell as HQ (so HQ is always reachable by attacks)."""
    targets = terrain.get(f"{side}_targets", [])
    if not targets:
        raise RuntimeError(f"No target cells defined for {side}")
    pick = rng.choice(targets)
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
    )
