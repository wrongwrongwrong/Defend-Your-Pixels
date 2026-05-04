# ---------------------------------------------------------------------------
# game/input.py — all input handlers: token placement, setup, UI actions
# ---------------------------------------------------------------------------
from .constants import COL_LABELS, TEAM_NAMES, TOKEN_MOVE_RANGE, ROWS, COLS
from .state import GameState, opp, log_event, in_territory
from .logic import resolve

# ---------------------------------------------------------------------------
# Placement validation
# ---------------------------------------------------------------------------

def _missing_setup_items(state: GameState) -> list[str]:
    """Return a list of missing items for setup (HQ + tokens) for the current player."""
    p = state.turn
    missing: list[str] = []
    if state.hq.get(p) is None:
        missing.append("HQ position")
    if state.tok[p]['df'].pos is None:
        missing.append("DEF position")
    if state.tok[p]['a1'].pos is None:
        missing.append("ATK-A position")
    if state.tok[p]['a2'].pos is None:
        missing.append("ATK-B position")
    return missing


def can_done_setup(state: GameState) -> bool:
    return state.phase in ('setup_b', 'setup_r') and not _missing_setup_items(state)


# ---------------------------------------------------------------------------
# Token placement
# ---------------------------------------------------------------------------

def _origin_pos(state: GameState, key: str) -> tuple | None:
    """Return the token's position at the start of this turn (from undo snapshot)."""
    if state.undo and state.turn in state.undo.get('tok', {}):
        saved = state.undo['tok'][state.turn].get(key)
        if saved:
            return saved['pos']
    return state.tok[state.turn][key].pos


def reachable_cells(state: GameState) -> set:
    """Return (r, c) cells the selected token can move to during the turn phase."""
    if not state.sel or state.phase != 'turn':
        return set()
    p = state.turn
    tok = state.tok[p].get(state.sel)
    if not tok or not tok.pos:
        return set()
    origin = _origin_pos(state, state.sel) or tok.pos
    tr, tc = origin
    result = set()
    for dr in range(-TOKEN_MOVE_RANGE, TOKEN_MOVE_RANGE + 1):
        for dc in range(-TOKEN_MOVE_RANGE, TOKEN_MOVE_RANGE + 1):
            nr, nc = tr + dr, tc + dc
            if not (0 <= nr < ROWS and 0 <= nc < COLS):
                continue
            if not in_territory(p, nr, nc):
                continue
            terr = state.terrain[nr][nc]
            if terr.kind == 'wall' or (terr.kind == 'barricade' and terr.alive):
                continue
            occupied = any(
                k != state.sel and other.pos == (nr, nc)
                for k, other in state.tok[p].items()
            )
            if not occupied:
                result.add((nr, nc))
    return result


def _place_token(state: GameState, r: int, c: int) -> None:
    """Shared token placement logic used in turn and setup phases."""
    p = state.turn
    if not state.sel:
        return
    tok = state.tok[p][state.sel]
    if tok.pos == (r, c):
        if state.phase != 'turn':
            state.sel = None
        return
    if not in_territory(p, r, c):
        return
    terr = state.terrain[r][c]
    if terr.kind == 'wall' or (terr.kind == 'barricade' and terr.alive):
        log_event(state, "Cannot place on terrain")
        return
    # Enforce movement range during turn phase (measured from start-of-turn position)
    if state.phase == 'turn' and tok.pos is not None:
        origin = _origin_pos(state, state.sel) or tok.pos
        dist = max(abs(r - origin[0]), abs(c - origin[1]))
        if dist > TOKEN_MOVE_RANGE:
            log_event(state, f"Out of range! Max {TOKEN_MOVE_RANGE} tiles per turn")
            return
    for k, other in state.tok[p].items():
        if k != state.sel and other.pos == (r, c):
            log_event(state, f"Cell already occupied by {k.upper()}")
            return
    tok.pos = (r, c)
    tok.mv  = False
    if state.phase != 'turn':
        state.sel = None


# ---------------------------------------------------------------------------
# Grid click dispatch
# ---------------------------------------------------------------------------

def cell_click(state: GameState, r: int, c: int) -> None:
    p = state.turn

    # ── Unified setup phase (HQ + tokens in any order) ────────────────────
    if state.phase in ('setup_b', 'setup_r'):
        # If no HQ yet and player clicks one of their own alive pixels → HQ placement
        if state.hq.get(p) is None and state.sel is None:
            pix = state.pixels[r][c]
            if pix.own == p and pix.alive:
                coord = f"{COL_LABELS[c]}{r+1}"
                team = TEAM_NAMES[p]
                if state.hq_pending == (p, (r, c)):
                    state.hq[p] = (r, c)
                    state.hq_pending = None
                    log_event(state, f"{team} HQ confirmed at {coord}")
                else:
                    state.hq_pending = (p, (r, c))
                    log_event(state, f"Set {team} HQ at {coord}? Click again to confirm.", 'upg')
            return

        # Otherwise handle token placement (sel must be set via side panel)
        _place_token(state, r, c)
        return

    # ── Normal turn phase ─────────────────────────────────────────────────
    if state.phase == 'turn':
        _place_token(state, r, c)


# ---------------------------------------------------------------------------
# Direction & token selection
# ---------------------------------------------------------------------------

def pick_direction(state: GameState, direction: str) -> None:
    if state.sel in ('a1', 'a2') and state.phase == 'turn':
        state.tok[state.turn][state.sel].dir = direction
    elif state.pending_dir:
        state.tok[state.turn][state.pending_dir].dir = direction
        state.pending_dir = None


def sel_tok(state: GameState, key: str) -> None:
    state.sel = None if state.sel == key else key


def undo_turn_plan(state: GameState) -> None:
    """Undo all planning changes since the start of the current turn (before Resolve)."""
    if state.phase != 'turn' or state.undo is None:
        return
    if state.undo.get('turn') != state.turn:
        return
    snap = state.undo
    for pl in ('b', 'r'):
        for k, t in state.tok[pl].items():
            saved = snap['tok'][pl][k]
            t.pos = saved['pos']
            t.mv = saved['mv']
            t.dir = saved['dir']
    state.sel = snap.get('sel')
    state.pending_dir = snap.get('pending_dir')
    log_event(state, "Undo: restored plan for this turn")


# ---------------------------------------------------------------------------
# Phase transitions
# ---------------------------------------------------------------------------

def start_team_pick(state: GameState) -> None:
    """intro -> team_pick"""
    state.phase = 'team_pick'


def confirm_teams(state: GameState) -> None:
    """team_pick -> setup_b"""
    state.turn = 'b'
    state.hq_pending = None
    state.phase = 'setup_b'


def done_setup(state: GameState) -> None:
    """Player presses Space/Done during setup. Validates HQ + all tokens."""
    if state.phase not in ('setup_b', 'setup_r'):
        return
    missing = _missing_setup_items(state)
    if missing:
        log_event(state, "Complete setup first: " + ", ".join(missing), 'info')
        return
    state.sel         = None
    state.pending_dir = None
    state.hq_pending  = None
    if state.phase == 'setup_b':
        state.phase = 'setup_pass'
    elif state.phase == 'setup_r':
        state.turn  = 'b'
        state.phase = 'pass_turn'


def cont_setup_r(state: GameState) -> None:
    """setup_pass -> setup_r"""
    state.turn = 'r'
    state.hq_pending = None
    state.phase = 'setup_r'


def start_turn(state: GameState) -> None:
    state.phase       = 'turn'
    state.sel         = None
    state.pending_dir = None
    state.undo = {
        'turn': state.turn,
        'tok': {
            pl: {k: {'pos': t.pos, 'mv': t.mv, 'dir': t.dir} for k, t in state.tok[pl].items()}
            for pl in ('b', 'r')
        },
        'sel': None,
        'pending_dir': None,
    }
