"""
Game state engine: rules, resolution, win conditions.
Grid is 12x12. Board split along the anti-diagonal (top-right → bottom-left).
P1 (farmer/green) owns the upper-left  triangle: col + row <  GRID_SIZE - 1.
P2 (emu/orange)   owns the lower-right triangle: col + row >= GRID_SIZE - 1.
"""

import math
import random
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple, Set
from enum import Enum

GRID_SIZE = 12
CELLS_PER_PLAYER = 24   # active wheat paddocks / feeding grounds per side
HARD_TERRAIN_PER_SIDE = 2
SOFT_TERRAIN_PER_SIDE = 3

# Corner cells are forbidden for HQ placement and terrain
CORNER_CELLS = frozenset({(0, 0), (GRID_SIZE - 1, GRID_SIZE - 1)})

class Direction(Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    DIAGONAL = "diagonal"

class TerrainType(Enum):
    HARD = "hard"    # 4 hits to destroy
    SOFT = "soft"    # 2 hits to destroy

class Phase(Enum):
    SIDE_SELECTION = "side_selection"
    TUTORIAL       = "tutorial"
    HQ_PLACEMENT   = "hq_placement"
    PLANNING       = "planning"
    RESOLVE        = "resolve"
    GAME_OVER      = "game_over"

@dataclass
class TerrainCell:
    terrain_type: TerrainType
    hp: int = 0

    def __post_init__(self):
        if self.terrain_type == TerrainType.SOFT:
            self.hp = 2
        elif self.terrain_type == TerrainType.HARD:
            self.hp = 4

@dataclass
class Token:
    player: int          # 1 or 2
    role: str            # "attack_a", "attack_b", "defense"
    col: int = -1
    row: int = -1
    direction: Optional[Direction] = None
    valid: bool = True

@dataclass
class GameState:
    phase: Phase = Phase.SIDE_SELECTION
    current_player: int = 1
    # Which physical player is on which narrative side
    # "farmer" = Old Mick's side, "emu" = The Mob's side
    player_sides: Dict[int, str] = field(default_factory=lambda: {1: "farmer", 2: "emu"})
    winner: Optional[int] = None
    win_reason: str = ""

    # 12x12 terrain grid: None or TerrainCell
    terrain: Dict[Tuple[int,int], TerrainCell] = field(default_factory=dict)

    # territory damage: set of (col,row) cells destroyed
    destroyed_cells: set = field(default_factory=set)

    # hidden bases: {player: (col, row)} — set during HQ_PLACEMENT, never revealed
    hidden_bases: Dict[int, Optional[Tuple[int,int]]] = field(default_factory=lambda: {1: None, 2: None})
    # once locked, HQ cannot be moved
    hq_locked: Dict[int, bool] = field(default_factory=lambda: {1: False, 2: False})

    # defense shield state: {(col,row): bool} — True = shield active
    defense_shields: Dict[Tuple[int,int], bool] = field(default_factory=dict)

    # absorbed_cells[pid]: set of cells whose shields were consumed this placement
    # Resets when the defense token moves to a new position
    absorbed_cells: Dict[int, set] = field(default_factory=lambda: {1: set(), 2: set()})

    # Previous defense token positions to detect movement
    prev_defense_positions: Dict[int, Optional[Tuple[int,int]]] = field(
        default_factory=lambda: {1: None, 2: None})

    tokens: Dict[str, Token] = field(default_factory=dict)

    # terrain confirmed per player
    terrain_confirmed: Dict[int, bool] = field(default_factory=lambda: {1: False, 2: False})

    # Active territory cells per player (wheat paddocks / feeding grounds)
    active_cells: Dict[int, List[Tuple[int,int]]] = field(default_factory=dict)

    last_attack_results: list = field(default_factory=list)


def angle_to_direction(angle_deg: float) -> Direction:
    """Snap marker rotation angle to one of 3 discrete directions."""
    angle = angle_deg % 180
    if angle < 0:
        angle += 180

    THRESHOLD = 22.5
    if angle <= THRESHOLD or angle >= (180 - THRESHOLD):
        return Direction.HORIZONTAL
    elif abs(angle - 90) <= THRESHOLD:
        return Direction.VERTICAL
    else:
        return Direction.DIAGONAL


def generate_active_cells(seed=None) -> Dict[int, List[Tuple[int,int]]]:
    """Randomly pick CELLS_PER_PLAYER cells from each player's territory,
    excluding the anti-diagonal fence line (col + row == GRID_SIZE - 1).
    """
    rng = random.Random(seed)
    result = {}
    for pid in [1, 2]:
        pool = [
            (c, r) for c in range(GRID_SIZE) for r in range(GRID_SIZE)
            if is_player_territory(pid, c, r)
            and abs((c + r) - (GRID_SIZE - 1)) > 1   # exclude 3-cell fence buffer
            and (c, r) not in CORNER_CELLS
        ]
        result[pid] = rng.sample(pool, min(CELLS_PER_PLAYER, len(pool)))
    return result


def generate_terrain(active_cells: Dict[int, List[Tuple[int,int]]], seed=None) -> Dict[Tuple[int,int], TerrainCell]:
    """Randomly place HARD_TERRAIN_PER_SIDE hard + SOFT_TERRAIN_PER_SIDE soft terrain
    cells in each player's territory, avoiding active_cells, corner cells, and the
    fence buffer row.
    """
    rng = random.Random(seed)
    active_set = set()
    for cells in active_cells.values():
        active_set.update(map(tuple, cells))

    terrain: Dict[Tuple[int,int], TerrainCell] = {}
    for pid in [1, 2]:
        pool = [
            (c, r) for c in range(GRID_SIZE) for r in range(GRID_SIZE)
            if is_player_territory(pid, c, r)
            and abs((c + r) - (GRID_SIZE - 1)) > 1   # exclude fence buffer
            and (c, r) not in active_set
            and (c, r) not in CORNER_CELLS
        ]
        rng.shuffle(pool)
        chosen = pool[:HARD_TERRAIN_PER_SIDE + SOFT_TERRAIN_PER_SIDE]
        for i, pos in enumerate(chosen):
            t = TerrainType.HARD if i < HARD_TERRAIN_PER_SIDE else TerrainType.SOFT
            terrain[pos] = TerrainCell(t)
    return terrain


def is_player_territory(player: int, col: int, row: int) -> bool:
    """Anti-diagonal split: P1 (farmer) owns upper-left, P2 (emu) owns lower-right."""
    if player == 1:
        return col + row < GRID_SIZE - 1
    else:
        return col + row >= GRID_SIZE - 1


def get_defense_zone(col: int, row: int) -> List[Tuple[int,int]]:
    """3x3 area centered on defense token."""
    cells = []
    for dc in range(-1, 2):
        for dr in range(-1, 2):
            c, r = col + dc, row + dr
            if 0 <= c < GRID_SIZE and 0 <= r < GRID_SIZE:
                cells.append((c, r))
    return cells


def cast_ray(state: GameState, start_col: int, start_row: int,
             direction: Direction, player: int) -> List[dict]:
    """
    Cast an attack ray, return list of cells hit with outcome.
    Stops at first valid target: enemy cell, soft terrain, hard terrain.
    """
    steps = []
    dc_dr_pairs = []

    # Anti-diagonal fence: P1 (farmer) is upper-left, P2 (emu) is lower-right.
    # Every attack direction must cross INTO the enemy's half of the board.
    if direction == Direction.HORIZONTAL:
        # P1 shoots right (+col), P2 shoots left (-col)
        dc_dr_pairs = [(1, 0)] if player == 1 else [(-1, 0)]
    elif direction == Direction.VERTICAL:
        # P1 shoots downward (+row toward lower-right), P2 shoots upward (-row)
        dc_dr_pairs = [(0, 1)] if player == 1 else [(0, -1)]
    elif direction == Direction.DIAGONAL:
        # P1 shoots down-right (+col,+row), P2 shoots up-left (-col,-row)
        dc_dr_pairs = [(1, 1)] if player == 1 else [(-1, -1)]

    results = []
    for dc, dr in dc_dr_pairs:
        col, row = start_col + dc, start_row + dr
        path = []
        hit = None
        enemy_active = set(map(tuple, state.active_cells.get(3 - player, [])))
        enemy_hq     = state.hidden_bases.get(3 - player)
        while 0 <= col < GRID_SIZE and 0 <= row < GRID_SIZE:
            pos = (col, row)
            in_enemy_territory = not is_player_territory(player, col, row)
            # Only terrain in the enemy's territory can block/absorb a shot.
            # Own terrain is transparent to own attacks.
            if pos in state.terrain and in_enemy_territory:
                terrain = state.terrain[pos]
                hit = {"type": "terrain", "terrain_type": terrain.terrain_type.value,
                       "col": col, "row": row, "hp": terrain.hp}
                path.append({"col": col, "row": row, "hit": True})
                break
            elif pos in enemy_active and pos not in state.destroyed_cells:
                # Active territory cell — may coincide with HQ (handled in resolve_turn)
                hit = {"type": "territory", "col": col, "row": row, "player": 3 - player}
                path.append({"col": col, "row": row, "hit": True})
                break
            elif pos == enemy_hq and in_enemy_territory:
                # Direct HQ hit — base is on a non-active cell
                hit = {"type": "hq", "col": col, "row": row, "player": 3 - player}
                path.append({"col": col, "row": row, "hit": True})
                break
            else:
                path.append({"col": col, "row": row, "hit": False})
            col += dc
            row += dr
        results.append({"path": path, "hit": hit})
    return results


def apply_defense(state: GameState, attacking_player: int) -> GameState:
    """Rebuild defense shields from current defense token positions.
    If a defense token has moved since its last position, reset absorbed_cells for that player.
    """
    state.defense_shields = {}
    for pid in [1, 2]:
        key = f"p{pid}_defense"
        token = state.tokens.get(key)
        if token and token.col >= 0 and token.row >= 0:
            current_pos = (token.col, token.row)
            # Detect movement — reset absorbed memory if token moved
            prev = state.prev_defense_positions.get(pid)
            if prev != current_pos:
                state.absorbed_cells[pid] = set()
                state.prev_defense_positions[pid] = current_pos
            for cell in get_defense_zone(token.col, token.row):
                # Only shield cells that haven't been previously absorbed
                if cell not in state.absorbed_cells[pid]:
                    state.defense_shields[cell] = True
    return state


def resolve_turn(state: GameState, attacking_player: int) -> GameState:
    """Execute full resolve sequence for attacking_player."""
    state = apply_defense(state, attacking_player)
    results = []

    for suffix in ["attack_a", "attack_b"]:
        key = f"p{attacking_player}_{suffix}"
        token = state.tokens.get(key)
        if not token or token.col < 0 or token.row < 0 or token.direction is None:
            continue

        rays = cast_ray(state, token.col, token.row, token.direction, attacking_player)
        for ray in rays:
            if ray["hit"] is None:
                results.append({"token": key, "path": ray["path"], "outcome": "miss"})
                continue

            hit = ray["hit"]
            pos = (hit["col"], hit["row"])

            if hit["type"] == "terrain":
                terrain = state.terrain[pos]
                terrain.hp -= 1
                if terrain.hp <= 0:
                    del state.terrain[pos]
                    results.append({"token": key, "path": ray["path"],
                                    "outcome": "terrain_destroyed", "col": hit["col"], "row": hit["row"]})
                else:
                    outcome = "terrain_hit"
                    results.append({"token": key, "path": ray["path"],
                                    "outcome": outcome, "col": hit["col"], "row": hit["row"],
                                    "hp_remaining": terrain.hp})

            elif hit["type"] == "territory":
                defending_player = 3 - attacking_player
                if pos in state.defense_shields:
                    # Shield absorbs hit — record this cell as absorbed
                    del state.defense_shields[pos]
                    state.absorbed_cells[defending_player].add(pos)
                    results.append({"token": key, "path": ray["path"],
                                    "outcome": "shielded", "col": hit["col"], "row": hit["row"]})
                else:
                    state.destroyed_cells.add(pos)
                    results.append({"token": key, "path": ray["path"],
                                    "outcome": "hit", "col": hit["col"], "row": hit["row"]})
                    # Check if the destroyed territory cell also happened to be the HQ
                    enemy = 3 - attacking_player
                    if state.hidden_bases[enemy] == pos:
                        state.phase = Phase.GAME_OVER
                        state.winner = attacking_player
                        state.win_reason = "base_destroyed"

            elif hit["type"] == "hq":
                # Ray landed directly on the HQ (which sits on a non-active cell)
                defending_player = 3 - attacking_player
                if pos in state.defense_shields:
                    # Shield can still protect the HQ cell
                    del state.defense_shields[pos]
                    state.absorbed_cells[defending_player].add(pos)
                    results.append({"token": key, "path": ray["path"],
                                    "outcome": "shielded", "col": hit["col"], "row": hit["row"]})
                else:
                    results.append({"token": key, "path": ray["path"],
                                    "outcome": "base_hit", "col": hit["col"], "row": hit["row"]})
                    state.phase = Phase.GAME_OVER
                    state.winner = attacking_player
                    state.win_reason = "base_destroyed"

    state.last_attack_results = results
    _check_territory_win(state, attacking_player)
    return state


def _check_territory_win(state: GameState, attacking_player: int):
    enemy = 3 - attacking_player
    active = set(map(tuple, state.active_cells.get(enemy, [])))
    if not active:
        return
    destroyed = active & state.destroyed_cells
    if len(destroyed) >= len(active):
        state.phase = Phase.GAME_OVER
        state.winner = attacking_player
        state.win_reason = "territory_destroyed"


def get_preview(state: GameState, attacking_player: int) -> dict:
    """Compute preview rays without modifying state."""
    preview = []
    temp_state = GameState(
        phase=state.phase,
        terrain=dict(state.terrain),
        destroyed_cells=set(state.destroyed_cells),
        hidden_bases=dict(state.hidden_bases),
        defense_shields=dict(state.defense_shields),
        tokens=dict(state.tokens),
        active_cells=dict(state.active_cells),
        absorbed_cells={pid: set(s) for pid, s in state.absorbed_cells.items()},
        prev_defense_positions=dict(state.prev_defense_positions),
    )
    temp_state = apply_defense(temp_state, attacking_player)

    for suffix in ["attack_a", "attack_b"]:
        key = f"p{attacking_player}_{suffix}"
        token = state.tokens.get(key)
        if not token or token.col < 0 or token.row < 0 or token.direction is None:
            continue
        rays = cast_ray(temp_state, token.col, token.row, token.direction, attacking_player)
        preview.append({"token": key, "rays": rays})
    return {"previews": preview, "defense_zone": list(temp_state.defense_shields.keys())}


def state_to_dict(state: GameState) -> dict:
    return {
        "phase": state.phase.value,
        "current_player": state.current_player,
        "winner": state.winner,
        "win_reason": state.win_reason,
        "terrain": {f"{k[0]},{k[1]}": {"type": v.terrain_type.value, "hp": v.hp}
                    for k, v in state.terrain.items()},
        "destroyed_cells": [[p[0], p[1]] for p in state.destroyed_cells],
        "hidden_bases": {str(k): list(v) if v else None for k, v in state.hidden_bases.items()},
        "defense_shields": [[p[0], p[1]] for p in state.defense_shields.keys()],
        "absorbed_cells": {
            str(pid): [[p[0], p[1]] for p in cells]
            for pid, cells in state.absorbed_cells.items()
        },
        "tokens": {k: {
            "player": t.player, "role": t.role,
            "col": t.col, "row": t.row,
            "direction": t.direction.value if t.direction else None,
            "valid": t.valid
        } for k, t in state.tokens.items()},
        "player_sides": state.player_sides,
        "hq_locked": state.hq_locked,
        "terrain_confirmed": state.terrain_confirmed,
        "active_cells": {str(pid): [[c, r] for c, r in cells]
                         for pid, cells in state.active_cells.items()},
        "last_attack_results": state.last_attack_results,
    }
