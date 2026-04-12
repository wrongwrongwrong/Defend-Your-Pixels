from __future__ import annotations

"""
Action dispatcher for the bridge layer.

This file is the "thin controller" between:
- inbound WebSocket `action` messages (already parsed into Python dicts)
- the authoritative rules engine in `model_backend.game.GameState`

Important design constraints:
- The model remains authoritative (all validation happens in GameState methods).
- The dispatcher only performs minimal shape/type checks and converts payloads
  into the model's Python types (e.g. `Pos`).
"""

from model_backend.game import GameState, Pos


def apply_action(game: GameState, action: dict) -> bool:
    """Validate an incoming action payload and dispatch it to `GameState`.

    Returns:
        True  -> action was accepted and applied to the model
        False -> action was rejected; rejection reason is written to `game.last_action`
    """
    # Defensive programming: the transport layer can hand us anything.
    if not isinstance(action, dict):
        return _reject(game, "Ignored malformed action payload")

    # `action` is the "verb" that determines the handler.
    action_type = action.get("action")

    # Each branch validates required fields and calls the corresponding model method.
    if action_type == "end_turn":
        return _apply_end_turn(game)
    if action_type == "move_unit":
        return _apply_move_unit(game, action)

    # Unknown verbs are rejected to keep the model safe and make debugging explicit.
    return _reject(game, f"Unknown action: {action_type}")


def _apply_end_turn(game: GameState) -> bool:
    # Bridge-level guardrails: don't even call into the model if the turn cannot end.
    # (These checks mirror the UI constraints and keep `last_action` meaningful.)
    if game.game_over:
        return _reject(game, "Cannot end turn after game over")
    if game.move_countdown_active:
        return _reject(game, "Cannot end turn while move countdown is active")

    # The model updates: active_player, turn counter, income, per-unit new_turn, etc.
    game.end_turn()
    return True
def _apply_move_unit(game: GameState, action: dict) -> bool:
    if game.move_countdown_active:
        return _reject(game, "Cannot move another unit while move countdown is active")

    # Move is a two-step validation:
    # 1) we must know which unit is being moved
    # 2) we must have a valid {x,y} grid position
    unit_id = _require_known_unit(game, action, "move_unit")
    if unit_id is None:
        return False

    position = _require_pos(game, action, field_name="position", action_name="move_unit")
    if position is None:
        return False

    # The model enforces bounds, collisions, movement points, terrain rules, etc.
    ok = game.move_unit_to(unit_id, position)
    if not ok:
        return _reject(game, f"{unit_id} could not move to ({position.x}, {position.y})")
    return True


def _require_known_unit(game: GameState, action: dict, action_name: str) -> str | None:
    # All unit-referencing actions must include a string `unit_id`.
    unit_id = action.get("unit_id")
    if not isinstance(unit_id, str):
        _reject(game, f"{action_name} missing unit_id")
        return None
    # Reject unknown IDs so the model doesn't have to guard every lookup.
    if unit_id not in game.units:
        _reject(game, f"Unknown unit: {unit_id}")
        return None
    return unit_id


def _require_pos(game: GameState, action: dict, *, field_name: str, action_name: str) -> Pos | None:
    # Positions are expected as `{ "x": int, "y": int }` in grid coordinates.
    unit_id = action.get("unit_id")
    raw_position = action.get(field_name)
    if not isinstance(raw_position, dict):
        suffix = f" for {unit_id}" if isinstance(unit_id, str) else ""
        _reject(game, f"{action_name} missing {field_name}{suffix}")
        return None

    x = raw_position.get("x")
    y = raw_position.get("y")
    if not isinstance(x, int) or not isinstance(y, int):
        suffix = f" for {unit_id}" if isinstance(unit_id, str) else ""
        _reject(game, f"{action_name} invalid {field_name}{suffix}")
        return None

    # Convert transport payload into the model's strongly-typed `Pos`.
    return Pos(x, y)


def _reject(game: GameState, message: str) -> bool:
    # `last_action` is shown by the UI as a status text; store human-readable context.
    game.last_action = message
    return False
