"""
Tutorial state machine for Old Mick Against the Mob.

Monitors tracker data and advances through predefined tutorial steps
when conditions are met. The tutorial state is broadcast to the frontend
for rendering hints and highlights.
"""

from dataclasses import dataclass, field
from typing import Any

TUTORIAL_SEED = 42  # Fixed seed ensures predictable terrain

# Tutorial step definitions
# Each step has:
#   - id: unique identifier
#   - title: heading text
#   - text: instruction text
#   - highlight: optional {col, row} to highlight on board
#   - condition: how to advance (token position, direction, turn change, or "dismiss")
STEPS = [
    {
        "id": "intro",
        "title": "Welcome to Old Mick Against the Mob",
        "text": "In 1932, emus invaded Australian farmland. You are Old Mick, defending your homestead.",
        "condition": "dismiss",
    },
    {
        "id": "explain_board",
        "title": "The Battlefield",
        "text": "The board is split diagonally. Old Mick (orange) owns the bottom-left, The Mob (green) owns the top-right.",
        "condition": "dismiss",
    },
    {
        "id": "explain_tokens",
        "title": "Your Units",
        "text": "You have 2 Attack tokens (Keith A & B), 1 Defense token (Old Mick himself), and 1 HQ token.\nAttackers shoot rays. The Defender protects nearby cells. The HQ is your base to protect!",
        "condition": "dismiss",
    },
    # ─── HQ Setup ───────────────────────────────────────────────────────────
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
        "condition": {"token": "p1.hq", "col": 1, "row": 2},
    },
    # ─── Turn Marker Setup ──────────────────────────────────────────────────
    {
        "id": "explain_turn_marker",
        "title": "The Turn Marker",
        "text": "The turn marker is a cube. The camera detects the top face and its rotation angle.\nP1's turn: marker #10 face up, rotated so the marker reads upright.\nP2's turn: same face, rotated 180° (upside-down).",
        "condition": "dismiss",
    },
    {
        "id": "set_turn_p1",
        "title": "Set Turn to Old Mick",
        "text": "Place the cube with marker #10 face up, rotated so the marker appears upright to the camera.\nThe system will detect it as Old Mick's turn.",
        "condition": "turn_change",
        "wait_turn": 1,  # Wait for turn to become P1's
    },
    # ─── Attack Token Placement ─────────────────────────────────────────────
    {
        "id": "place_atk_a",
        "title": "Place Your First Attacker",
        "text": "Place Keith A on cell D4 (the highlighted cell).\nPhysically move the ArUco marker onto the board.",
        "highlight": {"col": 3, "row": 3},
        "condition": {"token": "p1.atk_a", "col": 3, "row": 3},
    },
    {
        "id": "aim_atk_a",
        "title": "Aim Your Attack",
        "text": "Rotate Keith A to face EAST (right) toward enemy territory.\nThe attack ray will fire in this direction.",
        "highlight": {"col": 3, "row": 3},
        "condition": {"token": "p1.atk_a", "direction": "E"},
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
        "condition": {"token": "p1.atk_b", "col": 2, "row": 5},
    },
    {
        "id": "aim_atk_b",
        "title": "Aim Second Attacker",
        "text": "Rotate Keith B to face SOUTH-EAST toward enemy territory.",
        "highlight": {"col": 2, "row": 5},
        "condition": {"token": "p1.atk_b", "direction": "SE"},
    },
    {
        "id": "place_def",
        "title": "Place Your Defender",
        "text": "Place Old Mick (defender) on cell B5 to protect your resources.",
        "highlight": {"col": 1, "row": 4},
        "condition": {"token": "p1.def", "col": 1, "row": 4},
    },
    {
        "id": "explain_defense",
        "title": "Defense Zone",
        "text": "The defender creates a protection zone (yellow glow). Enemy attacks hitting protected cells deal reduced damage.",
        "condition": "dismiss",
    },
    # ─── End Turn ───────────────────────────────────────────────────────────
    {
        "id": "end_turn",
        "title": "End Your Turn",
        "text": "Rotate the turn marker cube 180° (so marker #10 appears upside-down).\nYour attacks will resolve and it becomes The Mob's turn.",
        "condition": "turn_change",
        "wait_turn": 2,  # Wait for turn to become P2's
    },
    {
        "id": "wait_opponent",
        "title": "Opponent's Turn",
        "text": "The Mob is now playing. In a real game, your opponent would place their tokens.\nRotate the turn marker 180° again to return to Old Mick's turn.",
        "condition": "turn_change",
        "wait_turn": 1,  # Wait for turn to return to P1
    },
    # ─── Game Mechanics ─────────────────────────────────────────────────────
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
        "text": "You now know the basics. Good luck defending your homestead!",
        "condition": "dismiss",
        "final": True,
    },
]


@dataclass
class TutorialController:
    """
    Manages tutorial progression based on tracker input.
    """
    step_index: int = 0
    dismissed: bool = False
    last_turn: int | None = None
    completed: bool = False

    def dismiss(self) -> None:
        """Called when user presses space/clicks to dismiss current step."""
        step = STEPS[self.step_index]
        if step.get("condition") == "dismiss":
            self._advance()

    def tick(self, p1_tokens: dict, p2_tokens: dict, current_turn: int | None,
             hq_markers: dict | None = None) -> dict:
        """
        Check conditions and return current tutorial state.
        Called every frame with tracker data.
        
        Args:
            p1_tokens: P1 token positions {atk_a, atk_b, def}
            p2_tokens: P2 token positions {atk_a, atk_b, def}
            current_turn: Current turn (1 or 2)
            hq_markers: HQ marker positions {"p1": {col, row, stale}, "p2": {...}}
        """
        if self.completed:
            return self.snapshot()

        step = STEPS[self.step_index]
        condition = step.get("condition")

        # Check condition based on type
        if condition == "dismiss":
            # Handled by dismiss() method - wait for user input
            pass
        elif condition == "turn_change":
            wait_turn = step.get("wait_turn")
            if self.last_turn is None:
                self.last_turn = current_turn
            elif current_turn is not None and current_turn != self.last_turn:
                if wait_turn is None or current_turn == wait_turn:
                    self._advance()
                self.last_turn = current_turn
        elif isinstance(condition, dict):
            if self._check_token_condition(condition, p1_tokens, p2_tokens, hq_markers):
                self._advance()

        return self.snapshot()

    def _check_token_condition(self, condition: dict, p1: dict, p2: dict,
                               hq_markers: dict | None = None) -> bool:
        """Check if a token meets the specified condition."""
        token_path = condition.get("token", "")
        parts = token_path.split(".")
        if len(parts) != 2:
            return False

        side, role = parts
        
        # Handle HQ markers separately (they come from hq_markers, not p1/p2)
        if role == "hq":
            if not hq_markers:
                return False
            tok = hq_markers.get(side, {})
        else:
            tokens = p1 if side == "p1" else p2
            tok = tokens.get(role, {}) if tokens else {}

        if tok is None or tok.get("col") is None:
            return False

        # Check position condition
        if "col" in condition and "row" in condition:
            if tok.get("col") != condition["col"] or tok.get("row") != condition["row"]:
                return False

        # Check direction condition (not applicable for HQ)
        if "direction" in condition:
            if tok.get("direction") != condition["direction"]:
                return False

        return True

    def _advance(self) -> None:
        """Move to next step."""
        if self.step_index < len(STEPS) - 1:
            self.step_index += 1
            self.dismissed = False
            step = STEPS[self.step_index]
            if step.get("final"):
                self.completed = True
            print(f"[TUTORIAL] Advanced to step {self.step_index}: {STEPS[self.step_index]['id']}")

    def snapshot(self) -> dict:
        """Return state to send to frontend."""
        step = STEPS[self.step_index]
        return {
            "active": True,
            "step_index": self.step_index,
            "total_steps": len(STEPS),
            "step_id": step["id"],
            "title": step.get("title", ""),
            "text": step.get("text", ""),
            "highlight": step.get("highlight"),
            "needs_dismiss": step.get("condition") == "dismiss",
            "completed": self.completed,
        }


def new_tutorial() -> TutorialController:
    """Create a new tutorial controller."""
    return TutorialController()
