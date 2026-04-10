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
    if action_type == "upgrade_unit":
        return _apply_upgrade_unit(game, action)
    if action_type == "move_unit":
        return _apply_move_unit(game, action)
    if action_type == "capture":
        return _apply_capture(game, action)
    if action_type == "act_on_target":
        return _apply_act_on_target(game, action)

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


def _apply_upgrade_unit(game: GameState, action: dict) -> bool:
    # Placeholder: the React UI currently has upgrade buttons, but the Python prototype
    # hasn't implemented an upgrade system yet. Keep the action wired for future work.
    unit_id = action.get("unit_id")
    upgrade_type = action.get("upgrade_type")
    return _reject(
        game,
        f"Upgrade not implemented in Python prototype: {unit_id} / {upgrade_type}",
    )


def _apply_move_unit(game: GameState, action: dict) -> bool:
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


def _apply_capture(game: GameState, action: dict) -> bool:
    # Capture is validated by the model (e.g. must be on a drill, must be allowed).
    unit_id = _require_known_unit(game, action, "capture")
    if unit_id is None:
        return False

    ok = game.capture(unit_id)
    if ok:
        # Quality-of-life: if capture succeeded, stop the "move countdown" state so
        # that the UI can proceed without waiting for tracker stabilization.
        game.clear_move_countdown()
        return True

    # If capture fails, we can include the unit's current position to help debugging.
    unit = game.units[unit_id]
    return _reject(game, f"{unit_id} could not capture at ({unit.pos.x}, {unit.pos.y})")


def _apply_act_on_target(game: GameState, action: dict) -> bool:
    # Act-on-target covers attacks and interactions that require a target grid cell.
    unit_id = _require_known_unit(game, action, "act_on_target")
    if unit_id is None:
        return False

    target = _require_pos(game, action, field_name="target", action_name="act_on_target")
    if target is None:
        return False

    # The model decides whether this action is legal and applies damage/effects.
    ok = game.act_on_target(unit_id, target)
    if not ok:
        return _reject(game, f"{unit_id} could not act on ({target.x}, {target.y})")
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
