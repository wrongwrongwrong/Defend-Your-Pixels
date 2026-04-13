# ---------------------------------------------------------------------------
# game/input.py — all input handlers: token placement, king setup, UI actions
# ---------------------------------------------------------------------------
from .constants import COL_LABELS
from .state import GameState, opp, log_event, in_territory
from .logic import do_nuke, resolve


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
    if state.sel == 'df':
        # DEF may not share a cell with either ATK token
        for k in ('a1', 'a2'):
            if state.tok[p][k].pos == (r, c):
                log_event(state, "DEF can't share a cell with ATK")
                return
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
        if state.g[r][c].own == 'b' and state.g[r][c].alive:
            state.hq['b'] = (r, c)
            state.phase = 'setup_pass'
        return

    if state.phase == 'setup_hq_r':
        if state.g[r][c].own == 'r' and state.g[r][c].alive:
            state.hq['r'] = (r, c)
            state.phase = 'init_place_b'
            state.turn  = 'b'
        return

    if state.phase in ('turn', 'init_place_b', 'init_place_r'):
        if state.pending_dir:
            return
        if state.nuke_mode:
            if state.g[r][c].own == opp(state.turn) and state.g[r][c].alive:
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


# ---------------------------------------------------------------------------
# Phase transitions
# ---------------------------------------------------------------------------

def done_init_place(state: GameState) -> None:
    """Player presses Done during initial token placement."""
    state.sel         = None
    state.pending_dir = None
    state.nuke_mode   = False
    if state.phase == 'init_place_b':
        state.phase = 'init_pass'       # Blue looks away, Red takes over
    elif state.phase == 'init_place_r':
        state.turn  = 'b'
        state.phase = 'pass_turn'       # Both sides placed — normal turns begin


def start_setup(state: GameState) -> None:
    state.phase = 'setup_hq_b'


def cont_setup_r(state: GameState) -> None:
    state.phase = 'setup_hq_r'


def cont_init_r(state: GameState) -> None:
    state.turn  = 'r'
    state.phase = 'init_place_r'


def start_turn(state: GameState) -> None:
    state.phase       = 'turn'
    state.sel         = None
    state.nuke_mode   = False
    state.pending_dir = None
