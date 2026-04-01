from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .types import PlayerId, Pos


class UnitKind(Enum):
    ATTACKER = "attacker"
    DEFENDER = "defender"


@dataclass(slots=True)
class CommandTower:
    owner: PlayerId
    pos: Pos
    hp: int = 20
    max_hp: int = 20

    def regen(self, ether_spent: int) -> int:
        # Prototype: 1 ether -> +1 HP
        heal = min(ether_spent, self.max_hp - self.hp)
        self.hp += heal
        return heal


@dataclass(slots=True)
class EtherDrill:
    pos: Pos
    owner: Optional[PlayerId] = None
    yield_per_turn: int = 5  # high-yield default; tune later


@dataclass(slots=True)
class Obstacle:
    pos: Pos
    hp: int = 2  # “destroyed with 2/1 shoot” -> keep simple HP=2 for prototype
    owner: Optional[PlayerId] = None  # defender-generated obstacles can have owner


@dataclass(slots=True)
class Unit:
    id: str
    owner: PlayerId
    pos: Pos
    kind: UnitKind

    ap: int = 1
    move_points: float = 2.0
    heat: int = 0  # 0..100+, increments by 33 per use
    overload_streak: int = 0  # consecutive overload attempts
    paralyzed_turns: int = 0

    on_highway: bool = False  # if moved onto highway this turn

    def new_turn(self) -> None:
        self.ap = 1
        self.move_points = 2.0
        self.on_highway = False
        if self.paralyzed_turns > 0:
            self.paralyzed_turns -= 1

    def can_act(self) -> bool:
        return self.paralyzed_turns == 0

    def vent(self) -> None:
        # “reduce Heat by 100%”
        self.heat = 0
        self.overload_streak = 0

    def add_heat(self, amount: int) -> None:
        self.heat += amount


class Attacker(Unit):
    def __init__(self, id: str, owner: PlayerId, pos: Pos, *, range_base: int = 3):
        super().__init__(id=id, owner=owner, pos=pos, kind=UnitKind.ATTACKER)
        self.range_base = range_base


class Defender(Unit):
    def __init__(self, id: str, owner: PlayerId, pos: Pos, *, shield_range: int = 2):
        super().__init__(id=id, owner=owner, pos=pos, kind=UnitKind.DEFENDER)
        self.shield_range = shield_range

