# ---------------------------------------------------------------------------
# game/input.py — all input handlers: token placement, king setup, UI actions
# ---------------------------------------------------------------------------
from .constants import COL_LABELS
from .state import GameState, opp, log_event, in_territory
from .logic import do_nuke, resolve
# ---------------------------------------------------------------------------
# Placement validation
# ---------------------------------------------------------------------------

def _missing_init_items(state: GameState) -> list[str]:
    """Return a list of missing items for initial placement (current player)."""
    p = state.turn
    missing: list[str] = []
    a1 = state.tok[p]['a1']
    a2 = state.tok[p]['a2']
    df = state.tok[p]['df']
    if df.pos is None:
        missing.append("DEF position")
    if a1.pos is None:
        missing.append("ATK-A position")
    if a2.pos is None:
        missing.append("ATK-B position")
    if a1.pos is not None and not a1.dir:
        missing.append("ATK-A direction")
    if a2.pos is not None and not a2.dir:
        missing.append("ATK-B direction")
    return missing


def can_done_init_place(state: GameState) -> bool:
    return state.phase in ('init_place_b', 'init_place_r') and not _missing_init_items(state)



# ---------------------------------------------------------------------------
# Token placement
# ---------------------------------------------------------------------------

def _place_token(state: GameState, r: int, c: int) -> None:
    """Shared token placement logic used in turn and init phases."""
    p = state.turn
    if not state.sel:
        return
    tok = state.tok[p][state.sel]
    # Clicking the token's own cell deselects it
    if tok.pos == (r, c):
        state.sel = None
        return
    # Must be on the player's own half (not diagonal, not enemy side)
    if not in_territory(p, r, c):
        return
    # No two tokens of the same player may share a cell
    for k, other in state.tok[p].items():
        if k != state.sel and other.pos == (r, c):
            log_event(state, f"Cell already occupied by {k.upper()}")
            return
    if state.sel == 'df':
        tok.pos   = (r, c)
        tok.mv    = False
        state.sel = None
    else:
        tok.pos           = (r, c)
        tok.mv            = False
        tok.dir           = None          # direction must be chosen fresh
        state.pending_dir = state.sel
        state.sel         = None


# ---------------------------------------------------------------------------
# Grid click dispatch
# ---------------------------------------------------------------------------

def cell_click(state: GameState, r: int, c: int) -> None:
    if state.phase == 'setup_hq_b':
        # Force correct player for this phase.
        state.turn = 'b'
        if state.pixels[r][c].own == 'b' and state.pixels[r][c].alive:
            coord = f"{COL_LABELS[c]}{r+1}"
            if state.hq_pending == ('b', (r, c)):
                state.hq['b'] = (r, c)
                state.hq_pending = None
                state.phase = 'setup_pass'
                log_event(state, f"Blue HQ confirmed at {coord}")
            else:
                state.hq_pending = ('b', (r, c))
                log_event(state, f"Confirm Blue HQ at {coord}? Click again to confirm.", 'upg')
        return

    if state.phase == 'setup_hq_r':
        # Force correct player for this phase.
        state.turn = 'r'
        if state.pixels[r][c].own == 'r' and state.pixels[r][c].alive:
            coord = f"{COL_LABELS[c]}{r+1}"
            if state.hq_pending == ('r', (r, c)):
                state.hq['r'] = (r, c)
                state.hq_pending = None
                state.phase = 'init_place_b'
                state.turn  = 'b'
                log_event(state, f"Red HQ confirmed at {coord}")
            else:
                state.hq_pending = ('r', (r, c))
                log_event(state, f"Confirm Red HQ at {coord}? Click again to confirm.", 'upg')
        return

    if state.phase in ('turn', 'init_place_b', 'init_place_r'):
        # If an ATK token is awaiting a direction, allow the player to re-place it
        # by clicking a different valid tile (instead of forcing an immediate dir pick).
        if state.pending_dir:
            key = state.pending_dir
            if key in ('a1', 'a2'):
                state.sel = key
                state.pending_dir = None
                _place_token(state, r, c)
            return
        if state.nuke_mode:
            if state.pixels[r][c].own == opp(state.turn) and state.pixels[r][c].alive:
                do_nuke(state, r, c)
            return
        _place_token(state, r, c)


# ---------------------------------------------------------------------------
# Direction & token selection
# ---------------------------------------------------------------------------

def pick_direction(state: GameState, direction: str) -> None:
    if not state.pending_dir:
        return
    state.tok[state.turn][state.pending_dir].dir = direction
    state.pending_dir = None


def sel_tok(state: GameState, key: str) -> None:
    if state.pending_dir:
        return
    state.nuke_mode = False
    state.sel = None if state.sel == key else key


def toggle_nuke(state: GameState) -> None:
    if state.pending_dir:
        return
    state.sel       = None
    state.nuke_mode = not state.nuke_mode


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
    state.nuke_mode = snap.get('nuke_mode', False)
    log_event(state, "Undo: restored plan for this turn")


# ---------------------------------------------------------------------------
# Phase transitions
# ---------------------------------------------------------------------------

def done_init_place(state: GameState) -> None:
    """Player presses Done during initial token placement."""
    if state.phase in ('init_place_b', 'init_place_r'):
        missing = _missing_init_items(state)
        if missing:
            log_event(state, "Place all tokens before Done: " + ", ".join(missing), 'info')
            return
    state.sel         = None
    state.pending_dir = None
    state.nuke_mode   = False
    if state.phase == 'init_place_b':
        state.phase = 'init_pass'       # Blue looks away, Red takes over
    elif state.phase == 'init_place_r':
        state.turn  = 'b'
        state.phase = 'pass_turn'       # Both sides placed — normal turns begin


def start_setup(state: GameState) -> None:
    state.turn = 'b'
    state.hq_pending = None
    state.phase = 'setup_hq_b'


def cont_setup_r(state: GameState) -> None:
    state.turn = 'r'
    state.hq_pending = None
    state.phase = 'setup_hq_r'


def cont_init_r(state: GameState) -> None:
    state.turn  = 'r'
    state.phase = 'init_place_r'


def start_turn(state: GameState) -> None:
    state.phase       = 'turn'
    state.sel         = None
    state.nuke_mode   = False
    state.pending_dir = None
    # Snapshot for undo during planning (before Resolve).
    state.undo = {
        'turn': state.turn,
        'tok': {
            pl: {k: {'pos': t.pos, 'mv': t.mv, 'dir': t.dir} for k, t in state.tok[pl].items()}
            for pl in ('b', 'r')
        },
        'sel': None,
        'pending_dir': None,
        'nuke_mode': False,
    }
