# ---------------------------------------------------------------------------
# game/tutorial.py — guided single-player tutorial with pre-defined board
# ---------------------------------------------------------------------------
from .constants import ROWS, COLS, COL_LABELS
from .state import GameState, PixelCell, TerrainTile, Token, log_event
from .logic import resolve as _full_resolve

# ---------------------------------------------------------------------------
# Step definitions
# ---------------------------------------------------------------------------
#   type='popup'  → overlay with title + body, SPACE to dismiss
#   type='play'   → player interacts on the board, SPACE to resolve

MENU_OPTIONS = ["Start New Game", "Tutorial", "Quit"]

TUT_STEPS = [
    {
        'type': 'popup',
        'title': 'Welcome to the Tutorial!',
        'lines': [
            'Your Ranger tokens (A1, A2, DF) are already on the board.',
            'In a real game, place your physical fiducial markers',
            'on the table to match the positions shown on screen.',
            '',
            'SPACE  to continue',
        ],
    },
    {
        'type': 'popup',
        'title': 'Step 1 — Attack!',
        'lines': [
            'Click  A1  in the left sidebar to select it.',
            f'Then click cell  D4  on the grid to move it there.',
            'Choose direction:  Horizontal (>)',
            f'The ray will travel right and hit the Emu pixel at J4!',
            '',
            'SPACE  to begin',
        ],
    },
    {
        'type': 'play',
        'hint': 'Select A1 -> click D4 -> direction Horizontal -> SPACE to fire!',
        'highlight': (3, 3),
    },
    {
        'type': 'popup',
        'title': 'Nice Shot!',
        'lines': [
            'Attackers fire a ray in their set direction',
            'until it hits the first enemy pixel in its path.',
            '',
            'Now let\'s learn how to protect your own pixels.',
            '',
            'SPACE  to continue',
        ],
    },
    {
        'type': 'popup',
        'title': 'Step 2 — Defend!',
        'lines': [
            'Click  DF  in the left sidebar to select it.',
            'Then click cell  B2  on the grid to move it there.',
            'The defender shields all friendly pixels in a 3x3 area!',
            '',
            'SPACE  to begin',
        ],
    },
    {
        'type': 'play',
        'hint': 'Select DF -> click B2 -> SPACE to activate shield!',
        'highlight': (1, 1),
    },
    {
        'type': 'popup',
        'title': 'Tutorial Complete!',
        'lines': [
            'Congratulations, Ranger!',
            'You\'ve mastered attacking and defending.',
            '',
            'In the real game, Emus and Rangers take turns',
            'moving tokens and resolving combat each round.',
            'Earn kills to unlock Splash, DEF+, and Bonus ATK!',
            '',
            'SPACE  to return to the main menu',
        ],
        'final': True,
    },
]


# ---------------------------------------------------------------------------
# Tutorial state initialisation
# ---------------------------------------------------------------------------

def init_tutorial_state() -> GameState:
    """Return a deterministic board for the tutorial walkthrough."""
    px = [[PixelCell() for _ in range(COLS)] for _ in range(ROWS)]
    terr = [[TerrainTile() for _ in range(COLS)] for _ in range(ROWS)]

    blue_cells = [
        (0, 0), (0, 1), (0, 2), (0, 3),
        (1, 0), (1, 1), (1, 2), (1, 3),
        (2, 0), (2, 1), (2, 2),
        (3, 0), (3, 1),
    ]
    for r, c in blue_cells:
        px[r][c] = PixelCell(own='b', alive=True, hp=1)

    red_cells = [
        (8, 10), (8, 11),
        (9, 9), (9, 10), (9, 11),
        (10, 8), (10, 9), (10, 10), (10, 11),
        (11, 8), (11, 9), (11, 10), (11, 11),
    ]
    for r, c in red_cells:
        px[r][c] = PixelCell(own='r', alive=True, hp=1)

    # Target pixel that A1's horizontal ray can reach from D4
    px[3][9] = PixelCell(own='r', alive=True, hp=1)

    return GameState(
        pixels=px,
        terrain=terr,
        hq={'b': (0, 0), 'r': (11, 11)},
        hq_pending=None,
        tok={
            'b': {
                'a1': Token(pos=(2, 2), mv=False, dir='h'),
                'a2': Token(pos=(3, 1), mv=False, dir='v'),
                'df': Token(pos=(0, 2), mv=False),
            },
            'r': {
                'a1': Token(pos=(10, 9), mv=False, dir='h'),
                'a2': Token(pos=(9, 10), mv=False, dir='v'),
                'df': Token(pos=(11, 10), mv=False),
            },
        },
        kills={'b': 0, 'r': 0},
        upg={'b': set(), 'r': set()},
        new_upg={'b': set(), 'r': set()},
        turn='b', round=1, phase='tut_popup',
        tut_step=0,
    )


# ---------------------------------------------------------------------------
# Tutorial flow helpers
# ---------------------------------------------------------------------------

def tut_current(state: GameState) -> dict | None:
    """Return the current tutorial step config, or None."""
    if 0 <= state.tut_step < len(TUT_STEPS):
        return TUT_STEPS[state.tut_step]
    return None


def _tut_enter_step(state: GameState) -> None:
    """Set phase/state based on current step type."""
    step = tut_current(state)
    if step is None:
        state.phase = 'tut_popup'
        return
    if step['type'] == 'popup':
        state.phase = 'tut_popup'
    elif step['type'] == 'play':
        state.phase = 'turn'
        state.sel = None
        state.pending_dir = None
        for tok in state.tok['b'].values():
            tok.mv = False
        state.undo = {
            'turn': state.turn,
            'tok': {
                pl: {k: {'pos': t.pos, 'mv': t.mv, 'dir': t.dir}
                     for k, t in state.tok[pl].items()}
                for pl in ('b', 'r')
            },
            'sel': None,
            'pending_dir': None,
        }


def tut_dismiss_popup(state: GameState) -> str | None:
    """SPACE pressed on a tutorial popup.

    Returns 'menu' if the tutorial is finished, else None.
    """
    step = tut_current(state)
    if step and step.get('final'):
        return 'menu'
    state.tut_step += 1
    _tut_enter_step(state)
    return None


def tut_resolve(state: GameState) -> None:
    """Resolve combat in tutorial mode, then advance to the next step."""
    _full_resolve(state)
    # Override the turn swap — keep player as blue
    state.turn = 'b'
    for tok in state.tok['b'].values():
        tok.mv = False
    state.sel = None
    state.pending_dir = None
    state.undo = None
    # Advance to next step
    state.tut_step += 1
    _tut_enter_step(state)
