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

from collections import defaultdict

from model_backend.game import GameState, PlayerId, Pos, TerrainType
from model_backend.game.entities import Unit, UnitKind


MarkerSlot = tuple[PlayerId, UnitKind, int]
TrackerAction = dict[str, object]
UnitMetadata = dict[str, dict[str, float]]
_STABLE_FRAMES_REQUIRED = 3
_CELL_SWITCH_THRESHOLD = 0.75
_MARKER_POSITION_HISTORY: dict[int, tuple[Pos, int]] = {}

# Mapping of ArUco marker IDs to (player, unit kind, ordinal within that kind).
# This is a prototype convention shared with the live tracker runner printout.
_MARKER_TO_SLOT: dict[int, MarkerSlot] = {
    10: (PlayerId.P1, UnitKind.ATTACKER, 0),
    # 11: (PlayerId.P1, UnitKind.ATTACKER, 1),
    # 12: (PlayerId.P1, UnitKind.DEFENDER, 0),
    # 13: (PlayerId.P1, UnitKind.DEFENDER, 1),
    14: (PlayerId.P2, UnitKind.ATTACKER, 0),
    # 15: (PlayerId.P2, UnitKind.ATTACKER, 1),
    # 16: (PlayerId.P2, UnitKind.DEFENDER, 0),
    # 17: (PlayerId.P2, UnitKind.DEFENDER, 1),
}


def build_tracker_move_actions(game: GameState, snapshot: dict) -> tuple[list[TrackerAction], UnitMetadata]:
    """Build `move_unit` actions from the latest tracker snapshot.

    The tracker is not authoritative. It only proposes move intents for the
    current player's units, and the Python model still validates each move.
    """
    # If calibration isn't ready, we don't trust marker positions yet.
    if not snapshot.get("calibration_ready"):
        _MARKER_POSITION_HISTORY.clear()
        return [], {}

    # Associate each physical marker with one model unit slot.
    units_by_slot = _build_units_by_slot(game)
    pending_actions: list[TrackerAction] = []
    unit_metadata: UnitMetadata = {}
    claimed_positions: set[Pos] = set()

    # Iterate markers from the tracker snapshot and translate them into proposed moves.
    for marker in snapshot.get("markers", []):
        # Identify which unit (role) this physical marker corresponds to.
        slot = _MARKER_TO_SLOT.get(marker.get("id"))
        if slot is None:
            continue

        # Convert marker payload -> model entities / types.
        unit = units_by_slot.get(slot)
        position = _coerce_grid_position(unit, marker.get("position"))
        if unit is None or position is None:
            continue

        stable_position = _stabilize_marker_position(int(marker["id"]), position)

        # Record rotation and other per-unit metadata even if we don't move.
        unit_metadata[unit.id] = _build_unit_metadata(marker)

        # Only allow the active player to propose moves this tick.
        if unit.owner != game.active_player:
            continue
        # If the marker hasn't moved grid cells, treat it as "claimed" to prevent
        # another marker from taking its square in the same tick.
        if stable_position is None:
            continue
        if stable_position == unit.pos:
            claimed_positions.add(stable_position)
            continue

        # Reject illegal placements early (bounds, collisions, towers, obstacles, blocked terrain).
        if not _can_place_unit(game, unit, stable_position, claimed_positions):
            continue

        # Reserve the position so multiple markers don't generate conflicting actions.
        claimed_positions.add(stable_position)
        # Emit a move action; GameState will validate movement points and apply if legal.
        pending_actions.append(_build_move_action(unit, stable_position))

    return pending_actions, unit_metadata


def _build_units_by_slot(game: GameState) -> dict[MarkerSlot, Unit]:
    """Map each marker slot to a deterministic unit for that player/kind."""
    grouped_units: dict[tuple[PlayerId, UnitKind], list[Unit]] = defaultdict(list)
    for unit in game.units.values():
        grouped_units[(unit.owner, unit.kind)].append(unit)

    units_by_slot: dict[MarkerSlot, Unit] = {}
    for (owner, kind), units in grouped_units.items():
        ordered_units = sorted(units, key=lambda unit: (unit.pos.x, unit.pos.y, unit.id))
        for index, unit in enumerate(ordered_units):
            units_by_slot[(owner, kind, index)] = unit
    return units_by_slot


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


def _coerce_grid_position(unit: Unit, position: dict | None) -> Pos | None:
    # Tracker positions may be floats; resolve them with hysteresis so tokens don't
    # bounce across grid edges while hovering near a boundary.
    if not isinstance(position, dict):
        return None

    x = position.get("x")
    y = position.get("y")
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        return None

    return Pos(_resolve_axis(unit.pos.x, float(x)), _resolve_axis(unit.pos.y, float(y)))


def _coerce_rotation(rotation: object) -> float:
    # Keep a predictable numeric type; missing/invalid rotation becomes 0.0.
    if isinstance(rotation, (int, float)):
        return float(rotation)
    return 0.0


def _stabilize_marker_position(marker_id: int, position: Pos) -> Pos | None:
    # Require the same cell to be observed for a few consecutive frames before
    # emitting a move intent. This avoids accidental moves from noisy detections.
    previous = _MARKER_POSITION_HISTORY.get(marker_id)
    if previous is None or previous[0] != position:
        _MARKER_POSITION_HISTORY[marker_id] = (position, 1)
        return None

    count = previous[1] + 1
    _MARKER_POSITION_HISTORY[marker_id] = (position, count)
    if count < _STABLE_FRAMES_REQUIRED:
        return None
    return position


def _resolve_axis(current: int, measured: float) -> int:
    # Keep the current cell until the measured token center clearly crosses into the
    # neighboring cell; this hysteresis reduces boundary jitter.
    if abs(measured - current) < _CELL_SWITCH_THRESHOLD:
        return current
    return int(round(measured))


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
