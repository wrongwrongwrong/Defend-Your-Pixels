from __future__ import annotations

from model_backend.game import GameState, PlayerId, Pos, TerrainType
from model_backend.game.entities import UnitKind


_MARKER_TO_ROLE = {
    10: (PlayerId.P1, UnitKind.ATTACKER),
    11: (PlayerId.P1, UnitKind.DEFENDER),
    12: (PlayerId.P1, UnitKind.ATTACKER),
    13: (PlayerId.P1, UnitKind.DEFENDER),
    14: (PlayerId.P2, UnitKind.ATTACKER),
    15: (PlayerId.P2, UnitKind.DEFENDER),
    16: (PlayerId.P2, UnitKind.ATTACKER),
    17: (PlayerId.P2, UnitKind.DEFENDER),
}


def build_tracker_move_actions(game: GameState, snapshot: dict) -> tuple[list[dict], dict[str, dict]]:
    if not snapshot.get("calibration_ready"):
        return [], {}

    units_by_role = _build_units_by_role(game)
    actions: list[dict] = []
    unit_metadata: dict[str, dict] = {}
    reserved_positions: set[Pos] = set()

    for marker in snapshot.get("markers", []):
        role = _MARKER_TO_ROLE.get(marker.get("id"))
        if role is None:
            continue

        unit = units_by_role.get(role)
        position = _coerce_grid_position(marker.get("position"))
        if unit is None or position is None:
            continue

        unit_metadata[unit.id] = {
            "rotation_deg": _coerce_rotation(marker.get("rotation")),
        }

        if unit.owner != game.active_player:
            continue
        if position == unit.pos:
            reserved_positions.add(position)
            continue

        if not _can_place_unit(game, unit, position, reserved_positions):
            continue

        reserved_positions.add(position)
        actions.append(
            {
                "action": "move_unit",
                "unit_id": unit.id,
                "position": {"x": position.x, "y": position.y},
                "source": "tracker",
            }
        )

    return actions, unit_metadata


def _build_units_by_role(game: GameState) -> dict[tuple[PlayerId, UnitKind], object]:
    units_by_role: dict[tuple[PlayerId, UnitKind], object] = {}
    for unit in game.units.values():
        units_by_role.setdefault((unit.owner, unit.kind), unit)
    return units_by_role


def _coerce_grid_position(position: dict | None) -> Pos | None:
    if not isinstance(position, dict):
        return None

    x = position.get("x")
    y = position.get("y")
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        return None

    return Pos(int(round(x)), int(round(y)))


def _coerce_rotation(rotation: object) -> float:
    if isinstance(rotation, (int, float)):
        return float(rotation)
    return 0.0


def _can_place_unit(game: GameState, unit, position: Pos, reserved_positions: set[Pos]) -> bool:
    if not game.board.in_bounds(position):
        return False
    if position in reserved_positions:
        return False

    occupant = game.unit_at(position)
    if occupant is not None and occupant.id != unit.id:
        return False

    tower = game.tower_at(position)
    if tower is not None:
        return False

    obstacle = game.obstacle_at(position)
    if obstacle is not None:
        return False

    terrain = game.board.get(position).terrain
    return terrain != TerrainType.BLOCKED
