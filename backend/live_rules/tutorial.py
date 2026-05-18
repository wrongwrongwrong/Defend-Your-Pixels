"""Tutorial state machine for the live Old Mick runtime."""

from __future__ import annotations

from dataclasses import dataclass

TUTORIAL_SEED = 42

STEPS = [
    {
        "id": "intro",
        "title": "Welcome to Old Mick Against the Mob",
        "text": "In 1932, emus invaded Australian farmland. You are Old Mick, defending your homestead.",
        "condition": "dismiss",
    },
    {
        "id": "scan_board_corners",
        "title": "Scan the Board Corners",
        "text": "Before play, the camera must see all four board corner markers \nWhen the board outline appears in the preview, you are ready to continue.",
        "condition": "dismiss",
        "tutorial_gif": "assets/gif/scan_board_corners.gif",
    },
    {
        "id": "explain_tokens",
        "title": "Your Units",
        "text": "You have 2 Attack tokens (Keith A & B), 1 Defense token (Old Mick yourself), and 1 HQ token.\nAttackers shoot rays. The Defender protects nearby cells. The HQ is your base to protect!",
        "condition": "dismiss",
    },
    {
        "id": "explain_sides_alternate",
        "title": "Who Owns Which Side?",
        "text": "The board is split by a diagonal fence.\nOld Mick (Player 1) controls the bottom-left territory (orange highlight).\nThe Mob (Player 2) controls the top-right territory (green highlight).\nWatch the highlights alternate—you must keep your tokens on your side.",
        "condition": "dismiss",
        "highlight_alternate_sides": True,
    },
    {
        "id": "explain_hq",
        "title": "Headquarters (HQ)",
        "text": "Each player has a hidden HQ. If your HQ is destroyed, you lose!\nPlace your HQ secretly on your side of the board before the game begins.",
        "condition": "dismiss",
    },
    {
        "id": "place_hq_p1",
        "title": "Place Old Mick's HQ",
        "text": "Place your HQ marker (hq_mick) on cell B3 in your territory.\nKeep your HQ location secret from your opponent!",
        "highlight": {"col": 1, "row": 2},
        "condition": "dismiss",
    },
    {
        "id": "explain_turn_marker",
        "title": "The Turn Marker",
        "text": "Turn is driven by which markers the camera sees:\n• Marker #10 scanned → Player 1's turn (Old Mick).\n• Marker #20 scanned → Player 2's turn (The Mob).\n• Marker #4 scanned → the active player ends their turn.",
        "condition": "dismiss",
    },
    {
        "id": "set_turn_p1",
        "title": "Set Turn to Old Mick",
        "text": "Scan turn marker #10 so the camera detects Old Mick's turn before you place attackers.",
        "condition": "turn_change",
        "wait_turn": 1,
    },
    {
        "id": "place_atk_a",
        "title": "Place Your First Attacker",
        "text": "Place Keith A on cell D4 (the highlighted cell).\nPhysically move the ArUco marker onto the board.",
        "highlight": {"col": 3, "row": 3},
        "condition": "dismiss",
    },
    {
        "id": "aim_atk_a",
        "title": "Aim Your Attack",
        "text": "Rotate Keith A to face EAST (right) toward enemy territory.\nThe attack ray will fire in this direction.",
        "highlight": {"col": 3, "row": 3},
        "condition": "dismiss",
        "tutorial_gif": "assets/gif/aim_atk_a.gif",
    },
    {
        "id": "explain_ray",
        "title": "Attack Rays",
        "text": "The green line shows your attack ray. It will hit the first enemy resource cell in its path.",
        "condition": "dismiss",
    },
    {
        "id": "place_atk_b",
        "title": "Place Second Attacker",
        "text": "Now place Keith B on cell C6 (the highlighted cell).",
        "highlight": {"col": 2, "row": 5},
        "condition": "dismiss",
    },
    {
        "id": "aim_atk_b",
        "title": "Aim Second Attacker",
        "text": "Rotate Keith B to face SOUTH-EAST toward enemy territory.",
        "highlight": {"col": 2, "row": 5},
        "condition": "dismiss",
    },
    {
        "id": "place_def",
        "title": "Place Your Defender",
        "text": "Place Old Mick (defender) on cell B5 to protect your resources.",
        "highlight": {"col": 1, "row": 4},
        "condition": "dismiss",
    },
    {
        "id": "explain_defense",
        "title": "Defense Zone",
        "text": "The defender creates a protection zone (yellow glow). Enemy attacks hitting protected cells deal reduced damage.",
        "condition": "dismiss",
    },
    {
        "id": "end_turn",
        "title": "End Your Turn",
        "text": "Scan marker #4 to end your turn.",
        "condition": "confirm_present",
    },
    {
        "id": "wait_opponent",
        "title": "Opponent's Turn",
        "text": "Simulate the opponent taking their turn: scan turn marker #20 so the camera detects The Mob's turn.",
        "condition": "turn_change",
        "wait_turn": 2,
    },
    {
        "id": "explain_tiers",
        "title": "Tier System",
        "text": "Destroying enemy resources earns points. At 6/14/22/32 points, you gain Tier upgrades:\n- Tier 1+: Splash damage\n- Tier 2+: Larger defense zone\n- Tier 4: Unlocks Nuke!",
        "condition": "dismiss",
    },
    {
        "id": "explain_win",
        "title": "How to Win",
        "text": "Win by destroying the enemy's hidden HQ, or reaching 40 attrition points.\nProtect your own HQ at all costs!",
        "condition": "dismiss",
    },
    {
        "id": "complete",
        "title": "Tutorial Complete!",
        "text": "You now know the basics. Press SPACE or click once more to continue straight into the live game.",
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
        # Dismiss-only steps, or skip past gated steps (confirm / turn) via Space / UI.
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
