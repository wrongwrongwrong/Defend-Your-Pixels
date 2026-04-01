"""
Minimal playability demo (rules-only, no AR).

Run (after `pip install -e .` from repo root):
  python3 -m model_backend.run_model_demo
"""

from __future__ import annotations

from model_backend.game import Attacker, Defender, Direction, GameState, Pos


def main() -> None:
    g = GameState(seed=1)

    # Mid-field 2-1-2 drills (simple positions for now)
    for p in [Pos(4, 5), Pos(5, 5), Pos(6, 6), Pos(7, 6), Pos(8, 6)]:
        g.add_drill(p, yield_per_turn=5)

    # Two units each
    g.add_unit(Attacker("A1", owner=1, pos=Pos(1, 0)))
    g.add_unit(Defender("D1", owner=1, pos=Pos(0, 1)))
    g.add_unit(Attacker("A2", owner=2, pos=Pos(10, 11)))
    g.add_unit(Defender("D2", owner=2, pos=Pos(11, 10)))

    g.start_turn()

    # Tiny scripted sequence to show movement + capture + economy increment.
    print("Turn", g.turn, "active", g.active_player)
    g.move_unit("A1", Direction.RIGHT)
    g.move_unit("A1", Direction.RIGHT)
    print("A1 at", g.units["A1"].pos, "ether", g.players[g.active_player].ether)
    g.end_turn()

    print("Turn", g.turn, "active", g.active_player)
    g.move_unit("A2", Direction.LEFT)
    g.move_unit("A2", Direction.LEFT)
    print("A2 at", g.units["A2"].pos, "ether", g.players[g.active_player].ether)


if __name__ == "__main__":
    main()

