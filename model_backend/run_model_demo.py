"""
Minimal playability demo (rules-only, no AR).

Run (after `pip install -e .` from repo root):
  python3 -m model_backend.run_model_demo
"""

from __future__ import annotations

from model_backend.game import Attacker, Defender, Direction, GameState, PlayerId, Pos


def main() -> None:
    g = GameState(seed=1)

    # Two units each
    g.add_unit(Attacker("A1", owner=PlayerId.P1, pos=Pos(1, 0)))
    g.add_unit(Defender("D1", owner=PlayerId.P1, pos=Pos(0, 1)))
    g.add_unit(Attacker("A2", owner=PlayerId.P2, pos=Pos(10, 11)))
    g.add_unit(Defender("D2", owner=PlayerId.P2, pos=Pos(11, 10)))

    g.spawn_default_pixels()
    g.start_turn()

    print("Turn", g.turn, "active", g.active_player)
    g.move_unit("A1", Direction.RIGHT)
    g.move_unit("A1", Direction.RIGHT)
    print("A1 at", g.units["A1"].pos)
    g.end_turn()

    print("Turn", g.turn, "active", g.active_player)
    g.move_unit("A2", Direction.LEFT)
    g.move_unit("A2", Direction.LEFT)
    print("A2 at", g.units["A2"].pos)


if __name__ == "__main__":
    main()

