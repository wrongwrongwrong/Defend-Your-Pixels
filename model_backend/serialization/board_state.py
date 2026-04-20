from __future__ import annotations

"""Serialize the authoritative Python model into the board_state payload."""

from model_backend.game import GameState, PlayerId
from model_backend.game.entities import themed_hq_name, themed_resource_name


def serialize_game_state(game: GameState, unit_metadata: dict[str, dict] | None = None) -> dict:
    """Return the snake_case payload consumed by the bridge and React adapter.

    This is the boundary between Python model internals and transport/UI code. The
    payload is intentionally plain data so downstream layers never inspect model
    objects directly.
    """
    unit_metadata = unit_metadata or {}

    return {
        "turn": int(game.turn),
        "active_player": int(game.active_player),
        "game_over": bool(game.game_over),
        "winner": int(game.winner) if game.winner is not None else None,
        "last_action": game.last_action,
        "move_countdown": _serialize_move_countdown(game),
        "players": [_serialize_player(game, player_id) for player_id in (PlayerId.P1, PlayerId.P2)],
        "units": [_serialize_unit(unit, unit_metadata.get(unit.id, {})) for unit in game.units.values()],
    }


def _serialize_move_countdown(game: GameState) -> dict:
    return {
        "active": game.move_countdown_active,
        "seconds_remaining": game.move_countdown_seconds_remaining(),
        "duration_seconds": float(game.MOVE_COUNTDOWN_SECONDS),
        "unit_id": game.move_countdown_unit_id,
    }


def _serialize_player(game: GameState, player_id: PlayerId) -> dict:
    """Serialize one player's economy and tower summary."""
    player = game.players[player_id]
    tower = game.towers.get(player_id)

    return {
        "id": int(player_id),
        "ether": int(player.ether),
        "income_per_turn": int(player.income_per_turn),
        "hq_name": themed_hq_name(player_id),
        "resource_name": themed_resource_name(player_id),
        "command_tower_hp": int(tower.hp) if tower is not None else 0,
        "command_tower_max_hp": int(tower.max_hp) if tower is not None else 0,
        "command_tower_position": _serialize_position(tower.pos) if tower is not None else None,
    }


def _serialize_unit(unit, metadata: dict) -> dict:
    """Serialize a unit plus any tracker-derived metadata such as rotation.

    Rotation is not authoritative gameplay state today, but keeping it here lets the
    frontend render the physical token orientation next to authoritative positions.
    """
    payload = {
        "id": str(unit.id),
        "owner": int(unit.owner),
        "kind": unit.kind.value,
        "theme_name": unit.theme_name,
        "position": {
            "x": int(unit.pos.x),
            "y": int(unit.pos.y),
        },
        "hp": int(unit.hp),
        "max_hp": int(unit.max_hp),
    }

    rotation_deg = metadata.get("rotation_deg")
    if isinstance(rotation_deg, (int, float)):
        payload["rotation_deg"] = float(rotation_deg)

    return payload


def _serialize_position(pos) -> dict:
    return {
        "x": int(pos.x),
        "y": int(pos.y),
    }
