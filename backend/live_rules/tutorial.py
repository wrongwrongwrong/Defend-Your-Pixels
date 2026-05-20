"""Tutorial state machine for the live Old Mick runtime."""

from __future__ import annotations

from dataclasses import dataclass

TUTORIAL_SEED = 42

# Tutorial body copy: keep each line ≤10 words for the overlay panel.
MAX_WORDS_PER_TUTORIAL_LINE = 10

STEPS = [
    {
        "id": "intro",
        "title": "Welcome to Old Mick vs the Mob",
        "text": "In 1932, emus invaded the outback.\nYou are Old Mick.\nDefend your homestead.",
        "condition": "dismiss",
    },
    {
        "id": "scan_board_corners",
        "title": "Scan the Board Corners",
        "text": "Scan all four corner markers.\nWhen the board outline appears, continue.",
        "condition": "dismiss",
        "tutorial_layout": "gif",
        "tutorial_gif": "assets/gif/scan_board_corners.gif",
    },
    {
        "id": "explain_tokens",
        "title": "Your Units",
        "text": "Two attackers: Rifleman A and B.\nOne defender: Old Mick.\nOne HQ — keep it hidden.",
        "condition": "dismiss",
    },
    {
        "id": "explain_sides_alternate",
        "title": "Who Owns Which Side?",
        "text": "A diagonal fence splits the board.\nOld Mick: bottom-left (orange).\nThe Mob: top-right (green).",
        "condition": "dismiss",
        "highlight_side": "p1",
    },
    {
        "id": "explain_win",
        "title": "How to Win",
        "text": "Destroy the enemy HQ, or wipe out their resources.\nProtect your own HQ.",
        "condition": "dismiss",
        "tutorial_layout": "with_pic",
        "tutorial_image": "assets/images/cell-emu-feeding grounds.png",
    },
    {
        "id": "explain_turn_markers",
        "title": "Turn Control",
        "text": "Scan markers to set whose turn it is. Old Mick marker → your turn.\nMob marker → their turn.",
        "condition": "dismiss",
        "tutorial_layout": "gif",
        "tutorial_gif": "assets/gif/End_turn_explain.gif",
    },
    {
        "id": "explain_confirm_marker",
        "title": "Confirm Marker",
        "text": "Scan the confirm marker to lock choices. Use it to finish HQ setup or end your turn.",
        "condition": "dismiss",
        "tutorial_layout": "gif",
        "tutorial_gif": "assets/gif/p1_to_confirm.gif",
    },
    {
        "id": "set_turn_p1",
        "title": "Set Old Mick's Turn",
        "text": "Set the turn marker to Old Mick's side.",
        "condition": "turn_change",
        "wait_turn": 1,
        "tutorial_layout": "gif",
        "tutorial_gif": "assets/gif/confirm_to_p1.gif",
    },
    {
        "id": "explain_hq",
        "title": "Headquarters (HQ)",
        "text": "Each player has one HQ.\nLose if yours is destroyed.\nPlace it secretly before battle.",
        "condition": "dismiss",
    },
    {
        "id": "place_hq_p1",
        "title": "Place Old Mick's HQ",
        "text": "Place your HQ on cell B10.\nIn real game, when one side is placing, the other must look away.",
        "highlight": {"col": 1, "row": 9},
        "condition": "dismiss",
        "tutorial_layout": "with_pic",
        "tutorial_image": "assets/images/hq_mick.png",
    },
    {
        "id": "hq_confirm_scan",
        "title": "Confirm HQ Placement",
        "text": "Slide to the confirm marker.\nScan confirm to finish HQ placement.",
        "highlight": {"col": 1, "row": 9},
        "condition": "confirm_present",
        "tutorial_layout": "gif",
        "tutorial_gif": "assets/gif/p1_to_confirm.gif",
    },
    {
        "id": "notify_tutorial_skip",
        "title": "Tutorial Pace",
        "text": "Token placement and Mob's turn are skipped in this tutorial.",
        "condition": "dismiss",
        "runner_effect": "skip_p2_setup",
    },
    {
        "id": "resume_p1_turn",
        "title": "Old Mick's Turn Again",
        "text": "Slide back to Old Mick's turn marker.",
        "condition": "turn_change",
        "wait_turn": 1,
        "tutorial_layout": "gif",
        "tutorial_gif": "assets/gif/confirm_to_p1.gif",
    },
    {
        "id": "place_atk_a",
        "title": "Place Rifleman A",
        "text": "Place Rifleman A on cell D4.\nMove the marker onto the board.",
        "highlight": {"col": 3, "row": 3},
        "condition": "dismiss",
        "tutorial_layout": "gif",
        "tutorial_gif": "assets/gif/defense_placement_rotated.gif",
    },
    {
        "id": "place_atk_b",
        "title": "Place Rifleman B",
        "text": "Place Rifleman B on cell C6.\nMove the marker onto the board.",
        "highlight": {"col": 2, "row": 5},
        "condition": "dismiss",
        "tutorial_layout": "gif",
        "tutorial_gif": "assets/gif/defense_placement_rotated.gif",
    },
    {
        "id": "aim_atk_a",
        "title": "Aim Rifleman A",
        "text": "Place Rifleman A on cell D5.\nPoint the angle toward south.",
        "highlight": {"col": 3, "row": 4},
        "condition": {
            "token": "p1.atk_a",
            "col": 3,
            "row": 4,
            "direction": "S",
        },
        "tutorial_layout": "gif",
        "tutorial_gif": "assets/gif/attacker_rotation_rotate.gif",
    },
    {
        "id": "explain_ray",
        "title": "Attack Rays",
        "text": "The green line is your attack ray.\nIt stops at the first enemy resource.",
        "condition": "dismiss",
    },
    {
        "id": "place_def",
        "title": "Place Your Defender",
        "text": "Place Old Mick on cell B5.",
        "highlight": {"col": 1, "row": 4},
        "condition": "dismiss",
        "tutorial_layout": "gif",
        "tutorial_gif": "assets/gif/defense_placement_rotated.gif",
    },
    {
        "id": "explain_defense",
        "title": "Defense Zone",
        "text": "The defender's yellow zone softens incoming hits.",
        "condition": "dismiss",
    },
    {
        "id": "end_turn",
        "title": "End Your Turn",
        "text": "Scan the confirm marker to end your turn.",
        "condition": "confirm_present",
        "tutorial_layout": "gif",
        "tutorial_gif": "assets/gif/p1_to_confirm.gif",
    },
    {
        "id": "explain_upgrade_sidebar",
        "title": "Upgrades & Side Panel",
        "text": "Destroy enemy resources to earn tiers.\nTier two upgrades attackers and defense.\nWatch the left sidebar fill in.",
        "condition": "dismiss",
        "highlight_sidebar": "left",
        "runner_effect": "p1_tier2",
    },
    {
        "id": "explain_nuke",
        "title": "The Nuke",
        "text": "At eight or fewer cells left, Nuke unlocks.Place your nuke marker on cell K10.",
        "highlight": {"col": 10, "row": 9},
        "condition": {
            "token": "p1.nuke",
            "col": 10,
            "row": 9,
        },
        "tutorial_layout": "with_pic",
        "tutorial_images": [
            "assets/images/nuke-mick-keith.png",
            "assets/images/nuke-emu-ancestors.png",
        ],
        "runner_effect": "p1_nuke_unlock",
    },
    {
        "id": "explain_help_guide",
        "title": "Help Guide Marker",
        "text": "During a game, scan the help guide marker anytime.",
        "condition": "dismiss",
        "tutorial_layout": "with_pic",
        "tutorial_image": "assets/images/quick_guide.png",
    },
    {
        "id": "complete",
        "title": "Tutorial Complete!",
        "text": "You're ready to play.\nPress SPACE or click to continue.",
        "condition": "dismiss",
        "final": True,
    },
]


def _resolve_layout(step: dict) -> str:
    layout = step.get("tutorial_layout")
    if layout in {"text", "gif", "with_pic"}:
        return layout
    if step.get("tutorial_image") or step.get("tutorial_images"):
        return "with_pic"
    if step.get("tutorial_gif"):
        return "gif"
    return "text"


@dataclass
class TutorialController:
    step_index: int = 0
    completed: bool = False
    finished: bool = False
    _prev_turn_signal: int | None = None
    _confirm_prev: bool = False
    _token_undo_armed: bool = False

    def dismiss(self) -> None:
        if self.finished:
            return
        step = STEPS[self.step_index]
        cond = step.get("condition")
        if cond == "dismiss":
            self._advance()
        elif cond == "turn_change":
            self._advance()

    def undo(
        self,
        *,
        confirm_present: bool = False,
        current_turn: int | None = None,
    ) -> None:
        if self.finished or self.step_index <= 0:
            return
        self.step_index -= 1
        step = STEPS[self.step_index]
        # Match current markers so tick() does not instantly re-advance this step.
        self._confirm_prev = confirm_present
        self._prev_turn_signal = current_turn
        self._token_undo_armed = isinstance(step.get("condition"), dict)
        self.completed = bool(step.get("final"))
        print(f"[TUTORIAL] Undo → step {self.step_index}: {step['id']}")

    def tick(
        self,
        p1_tokens: dict,
        p2_tokens: dict,
        current_turn: int | None,
        hq_markers: dict | None = None,
        confirm_present: bool = False,
        nuke_cells: dict | None = None,
    ) -> dict:
        if self.finished:
            return self.snapshot()

        step = STEPS[self.step_index]
        condition = step.get("condition")

        if condition == "confirm_present":
            edge = confirm_present and not self._confirm_prev
            self._confirm_prev = confirm_present
            if edge:
                self._advance()
            return self.snapshot()

        if condition == "turn_change":
            wait_turn = step.get("wait_turn")
            if isinstance(wait_turn, int) and current_turn == wait_turn and self._prev_turn_signal != wait_turn:
                self._advance()
                return self.snapshot()
            self._prev_turn_signal = current_turn
            return self.snapshot()

        if isinstance(condition, dict):
            met = self._check_token_condition(
                condition, p1_tokens, p2_tokens, hq_markers, nuke_cells
            )
            if self._token_undo_armed:
                if not met:
                    self._token_undo_armed = False
                return self.snapshot()
            if met:
                self._advance()

        return self.snapshot()

    def _check_token_condition(
        self,
        condition: dict,
        p1_tokens: dict,
        p2_tokens: dict,
        hq_markers: dict | None = None,
        nuke_cells: dict | None = None,
    ) -> bool:
        token_path = condition.get("token", "")
        side, _, role = token_path.partition(".")
        if side not in {"p1", "p2"} or not role:
            return False

        if role == "hq":
            tok = (hq_markers or {}).get(side, {})
        elif role == "nuke":
            cell = (nuke_cells or {}).get(side)
            if cell is None:
                return False
            col, row = cell
            tok = {"col": col, "row": row}
        else:
            tokens = p1_tokens if side == "p1" else p2_tokens
            tok = tokens.get(role, {}) if tokens else {}

        if tok.get("col") is None:
            return False
        if "col" in condition and tok.get("col") != condition["col"]:
            return False
        if "row" in condition and tok.get("row") != condition["row"]:
            return False
        if "direction" in condition and tok.get("direction") != condition["direction"]:
            return False
        return True

    def _advance(self) -> None:
        if self.step_index < len(STEPS) - 1:
            self.step_index += 1
            self._prev_turn_signal = None
            self._confirm_prev = False
            if STEPS[self.step_index].get("final"):
                self.completed = True
            print(f"[TUTORIAL] Advanced to step {self.step_index}: {STEPS[self.step_index]['id']}")
            return
        self.finished = True
        print("[TUTORIAL] Finished. Switching to normal game mode.")

    def snapshot(self) -> dict:
        step = STEPS[self.step_index]
        cond = step.get("condition")
        return {
            "active": not self.finished,
            "step_index": self.step_index,
            "total_steps": len(STEPS),
            "step_id": step["id"],
            "title": step.get("title", ""),
            "text": step.get("text", ""),
            "highlight": step.get("highlight"),
            "highlight_alternate_sides": bool(step.get("highlight_alternate_sides")),
            "highlight_side": step.get("highlight_side"),
            "highlight_sidebar": step.get("highlight_sidebar"),
            "tutorial_layout": _resolve_layout(step),
            "tutorial_gif": step.get("tutorial_gif"),
            "tutorial_image": step.get("tutorial_image"),
            "tutorial_images": step.get("tutorial_images"),
            "runner_effect": step.get("runner_effect"),
            "needs_dismiss": cond == "dismiss",
            "needs_confirm": cond == "confirm_present",
            "needs_token": isinstance(cond, dict),
            "allow_skip": cond == "turn_change",
            "can_undo": self.step_index > 0 and not self.finished,
            "completed": self.completed,
        }


def new_tutorial() -> TutorialController:
    return TutorialController()
