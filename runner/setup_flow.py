"""Shared setup-flow and validation helpers for live Old Mick runtimes."""

from __future__ import annotations

from dataclasses import dataclass, field


PHASE_SCAN = "scan"
PHASE_SIDE_SELECTION = "side_selection"
PHASE_HQ_PLACEMENT = "hq_placement"
PHASE_GAME = "game"

PLAYERS = ("p1", "p2")
ATTACKER_SLOTS = ("atk_a", "atk_b")
DEFENDER_SLOT = "def"
SLOTS = ATTACKER_SLOTS + (DEFENDER_SLOT,)

FIRST_PLAYER_SIDE_TO_PLAYER = {
    "old_mick": "p1",
    "mob": "p2",
}

SIDE_DISPLAY_NAME = {
    "p1": "Old Mick",
    "p2": "The Mob",
}

SIDE_ERROR_CODES = {
    "p1": {
        "zone": "old_mick_token_invalid_zone",
        "direction": "old_mick_attack_direction_invalid",
    },
    "p2": {
        "zone": "mob_token_invalid_zone",
        "direction": "mob_attack_direction_invalid",
    },
}

ALLOWED_DIRECTIONS_BY_SIDE = {
    "p1": frozenset(("E", "SE", "S", "SW")),
    "p2": frozenset(("W", "NW", "N", "NE")),
}

ERROR_MESSAGES = {
    "camera_unavailable": "Cannot detect the camera. Check the camera connection and configured camera index.",
    "marker_map_scan_failed": "Cannot locate the board markers. Make sure all four board corner markers are visible and readable.",
    "token_detection_failed": "Cannot detect one or more attack or defence tokens. Reposition the markers and try again.",
    "hq_wrong_side": "HQ must be placed on that side's own territory and not on the fence.",
    "hq_setup_complete": "Both HQ locations are confirmed. Starting the game.",
    "old_mick_token_invalid_zone": "Old Mick tokens must stay on the Old Mick side and cannot be placed on the fence.",
    "mob_token_invalid_zone": "Mob tokens must stay on the Mob side and cannot be placed on the fence.",
    "old_mick_attack_direction_invalid": "Old Mick attack tokens can only aim East, South-East, South, or South-West.",
    "mob_attack_direction_invalid": "Mob attack tokens can only aim West, North-West, North, or North-East.",
    "inactive_side_token_changed": "Only the active player's tokens may move during this turn. The opponent token change was ignored.",
}


def make_error(code: str) -> dict:
    return {"code": code, "message": ERROR_MESSAGES[code]}


def empty_token(*, stale: bool = True) -> dict:
    return {
        "col": None,
        "row": None,
        "angle": None,
        "direction": None,
        "stale": stale,
    }


def new_side_state(*, stale: bool = True) -> dict:
    return {slot: empty_token(stale=stale) for slot in SLOTS}


def clone_token(token: dict | None) -> dict:
    source = token or {}
    return {
        "col": source.get("col"),
        "row": source.get("row"),
        "angle": source.get("angle"),
        "direction": source.get("direction"),
        "stale": bool(source.get("stale", True)),
    }


def clone_side_state(side_state: dict | None) -> dict:
    source = side_state or {}
    return {slot: clone_token(source.get(slot)) for slot in SLOTS}


def side_of_cell(col: int | None, row: int | None) -> str | None:
    if col is None or row is None:
        return None
    total = int(col) + int(row)
    if total < 11:
        return "p1"
    if total > 11:
        return "p2"
    return None


def _states_equal(left: dict, right: dict) -> bool:
    for slot in SLOTS:
        left_token = left.get(slot) or {}
        right_token = right.get(slot) or {}
        if left_token.get("col") != right_token.get("col"):
            return False
        if left_token.get("row") != right_token.get("row"):
            return False
        if left_token.get("direction") != right_token.get("direction"):
            return False
        left_angle = left_token.get("angle")
        right_angle = right_token.get("angle")
        if left_angle is None and right_angle is None:
            continue
        if left_angle is None or right_angle is None:
            return False
        if round(float(left_angle), 1) != round(float(right_angle), 1):
            return False
    return True


def _has_missing_token_data(side_state: dict) -> bool:
    for slot in SLOTS:
        token = side_state.get(slot) or {}
        if token.get("col") is None or token.get("row") is None:
            return True
        if token.get("stale"):
            return True
        if slot in ATTACKER_SLOTS and token.get("direction") is None:
            return True
    return False


def is_valid_hq_position(side: str, position: dict | None) -> bool:
    if side not in PLAYERS or not isinstance(position, dict):
        return False
    col = position.get("x")
    row = position.get("y")
    if not isinstance(col, int) or not isinstance(row, int):
        return False
    if not (0 <= col <= 11 and 0 <= row <= 11):
        return False
    return side_of_cell(col, row) == side


def validate_side_tokens(side: str, side_state: dict) -> list[dict]:
    errors: list[dict] = []
    error_codes = SIDE_ERROR_CODES[side]
    allowed_directions = ALLOWED_DIRECTIONS_BY_SIDE[side]

    for slot in SLOTS:
        token = side_state.get(slot) or {}
        col = token.get("col")
        row = token.get("row")
        if col is None or row is None:
            continue
        if side_of_cell(col, row) != side:
            errors.append(make_error(error_codes["zone"]))
            break

        if slot in ATTACKER_SLOTS:
            direction = token.get("direction")
            if direction is not None and direction not in allowed_directions:
                errors.append(make_error(error_codes["direction"]))
                break

    return errors


def sanitize_token_states(
    raw_p1: dict,
    raw_p2: dict,
    accepted_p1: dict,
    accepted_p2: dict,
    *,
    active_side: str | None,
    require_full_detection: bool = True,
) -> tuple[dict, dict, list[dict]]:
    candidate = {
        "p1": clone_side_state(raw_p1),
        "p2": clone_side_state(raw_p2),
    }
    accepted = {
        "p1": clone_side_state(accepted_p1),
        "p2": clone_side_state(accepted_p2),
    }
    errors: list[dict] = []

    if active_side in PLAYERS:
        inactive_side = "p2" if active_side == "p1" else "p1"
        if not _states_equal(candidate[inactive_side], accepted[inactive_side]):
            candidate[inactive_side] = clone_side_state(accepted[inactive_side])
            errors.append(make_error("inactive_side_token_changed"))

    for side in PLAYERS:
        side_errors = validate_side_tokens(side, candidate[side])
        if side_errors:
            candidate[side] = clone_side_state(accepted[side])
            errors.extend(side_errors)

    if require_full_detection and (_has_missing_token_data(candidate["p1"]) or _has_missing_token_data(candidate["p2"])):
        errors.append(make_error("token_detection_failed"))

    deduped_errors: list[dict] = []
    seen_codes: set[str] = set()
    for error in errors:
        code = error["code"]
        if code in seen_codes:
            continue
        seen_codes.add(code)
        deduped_errors.append(error)

    return candidate["p1"], candidate["p2"], deduped_errors


@dataclass
class SetupState:
    phase: str = PHASE_SCAN
    board_scan_ready: bool = False
    first_player_side: str | None = None
    active_setup_side: str | None = None
    hq_candidates: dict = field(default_factory=lambda: {"p1": None, "p2": None})
    hq_confirmed: dict = field(default_factory=lambda: {"p1": False, "p2": False})
    status_code: str = "waiting_for_board_scan"
    status_message: str = "Waiting for a valid board scan."

    def reset(self, *, board_scan_ready: bool) -> None:
        self.phase = PHASE_SCAN
        self.board_scan_ready = False
        self.first_player_side = None
        self.active_setup_side = None
        self.hq_candidates = {"p1": None, "p2": None}
        self.hq_confirmed = {"p1": False, "p2": False}
        self.status_code = "waiting_for_board_scan"
        self.status_message = "Waiting for a valid board scan."
        self.set_board_scan_ready(board_scan_ready)

    def set_board_scan_ready(self, board_scan_ready: bool) -> None:
        self.board_scan_ready = bool(board_scan_ready)
        if self.phase == PHASE_GAME:
            return
        if not self.board_scan_ready:
            self.phase = PHASE_SCAN
            self.status_code = "waiting_for_board_scan"
            self.status_message = "Waiting for a valid board scan."
            return
        if self.first_player_side is None:
            self.phase = PHASE_SIDE_SELECTION
            self.status_code = "waiting_for_side_selection"
            self.status_message = "Board scan ready. Choose whether the first player is Old Mick or The Mob."
            return
        if not all(self.hq_confirmed.values()):
            self.phase = PHASE_HQ_PLACEMENT
            self._set_waiting_for_hq_status()

    def choose_side(self, first_player_side: str) -> bool:
        if first_player_side not in FIRST_PLAYER_SIDE_TO_PLAYER or not self.board_scan_ready:
            return False
        self.first_player_side = first_player_side
        self.hq_candidates = {"p1": None, "p2": None}
        self.hq_confirmed = {"p1": False, "p2": False}
        self.active_setup_side = FIRST_PLAYER_SIDE_TO_PLAYER[first_player_side]
        self.phase = PHASE_HQ_PLACEMENT
        self._set_waiting_for_hq_status()
        return True

    def set_hq_candidate(self, side: str, position: dict | None) -> dict | None:
        if self.phase != PHASE_HQ_PLACEMENT:
            return None
        if side != self.active_setup_side:
            self._set_waiting_for_hq_status()
            return None
        if not is_valid_hq_position(side, position):
            self.status_code = "waiting_for_hq_candidate"
            self.status_message = ERROR_MESSAGES["hq_wrong_side"]
            return make_error("hq_wrong_side")
        self.hq_candidates[side] = (int(position["x"]), int(position["y"]))
        self.status_code = "waiting_for_hq_confirmation"
        self.status_message = f"{SIDE_DISPLAY_NAME[side]} HQ candidate recorded. Confirm to lock it in."
        return None

    def confirm_hq(self, side: str) -> tuple[bool, dict | None]:
        if self.phase != PHASE_HQ_PLACEMENT or side != self.active_setup_side:
            self._set_waiting_for_hq_status()
            return False, None
        if self.hq_candidates.get(side) is None:
            self.status_code = "waiting_for_hq_candidate"
            self.status_message = f"{SIDE_DISPLAY_NAME[side]} must choose an HQ location before confirming."
            return False, None

        self.hq_confirmed[side] = True
        if all(self.hq_confirmed.values()):
            self.phase = PHASE_GAME
            self.active_setup_side = None
            self.status_code = "hq_setup_complete"
            self.status_message = ERROR_MESSAGES["hq_setup_complete"]
            return True, make_error("hq_setup_complete")

        self.active_setup_side = "p2" if side == "p1" else "p1"
        self.status_code = "waiting_for_hq_candidate"
        self.status_message = f"{SIDE_DISPLAY_NAME[self.active_setup_side]} must choose an HQ location."
        return False, None

    def reset_hq_setup(self) -> None:
        self.hq_candidates = {"p1": None, "p2": None}
        self.hq_confirmed = {"p1": False, "p2": False}
        if self.first_player_side is None:
            self.phase = PHASE_SIDE_SELECTION if self.board_scan_ready else PHASE_SCAN
            self.status_code = "waiting_for_side_selection" if self.board_scan_ready else "waiting_for_board_scan"
            self.status_message = (
                "Board scan ready. Choose whether the first player is Old Mick or The Mob."
                if self.board_scan_ready
                else "Waiting for a valid board scan."
            )
            self.active_setup_side = None
            return
        self.phase = PHASE_HQ_PLACEMENT
        self.active_setup_side = FIRST_PLAYER_SIDE_TO_PLAYER[self.first_player_side]
        self._set_waiting_for_hq_status()

    def hidden_hq_positions(self) -> tuple[tuple[int, int], tuple[int, int]] | None:
        if not all(self.hq_confirmed.values()):
            return None
        return self.hq_candidates["p1"], self.hq_candidates["p2"]

    def public_payload(self) -> dict:
        return {
            "board_scan_ready": self.board_scan_ready,
            "side_selection_complete": self.first_player_side is not None,
            "first_player_side": self.first_player_side,
            "active_setup_side": self.active_setup_side,
            "hq": {
                side: {
                    "has_candidate": self.hq_candidates[side] is not None,
                    "confirmed": self.hq_confirmed[side],
                }
                for side in PLAYERS
            },
            "status_code": self.status_code,
            "status_message": self.status_message,
        }

    def _set_waiting_for_hq_status(self) -> None:
        if self.active_setup_side is None:
            self.status_code = "waiting_for_hq_candidate"
            self.status_message = "Waiting for HQ placement."
            return
        if self.hq_candidates.get(self.active_setup_side) is None:
            self.status_code = "waiting_for_hq_candidate"
            self.status_message = f"{SIDE_DISPLAY_NAME[self.active_setup_side]} must choose an HQ location."
            return
        self.status_code = "waiting_for_hq_confirmation"
        self.status_message = f"{SIDE_DISPLAY_NAME[self.active_setup_side]} HQ candidate recorded. Confirm to lock it in."
