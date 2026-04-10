from __future__ import annotations

"""
Tracker -> model synchronization adapter.

Goal:
- The camera/tracker is NOT authoritative.
- It proposes move intents derived from detected marker positions.
- The authoritative `GameState` still validates those intents.

Output of this module:
- a list of action dicts compatible with `bridge/actions/model_action_dispatcher.apply_action`
- a metadata dict keyed by unit_id (e.g. rotation degrees) for UI/telemetry
"""

from model_backend.game import GameState, PlayerId, Pos, TerrainType
from model_backend.game.entities import Unit, UnitKind


MarkerRole = tuple[PlayerId, UnitKind]
TrackerAction = dict[str, object]
UnitMetadata = dict[str, dict[str, float]]

# Mapping of ArUco marker IDs to (player, unit kind).
# This is a prototype convention shared with the live tracker runner printout.
_MARKER_TO_ROLE: dict[int, MarkerRole] = {
    10: (PlayerId.P1, UnitKind.ATTACKER),
    11: (PlayerId.P1, UnitKind.DEFENDER),
    12: (PlayerId.P1, UnitKind.ATTACKER),
    13: (PlayerId.P1, UnitKind.DEFENDER),
    14: (PlayerId.P2, UnitKind.ATTACKER),
    15: (PlayerId.P2, UnitKind.DEFENDER),
    16: (PlayerId.P2, UnitKind.ATTACKER),
    17: (PlayerId.P2, UnitKind.DEFENDER),
}


def build_tracker_move_actions(game: GameState, snapshot: dict) -> tuple[list[TrackerAction], UnitMetadata]:
    """Build `move_unit` actions from the latest tracker snapshot.

    The tracker is not authoritative. It only proposes move intents for the
    current player's units, and the Python model still validates each move.
    """
    # If calibration isn't ready, we don't trust marker positions yet.
    if not snapshot.get("calibration_ready"):
        return [], {}

    # Associate one model unit to each tracker "role" (P1 attacker, P2 defender, etc).
    # This intentionally limits to 1 unit per kind per player for the prototype.
    units_by_role = _build_units_by_role(game)
    pending_actions: list[TrackerAction] = []
    unit_metadata: UnitMetadata = {}
    claimed_positions: set[Pos] = set()

    # Iterate markers from the tracker snapshot and translate them into proposed moves.
    for marker in snapshot.get("markers", []):
        # Identify which unit (role) this physical marker corresponds to.
        role = _MARKER_TO_ROLE.get(marker.get("id"))
        if role is None:
            continue

        # Convert marker payload -> model entities / types.
        unit = units_by_role.get(role)
        position = _coerce_grid_position(marker.get("position"))
        if unit is None or position is None:
            continue

        # Record rotation and other per-unit metadata even if we don't move.
        unit_metadata[unit.id] = _build_unit_metadata(marker)

        # Only allow the active player to propose moves this tick.
        if unit.owner != game.active_player:
            continue
        # If the marker hasn't moved grid cells, treat it as "claimed" to prevent
        # another marker from taking its square in the same tick.
        if position == unit.pos:
            claimed_positions.add(position)
            continue

        # Reject illegal placements early (bounds, collisions, towers, obstacles, blocked terrain).
        if not _can_place_unit(game, unit, position, claimed_positions):
            continue

        # Reserve the position so multiple markers don't generate conflicting actions.
        claimed_positions.add(position)
        # Emit a move action; GameState will validate movement points and apply if legal.
        pending_actions.append(_build_move_action(unit, position))

    return pending_actions, unit_metadata


def _build_units_by_role(game: GameState) -> dict[MarkerRole, Unit]:
    """Map one model unit to each tracker marker role."""
    units_by_role: dict[MarkerRole, Unit] = {}
    for unit in game.units.values():
        # Use setdefault so the first matching unit "wins" for a given role.
        units_by_role.setdefault((unit.owner, unit.kind), unit)
    return units_by_role


def _build_unit_metadata(marker: dict) -> dict[str, float]:
    # The tracker reports rotation in degrees. Keep it as a float for downstream use.
    return {"rotation_deg": _coerce_rotation(marker.get("rotation"))}


def _build_move_action(unit: Unit, position: Pos) -> TrackerAction:
    # This payload shape matches `model_action_dispatcher.apply_action` expectations.
    return {
        "action": "move_unit",
        "unit_id": unit.id,
        "position": {"x": position.x, "y": position.y},
        "source": "tracker",
    }


def _coerce_grid_position(position: dict | None) -> Pos | None:
    # Tracker positions may be floats; round to nearest grid cell for the model.
    if not isinstance(position, dict):
        return None

    x = position.get("x")
    y = position.get("y")
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        return None

    return Pos(int(round(x)), int(round(y)))


def _coerce_rotation(rotation: object) -> float:
    # Keep a predictable numeric type; missing/invalid rotation becomes 0.0.
    if isinstance(rotation, (int, float)):
        return float(rotation)
    return 0.0


def _can_place_unit(game: GameState, unit: Unit, position: Pos, reserved_positions: set[Pos]) -> bool:
    # Basic grid constraints.
    if not game.board.in_bounds(position):
        return False
    if position in reserved_positions:
        return False

    # Can't overlap another unit (except itself).
    occupant = game.unit_at(position)
    if occupant is not None and occupant.id != unit.id:
        return False

    # Can't stand on top of a command tower.
    tower = game.tower_at(position)
    if tower is not None:
        return False

    # Can't stand on a blocking obstacle.
    obstacle = game.obstacle_at(position)
    if obstacle is not None:
        return False

    # Can't move onto blocked terrain.
    terrain = game.board.get(position).terrain
    return terrain != TerrainType.BLOCKED
