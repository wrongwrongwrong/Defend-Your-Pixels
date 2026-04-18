# ---------------------------------------------------------------------------
# game/logic.py — all game rules: rays, combat, upgrades, resolution
# ---------------------------------------------------------------------------
from .constants import ROWS, COLS, DIRS, UPGRADES, COL_LABELS
from .state import GameState, opp, log_event


# ---------------------------------------------------------------------------
# Ray casting
# ---------------------------------------------------------------------------

def fire_ray(state: GameState, r: int, c: int, player: str, direction: str):
    """
    Cast an attack ray from (r, c) in the given direction.

    Returns (row, col) of the first hittable cell on the ray, or None.

    Ray rules:
        - Wall       → blocks permanently, returns None
        - Barricade  → hittable; if already destroyed, ray passes through
        - Enemy cell → hit, return position
        - Own cells / empty / diagonal strip → ray passes through
    """
    dr, dc = DIRS[player][direction]
    nr, nc = r + dr, c + dc
    while 0 <= nr < ROWS and 0 <= nc < COLS:
        pix = state.pixels[nr][nc]
        terr = state.terrain[nr][nc]
        if terr.kind == 'wall':
            return None
        if terr.kind == 'barricade':
            if terr.alive:
                return (nr, nc)       # soft terrain can be hit
            # destroyed soft terrain — ray passes through
            nr += dr; nc += dc
            continue
        if pix.own == opp(player) and pix.alive:
            return (nr, nc)
        nr += dr
        nc += dc
    return None


def get_ray_cells(state: GameState, r: int, c: int, player: str, direction: str) -> list:
    """
    Visualisation helper — returns every cell along the ray with a type tag.

    Tags:
        'path'         — ray passes through (empty / own cell / dead terrain)
        'target'       — first living enemy cell (will be hit)
        'terrain_hit'  — barricade that will be hit
        'blocked'      — wall (ray stops here, no damage)
    """
    dr, dc = DIRS[player][direction]
    nr, nc = r + dr, c + dc
    cells  = []
    while 0 <= nr < ROWS and 0 <= nc < COLS:
        pix = state.pixels[nr][nc]
        terr = state.terrain[nr][nc]
        if terr.kind == 'wall':
            cells.append((nr, nc, 'blocked'))
            break
        if terr.kind == 'barricade' and terr.alive:
            cells.append((nr, nc, 'terrain_hit'))
            break
        if terr.kind == 'barricade' and not terr.alive:
            cells.append((nr, nc, 'path'))
        elif pix.own == opp(player) and pix.alive:
            cells.append((nr, nc, 'target'))
            break
        else:
            cells.append((nr, nc, 'path'))
        nr += dr
        nc += dc
    return cells


# ---------------------------------------------------------------------------
# Adjacency helpers
# ---------------------------------------------------------------------------

def adj_enemy(state: GameState, player: str, r: int, c: int) -> list:
    return [(r+dr, c+dc)
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]
            if 0 <= r+dr < ROWS and 0 <= c+dc < COLS
            and state.pixels[r+dr][c+dc].own == opp(player)
            and state.pixels[r+dr][c+dc].alive]


def adj_own(state: GameState, player: str, r: int, c: int) -> list:
    return [(r+dr, c+dc)
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]
            if 0 <= r+dr < ROWS and 0 <= c+dc < COLS
            and state.pixels[r+dr][c+dc].own == player
            and state.pixels[r+dr][c+dc].alive]


def def_shield_cells(state: GameState, player: str, r: int, c: int, radius: int = 1) -> list:
    """
    Return all own alive cells within Chebyshev distance `radius` of (r, c).
    radius=1 → 3×3 bubble (base DEF:  1 + up to 8 cells)
    radius=2 → 5×5 bubble (DEF+ upg: 1 + up to 8 + up to 16 cells)
    """
    result = []
    for dr in range(-radius, radius + 1):
        for dc in range(-radius, radius + 1):
            nr, nc = r + dr, c + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS:
                if state.pixels[nr][nc].own == player and state.pixels[nr][nc].alive:
                    result.append((nr, nc))
    return result


# ---------------------------------------------------------------------------
# Upgrades
# ---------------------------------------------------------------------------

def check_upg(state: GameState, player: str) -> None:
    """Unlock any upgrades the player has now earned."""
    k, u = state.kills[player], state.upg[player]
    for thresh, key, name, _ in UPGRADES:
        if k >= thresh and key not in u:
            u.add(key)
            state.new_upg[player].add(key)
            name_str = 'Blue' if player == 'b' else 'Red'
            log_event(state, f"{name_str} unlocked {name}!", 'upg')


# ---------------------------------------------------------------------------
# Combat
# ---------------------------------------------------------------------------

def hit_cell(state: GameState, r: int, c: int, attacker: str, label: str = 'ATK'):
    """
    Apply one hit to the cell at (r, c).

    Returns:
        'king'  — enemy king was destroyed (instant win)
        True    — cell/terrain destroyed
        False   — hit blocked or cell already dead
    """
    pix  = state.pixels[r][c]
    terr = state.terrain[r][c]
    coord = f"{COL_LABELS[c]}{r+1}"

    if terr.kind is not None:
        if not terr.alive:
            return False
        terr.hp -= 1
        if terr.hp <= 0:
            terr.alive = False
            kind_name = 'wall' if terr.kind == 'wall' else 'barricade'
            terr.kind = None
            log_event(state, f"{label} destroyed {kind_name} at {coord}")
            return True
        log_event(state, f"{label} hit barricade at {coord} (HP {terr.hp})")
        return False

    if not pix.alive:
        return False

    if pix.shld:
        log_event(state, f"{label} > {coord} blocked by shield")
        pix.shld = False
        return False

    pix.hp -= 1

    if pix.hp <= 0:
        pix.alive = False
        state.kills[attacker] += 1
        check_upg(state, attacker)
        if state.hq[opp(attacker)] == (r, c):
            winner = 'Blue' if attacker == 'b' else 'Red'
            log_event(state, f"HQ at {coord} destroyed! {winner} wins!", 'win')
            return 'king'
        log_event(state, f"{label} destroyed {coord}")
        return True

    # Cell survived the hit
    log_event(state, f"{label} hit {coord} (HP {pix.hp})")
    return False


def _check_win(state: GameState, king_hit: bool) -> bool:
    """If win condition met, set phase to 'over' and record winner. Returns True if game over."""
    o = opp(state.turn)
    enemy_alive = any(
        state.pixels[r][c].alive
        for r in range(ROWS) for c in range(COLS)
        if state.pixels[r][c].own == o
    )
    if king_hit or not enemy_alive:
        state.phase  = 'over'
        state.winner = state.turn
        return True
    return False


# ---------------------------------------------------------------------------
# Turn resolution
# ---------------------------------------------------------------------------

def resolve(state: GameState) -> None:
    """
    Resolve the active player's turn.

    Order of operations:
        1. Clear own shields from previous round
        2. Apply DEF shield (+ adjacent if DEF+ unlocked)
        3. Fire ATK tokens (stacked = AOE, separate = individual rays)
        4. Bonus attack from ATK-A if T3 unlocked
        5. Win check — end game or swap turn
    """
    p        = state.turn
    king_hit = False
    state.new_upg = {'b': set(), 'r': set()}

    # 1 — clear own shields
    for r in range(ROWS):
        for c in range(COLS):
            if state.pixels[r][c].own == p:
                state.pixels[r][c].shld = False

    # 2 — defense
    #   Base DEF : 3×3 bubble  (Chebyshev radius 1 — up to 9 own cells)
    #   DEF+ upg : 5×5 bubble  (Chebyshev radius 2 — up to 25 own cells)
    df = state.tok[p]['df']
    if df.pos and not df.mv:
        radius = 2 if 'dt2' in state.upg[p] else 1
        shielded = def_shield_cells(state, p, *df.pos, radius=radius)
        for nr, nc in shielded:
            state.pixels[nr][nc].shld = True
        size_str = '5×5' if radius == 2 else '3×3'
        log_event(state, f"DEF shields {len(shielded)} cells ({size_str} around {COL_LABELS[df.pos[1]]}{df.pos[0]+1})")

    # 3 — attack tokens
    a1, a2  = state.tok[p]['a1'], state.tok[p]['a2']
    stacked = (a1.pos and a2.pos and not a1.mv and not a2.mv and a1.pos == a2.pos)

    if stacked:
        # Both ATK on same cell → AOE burst
        target = fire_ray(state, *a1.pos, p, a1.dir or 'h')
        if target:
            res = hit_cell(state, *target, p, 'STACK')
            if res == 'king':
                king_hit = True
            if state.terrain[target[0]][target[1]].kind is None:
                for er, ec in adj_enemy(state, p, *target):
                    if hit_cell(state, er, ec, p, 'STACK-AOE') == 'king':
                        king_hit = True
    else:
        for key, tok in [('a1', a1), ('a2', a2)]:
            if not tok.pos or not tok.dir:
                if tok.pos and not tok.dir:
                    log_event(state, f"{key.upper()} has no direction — skip")
                continue

            target = fire_ray(state, *tok.pos, p, tok.dir)
            if target:
                res = hit_cell(state, *target, p, key.upper())
                if res == 'king':
                    king_hit = True
                elif res and 't2' in state.upg[p] and state.terrain[target[0]][target[1]].kind is None:
                    for er, ec in adj_enemy(state, p, *target)[:1]:
                        if hit_cell(state, er, ec, p, 'SPLASH') == 'king':
                            king_hit = True

    # 4 — T3 bonus attack
    if 't3' in state.upg[p] and a1.pos and not a1.mv and a1.dir:
        target = fire_ray(state, *a1.pos, p, a1.dir)
        if target:
            if hit_cell(state, *target, p, 'T3-BONUS') == 'king':
                king_hit = True

    # 5 — win check / swap turn
    if _check_win(state, king_hit):
        return

    o = opp(p)
    state.turn        = o
    state.round      += 1
    for tok in state.tok[o].values():
        tok.mv = False
    state.sel         = None
    state.pending_dir = None
    state.undo        = None
    state.phase       = 'pass_turn'

