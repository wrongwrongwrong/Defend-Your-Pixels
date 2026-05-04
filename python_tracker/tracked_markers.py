from __future__ import annotations

from dataclasses import dataclass

from model_backend.game import PlayerId
from model_backend.game.entities import UnitKind


@dataclass(frozen=True, slots=True)
class TrackedMarker:
    id: int
    player: PlayerId | None
    label: str
    unit_kind: UnitKind | None = None
    slot_index: int = 0

    @property
    def is_token(self) -> bool:
        return self.unit_kind is not None


TRACKED_MARKERS: tuple[TrackedMarker, ...] = (
    TrackedMarker(id=10, player=PlayerId.P1, unit_kind=UnitKind.ATTACKER, slot_index=0, label="ATK A"),
    TrackedMarker(id=11, player=PlayerId.P1, unit_kind=UnitKind.ATTACKER, slot_index=1, label="ATK B"),
    TrackedMarker(id=12, player=PlayerId.P1, unit_kind=UnitKind.DEFENDER, slot_index=0, label="DEF"),
    TrackedMarker(id=13, player=None, label="TURN"),
    TrackedMarker(id=14, player=PlayerId.P2, unit_kind=UnitKind.ATTACKER, slot_index=0, label="ATK A"),
    TrackedMarker(id=15, player=PlayerId.P2, unit_kind=UnitKind.ATTACKER, slot_index=1, label="ATK B"),
    TrackedMarker(id=16, player=PlayerId.P2, unit_kind=UnitKind.DEFENDER, slot_index=0, label="DEF"),
)


MARKER_BY_ID: dict[int, TrackedMarker] = {marker.id: marker for marker in TRACKED_MARKERS}
TOKEN_MARKERS: tuple[TrackedMarker, ...] = tuple(marker for marker in TRACKED_MARKERS if marker.is_token)
TOKEN_IDS: set[int] = {marker.id for marker in TOKEN_MARKERS}
TURN_MARKER_ID = 13


def marker_label(marker_id: int) -> str:
    marker = MARKER_BY_ID.get(marker_id)
    if marker is None:
        return f"ID:{marker_id}"
    if marker.id == TURN_MARKER_ID:
        return marker.label
    if marker.unit_kind == UnitKind.ATTACKER:
        return marker.label
    if marker.unit_kind == UnitKind.DEFENDER:
        return marker.label
    return marker.label
