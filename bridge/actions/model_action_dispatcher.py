from __future__ import annotations

from model_backend.game import GameState, Pos


def apply_action(game: GameState, action: dict) -> bool:
    if not isinstance(action, dict):
        game.last_action = "Ignored malformed action payload"
        return False

    action_type = action.get("action")

    if action_type == "end_turn":
        if game.game_over:
            game.last_action = "Cannot end turn after game over"
            return False
        game.end_turn()
        return True

    if action_type == "upgrade_unit":
        unit_id = action.get("unit_id")
        upgrade_type = action.get("upgrade_type")
        game.last_action = f"Upgrade not implemented in Python prototype: {unit_id} / {upgrade_type}"
        return False

    if action_type == "move_unit":
        unit_id = action.get("unit_id")
        position = action.get("position")
        if not isinstance(unit_id, str):
            game.last_action = "move_unit missing unit_id"
            return False
        if not isinstance(position, dict):
            game.last_action = f"move_unit missing position for {unit_id}"
            return False

        x = position.get("x")
        y = position.get("y")
        if not isinstance(x, int) or not isinstance(y, int):
            game.last_action = f"move_unit invalid position for {unit_id}"
            return False
        if unit_id not in game.units:
            game.last_action = f"Unknown unit: {unit_id}"
            return False

        ok = game.move_unit_to(unit_id, Pos(x, y))
        if not ok:
            game.last_action = f"{unit_id} could not move to ({x}, {y})"
        return ok

    if action_type == "capture":
        unit_id = action.get("unit_id")
        if not isinstance(unit_id, str):
            game.last_action = "capture missing unit_id"
            return False
        if unit_id not in game.units:
            game.last_action = f"Unknown unit: {unit_id}"
            return False

        ok = game.capture(unit_id)
        if not ok:
            unit = game.units[unit_id]
            game.last_action = f"{unit_id} could not capture at ({unit.pos.x}, {unit.pos.y})"
        return ok

    if action_type == "act_on_target":
        unit_id = action.get("unit_id")
        target = action.get("target")
        if not isinstance(unit_id, str):
            game.last_action = "act_on_target missing unit_id"
            return False
        if not isinstance(target, dict):
            game.last_action = f"act_on_target missing target for {unit_id}"
            return False

        x = target.get("x")
        y = target.get("y")
        if not isinstance(x, int) or not isinstance(y, int):
            game.last_action = f"act_on_target invalid target for {unit_id}"
            return False
        if unit_id not in game.units:
            game.last_action = f"Unknown unit: {unit_id}"
            return False

        ok = game.act_on_target(unit_id, Pos(x, y))
        if not ok:
            game.last_action = f"{unit_id} could not act on ({x}, {y})"
        return ok

    game.last_action = f"Unknown action: {action_type}"
    return False
