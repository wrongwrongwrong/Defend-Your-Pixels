"""Tutorial state machine for the live Old Mick runtime."""

from __future__ import annotations

from dataclasses import dataclass

TUTORIAL_SEED = 42

# Tutorial body copy: keep each line ≤10 words for the overlay panel.
MAX_WORDS_PER_TUTORIAL_LINE = 10

STEPS = [
    {
        "id": "intro",
        "title": "Welcome to Old Mick Against the Mob",
        "text": "In 1932, emus invaded the outback.\nYou are Old Mick.\nDefend your homestead.",
        "condition": "dismiss",
    },
    {
        "id": "scan_board_corners",
        "title": "Scan the Board Corners",
        "text": "Show all four corner markers to the camera.\nWhen the board outline appears, continue.",
        "condition": "dismiss",
        "tutorial_gif": "assets/gif/scan_board_corners.gif",
    },
    {
        "id": "explain_tokens",
        "title": "Your Units",
        "text": "Two attackers: Keith A and B.\nOne defender: Old Mick.\nOne HQ — keep it hidden.",
        "condition": "dismiss",
    },
    {
        "id": "explain_sides_alternate",
        "title": "Who Owns Which Side?",
        "text": "A diagonal fence splits the board.\nOld Mick: bottom-left (orange).\nThe Mob: top-right (green).\nStay on your own side.",
        "condition": "dismiss",
        "highlight_alternate_sides": True,
    },
    {
        "id": "explain_hq",
        "title": "Headquarters (HQ)",
        "text": "Each player hides one HQ.\nLose if yours is destroyed.\nPlace it secretly before battle.",
        "condition": "dismiss",
    },
    {
        "id": "place_hq_p1",
        "title": "Place Old Mick's HQ",
        "text": "Place hq_mick on cell B3.\nDo not reveal it to your opponent.",
        "highlight": {"col": 1, "row": 2},
        "condition": "dismiss",
        "tutorial_gif": "assets/gif/Tutorial_HQsetup_Placeholder.gif",
    },
    {
        "id": "explain_turn_marker",
        "title": "The Turn Marker",
        "text": "Turns follow scanned markers:\n#10 → Old Mick\n#20 → The Mob\n#4 → end your turn",
        "condition": "dismiss",
        "tutorial_gif": "assets/gif/turn_marker.gif",
    },
    {
        "id": "set_turn_p1",
        "title": "Set Turn to Old Mick",
        "text": "Scan marker #10 now.\nThe camera should detect Old Mick's turn.",
        "condition": "turn_change",
        "wait_turn": 1,
        "tutorial_gif": "assets/gif/turn_marker.gif",
    },
    {
        "id": "place_atk_a",
        "title": "Place Your First Attacker",
        "text": "Place Keith A on cell D4.\nMove the marker onto the board.",
        "highlight": {"col": 3, "row": 3},
        "condition": "dismiss",
        "tutorial_gif": "assets/gif/defense_placement_rotated.gif",
    },
    {
        "id": "aim_atk_a",
        "title": "Aim Your Attack",
        "text": "Rotate Keith A to face EAST.\nThe ray fires in that direction.",
        "highlight": {"col": 3, "row": 3},
        "condition": "dismiss",
        "tutorial_gif": "assets/gif/aim_atk_a.gif",
    },
    {
        "id": "explain_ray",
        "title": "Attack Rays",
        "text": "The green line is your attack ray.\nIt stops at the first enemy resource.",
        "condition": "dismiss",
    },
    {
        "id": "place_atk_b",
        "title": "Place Second Attacker",
        "text": "Place Keith B on cell C6.",
        "highlight": {"col": 2, "row": 5},
        "condition": "dismiss",
    },
    {
        "id": "aim_atk_b",
        "title": "Aim Second Attacker",
        "text": "Rotate Keith B to face south-east.",
        "highlight": {"col": 2, "row": 5},
        "condition": "dismiss",
        "tutorial_gif": "assets/gif/attacker_rotation_rotate.gif",
    },
    {
        "id": "place_def",
        "title": "Place Your Defender",
        "text": "Place Old Mick on cell B5.",
        "highlight": {"col": 1, "row": 4},
        "condition": "dismiss",
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
        "text": "Scan marker #4 to end your turn.",
        "condition": "confirm_present",
        "tutorial_gif": "assets/gif/turn_marker.gif",
    },
    {
        "id": "wait_opponent",
        "title": "Opponent's Turn",
        "text": "Scan marker #20 for The Mob's turn.",
        "condition": "turn_change",
        "wait_turn": 2,
        "tutorial_gif": "assets/gif/turn_marker.gif",
    },
    {
        "id": "explain_tiers",
        "title": "Tier System",
        "text": "Destroy resources to earn tiers.\n6, 14, 22, 32 points unlock upgrades.\nTier 1: splash. Tier 2: bigger defense.\nTier 4 unlocks the Nuke.",
        "condition": "dismiss",
    },
    {
        "id": "explain_nuke",
        "title": "The Nuke",
        "text": "At 8 or fewer enemy cells, Nuke unlocks.\nScan #19 (Mick) or #29 (Mob) on an enemy cell.\nScan #4 to launch a 3×3 blast.\nHQs are never damaged.",
        "condition": "dismiss",
    },
    {
        "id": "explain_nuke_confirm",
        "title": "Launching the Nuke",
        "text": "With the nuke marker on target, the cell locks.\nScan #4 to fire — same as ending your turn.",
        "condition": "dismiss",
    },
    {
        "id": "explain_win",
        "title": "How to Win",
        "text": "Destroy the enemy HQ, or reach 40 attrition.\nProtect your own HQ.",
        "condition": "dismiss",
    },
    {
        "id": "complete",
        "title": "Tutorial Complete!",
        "text": "You're ready to play.\nPress SPACE or click to continue.",
        "condition": "dismiss",
        "final": True,
    },
]


@dataclass
class TutorialController:
    step_index: int = 0
    completed: bool = False
    finished: bool = False
    _prev_turn_signal: int | None = None
    _confirm_prev: bool = False

    def dismiss(self) -> None:
        if self.finished:
            return
        step = STEPS[self.step_index]
        cond = step.get("condition")
        if cond == "dismiss" or cond in ("confirm_present", "turn_change"):
            self._advance()

    def undo(self) -> None:
        if self.finished or self.step_index <= 0:
            return
        self.step_index -= 1
        self._prev_turn_signal = None
        self._confirm_prev = False
        step = STEPS[self.step_index]
        self.completed = bool(step.get("final"))
        print(f"[TUTORIAL] Undo → step {self.step_index}: {step['id']}")

    def tick(
        self,
        p1_tokens: dict,
        p2_tokens: dict,
        current_turn: int | None,
        hq_markers: dict | None = None,
        confirm_present: bool = False,
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
            if self._check_token_condition(condition, p1_tokens, p2_tokens, hq_markers):
                self._advance()

        return self.snapshot()

    def _check_token_condition(
        self,
        condition: dict,
        p1_tokens: dict,
        p2_tokens: dict,
        hq_markers: dict | None = None,
    ) -> bool:
        token_path = condition.get("token", "")
        side, _, role = token_path.partition(".")
        if side not in {"p1", "p2"} or not role:
            return False

        if role == "hq":
            tok = (hq_markers or {}).get(side, {})
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
            "tutorial_gif": step.get("tutorial_gif"),
            "needs_dismiss": cond == "dismiss",
            "allow_skip": cond in ("confirm_present", "turn_change"),
            "can_undo": self.step_index > 0 and not self.finished,
            "completed": self.completed,
        }


def new_tutorial() -> TutorialController:
    return TutorialController()
