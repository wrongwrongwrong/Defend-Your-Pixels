from __future__ import annotations

from model_backend.game import GameState, PlayerId


def serialize_game_state(game: GameState, unit_metadata: dict[str, dict] | None = None) -> dict:
    unit_metadata = unit_metadata or {}

    return {
        "turn": int(game.turn),
        "active_player": int(game.active_player),
        "game_over": bool(game.game_over),
        "winner": int(game.winner) if game.winner is not None else None,
        "last_action": game.last_action,
        "players": [_serialize_player(game, player_id) for player_id in (PlayerId.P1, PlayerId.P2)],
        "units": [_serialize_unit(unit, unit_metadata.get(unit.id, {})) for unit in game.units.values()],
    }


def _serialize_player(game: GameState, player_id: PlayerId) -> dict:
    player = game.players[player_id]
    tower = game.towers.get(player_id)

    return {
        "id": int(player_id),
        "ether": int(player.ether),
        "income_per_turn": int(player.income_per_turn),
        "command_tower_hp": int(tower.hp) if tower is not None else 0,
        "command_tower_max_hp": int(tower.max_hp) if tower is not None else 0,
    }


def _serialize_unit(unit, metadata: dict) -> dict:
    payload = {
        "id": str(unit.id),
        "owner": int(unit.owner),
        "kind": unit.kind.value,
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
