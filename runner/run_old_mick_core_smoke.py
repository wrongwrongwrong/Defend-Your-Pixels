from __future__ import annotations

from model_backend.game import AttackDirection, Attacker, CommandTower, Defender, GameState, PlayerId, Pos, TerrainType
from model_backend.game.entities import Pixel


def build_base_game(width: int = 6, height: int = 6) -> GameState:
    game = GameState(board_width=width, board_height=height)
    game.towers[PlayerId.P1] = CommandTower(PlayerId.P1, Pos(0, height // 2))
    game.towers[PlayerId.P2] = CommandTower(PlayerId.P2, Pos(width - 1, height // 2))
    return game


def test_first_hit_line_attack() -> None:
    game = build_base_game()
    game.add_unit(Attacker("a0", PlayerId.P1, Pos(1, 2)))
    game.add_pixel(Pixel("near", PlayerId.P2, Pos(3, 2)))
    game.add_pixel(Pixel("far", PlayerId.P2, Pos(4, 2)))
    game.start_turn()

    ok = game.attack_in_direction("a0", AttackDirection.RIGHT)
    assert ok, "directional attack should succeed"
    assert "near" not in game.pixels, "nearest target should be destroyed"
    assert "far" in game.pixels, "farther target should remain untouched"


def test_hard_terrain_blocks_attack() -> None:
    game = build_base_game()
    game.add_unit(Attacker("a0", PlayerId.P1, Pos(1, 3)))
    game.board.get(Pos(2, 3)).terrain = TerrainType.BLOCKED
    game.start_turn()

    ok = game.attack_in_direction("a0", AttackDirection.RIGHT)
    assert not ok, "attack should fail when blocked by hard terrain"
    assert game.towers[PlayerId.P2].hp == game.towers[PlayerId.P2].max_hp, "HQ should take no damage"
    assert "blocked" in game.last_action.lower(), "status text should mention blocking"


def test_defender_protection_requires_two_hits() -> None:
    game = build_base_game()
    game.add_unit(Attacker("a0", PlayerId.P2, Pos(4, 3)))
    game.add_unit(Defender("d0", PlayerId.P1, Pos(2, 3)))
    game.add_pixel(Pixel("p0", PlayerId.P1, Pos(3, 3)))
    game.start_turn()
    game.active_player = PlayerId.P2

    ok1 = game.attack_in_direction("a0", AttackDirection.LEFT)
    assert ok1, "first attack should succeed"
    assert "p0" in game.pixels, "protected resource tile should survive first hit"
    assert game.pixels["p0"].protection_layers == 0, "first hit should remove protection only"

    game.units["a0"].ap = 1
    ok2 = game.attack_in_direction("a0", AttackDirection.LEFT)
    assert ok2, "second attack should succeed"
    assert "p0" not in game.pixels, "second hit should destroy the resource tile"


def test_hq_destruction_ends_game() -> None:
    game = build_base_game()
    game.add_unit(Attacker("a0", PlayerId.P1, Pos(1, 3)))
    game.towers[PlayerId.P2].hp = 2
    game.start_turn()

    ok = game.attack_in_direction("a0", AttackDirection.RIGHT)
    assert ok, "attack should succeed"
    assert game.game_over, "game should end immediately when enemy HQ is destroyed"
    assert game.winner == PlayerId.P1, "attacking player should be the winner"
    assert "wins by destroying the enemy hq" in game.last_action.lower(), "status text should mention HQ win"


def main() -> None:
    tests = [
        ("first_hit_line_attack", test_first_hit_line_attack),
        ("hard_terrain_blocks_attack", test_hard_terrain_blocks_attack),
        ("defender_protection_requires_two_hits", test_defender_protection_requires_two_hits),
        ("hq_destruction_ends_game", test_hq_destruction_ends_game),
    ]

    for name, test_fn in tests:
        test_fn()
        print(f"PASS: {name}")

    print("All Old Mick core smoke tests passed.")


if __name__ == "__main__":
    main()
