from __future__ import annotations

from dataclasses import dataclass

from model_backend.game import PlayerId
from model_backend.game.entities import UnitKind


@dataclass(frozen=True, slots=True)
class TrackedMarker:
    id: int
    player: PlayerId
    label: str
    unit_kind: UnitKind | None = None
    slot_index: int = 0

    @property
    def is_token(self) -> bool:
        return self.unit_kind is not None


TRACKED_MARKERS: tuple[TrackedMarker, ...] = (
    TrackedMarker(id=10, player=PlayerId.P1, unit_kind=UnitKind.ATTACKER, slot_index=0, label="ATK"),
    TrackedMarker(id=14, player=PlayerId.P2, unit_kind=UnitKind.ATTACKER, slot_index=0, label="ATK"),
    TrackedMarker(id=13, player=PlayerId.P1, label="CONFIRM P1"),
    TrackedMarker(id=17, player=PlayerId.P2, label="CONFIRM P2"),
)


MARKER_BY_ID: dict[int, TrackedMarker] = {marker.id: marker for marker in TRACKED_MARKERS}
TOKEN_MARKERS: tuple[TrackedMarker, ...] = tuple(marker for marker in TRACKED_MARKERS if marker.is_token)
TOKEN_IDS: set[int] = {marker.id for marker in TOKEN_MARKERS}
CONFIRM_IDS: set[int] = {marker.id for marker in TRACKED_MARKERS if not marker.is_token}
CONFIRM_PLAYER_MAP: dict[int, int] = {
    marker.id: int(marker.player)
    for marker in TRACKED_MARKERS
    if not marker.is_token
}


def marker_label(marker_id: int) -> str:
    marker = MARKER_BY_ID.get(marker_id)
    if marker is None:
        return f"ID:{marker_id}"
    if marker.unit_kind == UnitKind.ATTACKER:
        return "ATK"
    if marker.unit_kind == UnitKind.DEFENDER:
        return "DEF"
    return marker.label
