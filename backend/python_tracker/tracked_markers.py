from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum


class MarkerPlayer(IntEnum):
    P1 = 1
    P2 = 2


class MarkerUnitKind(Enum):
    ATTACKER = "attacker"
    DEFENDER = "defender"


@dataclass(frozen=True, slots=True)
class TrackedMarker:
    id: int
    player: MarkerPlayer | None
    label: str
    unit_kind: MarkerUnitKind | None = None
    slot_index: int = 0
    is_turn: bool = False
    is_hq: bool = False
    is_confirm: bool = False
    is_help: bool = False
    is_nuke: bool = False

    @property
    def is_token(self) -> bool:
        return self.unit_kind is not None


TRACKED_MARKERS: tuple[TrackedMarker, ...] = (
    TrackedMarker(id=4, player=None, label="CONFIRM", is_confirm=True),
    TrackedMarker(id=5, player=None, label="HELP", is_help=True),
    TrackedMarker(id=10, player=MarkerPlayer.P1, label="TURN", is_turn=True),
    TrackedMarker(id=11, player=MarkerPlayer.P1, label="HQ", is_hq=True),
    TrackedMarker(id=12, player=MarkerPlayer.P1, unit_kind=MarkerUnitKind.ATTACKER, slot_index=0, label="ATK A"),
    TrackedMarker(id=13, player=MarkerPlayer.P1, unit_kind=MarkerUnitKind.ATTACKER, slot_index=1, label="ATK B"),
    TrackedMarker(id=14, player=MarkerPlayer.P1, unit_kind=MarkerUnitKind.DEFENDER, slot_index=0, label="DEF"),
    TrackedMarker(id=19, player=MarkerPlayer.P1, label="NUKE", is_nuke=True),
    TrackedMarker(id=20, player=MarkerPlayer.P2, label="TURN", is_turn=True),
    TrackedMarker(id=21, player=MarkerPlayer.P2, label="HQ", is_hq=True),
    TrackedMarker(id=22, player=MarkerPlayer.P2, unit_kind=MarkerUnitKind.ATTACKER, slot_index=0, label="ATK A"),
    TrackedMarker(id=23, player=MarkerPlayer.P2, unit_kind=MarkerUnitKind.ATTACKER, slot_index=1, label="ATK B"),
    TrackedMarker(id=24, player=MarkerPlayer.P2, unit_kind=MarkerUnitKind.DEFENDER, slot_index=0, label="DEF"),
    TrackedMarker(id=29, player=MarkerPlayer.P2, label="NUKE", is_nuke=True),
)


MARKER_BY_ID: dict[int, TrackedMarker] = {marker.id: marker for marker in TRACKED_MARKERS}
TOKEN_MARKERS: tuple[TrackedMarker, ...] = tuple(marker for marker in TRACKED_MARKERS if marker.is_token)
TURN_MARKERS: tuple[TrackedMarker, ...] = tuple(marker for marker in TRACKED_MARKERS if marker.is_turn)
HQ_MARKERS: tuple[TrackedMarker, ...] = tuple(marker for marker in TRACKED_MARKERS if marker.is_hq)
CONFIRM_MARKERS: tuple[TrackedMarker, ...] = tuple(marker for marker in TRACKED_MARKERS if marker.is_confirm)
HELP_MARKERS: tuple[TrackedMarker, ...] = tuple(marker for marker in TRACKED_MARKERS if marker.is_help)
NUKE_MARKERS: tuple[TrackedMarker, ...] = tuple(marker for marker in TRACKED_MARKERS if marker.is_nuke)
TOKEN_IDS: set[int] = {marker.id for marker in TOKEN_MARKERS}
TURN_MARKER_IDS: set[int] = {marker.id for marker in TURN_MARKERS}
HQ_MARKER_IDS: set[int] = {marker.id for marker in HQ_MARKERS}
CONFIRM_MARKER_IDS: set[int] = {marker.id for marker in CONFIRM_MARKERS}
HELP_MARKER_IDS: set[int] = {marker.id for marker in HELP_MARKERS}
NUKE_MARKER_IDS: set[int] = {marker.id for marker in NUKE_MARKERS}


def marker_label(marker_id: int) -> str:
    marker = MARKER_BY_ID.get(marker_id)
    if marker is None:
        return f"ID:{marker_id}"
    if marker.is_confirm:
        return marker.label
    if marker.is_help:
        return marker.label
    if marker.is_nuke and marker.player is not None:
        return f"P{int(marker.player)} {marker.label}"
    if marker.is_turn and marker.player is not None:
        return f"P{int(marker.player)} {marker.label}"
    if marker.is_hq and marker.player is not None:
        return f"P{int(marker.player)} {marker.label}"
    return marker.label
