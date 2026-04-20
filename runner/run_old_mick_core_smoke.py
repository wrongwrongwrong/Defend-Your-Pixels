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


def test_auto_attack_after_move_hits_adjacent_hq_and_spends_ap() -> None:
    # Use a narrow board so the enemy HQ can be adjacent after one move.
    game = build_base_game(width=4, height=6)
    game.add_unit(Attacker("a0", PlayerId.P1, Pos(1, 3)))
    game.start_turn()

    ok = game.move_unit_to("a0", Pos(2, 3))
    assert ok, "move should succeed"
    assert game.towers[PlayerId.P2].hp == 18, "auto-attack should hit adjacent enemy HQ for 2 damage"
    assert game.units["a0"].ap == 0, "auto-attack should spend AP"
    assert "auto-attack" in game.last_action.lower(), "status text should mention auto-attack"


def test_auto_attack_after_move_strips_protected_resource_tile() -> None:
    game = build_base_game(width=6, height=6)
    game.add_unit(Attacker("a0", PlayerId.P1, Pos(1, 1)))
    # Enemy defender protects the enemy pixel at (3,1).
    game.add_unit(Defender("d0", PlayerId.P2, Pos(3, 2)))
    game.add_pixel(Pixel("p0", PlayerId.P2, Pos(3, 1)))
    game.start_turn()

    assert game.pixels["p0"].protection_layers == 1, "pixel should start protected"
    ok = game.move_unit_to("a0", Pos(2, 1))
    assert ok, "move should succeed"
    assert "p0" in game.pixels, "first auto-attack should not destroy protected pixel"
    assert game.pixels["p0"].protection_layers == 0, "first auto-attack should strip protection"
    assert game.units["a0"].ap == 0, "auto-attack should spend AP"


def test_auto_attack_after_move_can_hit_adjacent_enemy_unit() -> None:
    game = build_base_game(width=6, height=6)
    game.add_unit(Attacker("a0", PlayerId.P1, Pos(1, 1)))
    game.add_unit(Attacker("e0", PlayerId.P2, Pos(3, 1)))
    game.start_turn()

    ok = game.move_unit_to("a0", Pos(2, 1))
    assert ok, "move should succeed"
    assert "e0" in game.units, "enemy unit should survive at 1 HP"
    assert game.units["e0"].hp == 1, "auto-attack should hit enemy unit for 2 damage"
    assert game.units["a0"].ap == 0, "auto-attack should spend AP"

def test_auto_attack_at_turn_start_works_for_next_player() -> None:
    game = build_base_game(width=6, height=6)
    # Place P1 attacker adjacent to P2 attacker after P2's turn starts.
    game.add_unit(Attacker("p1", PlayerId.P1, Pos(2, 1)))
    game.add_unit(Attacker("p2", PlayerId.P2, Pos(3, 1)))
    game.start_turn()

    # End P1's turn; when P2 starts, it should auto-attack adjacent enemy.
    game.end_turn()
    assert game.active_player == PlayerId.P2, "P2 should be active"
    assert "auto-attack" in game.last_action.lower(), "turn start should include auto-attack"
    assert "p1" in game.units, "P1 unit should survive at 1 HP"
    assert game.units["p1"].hp == 1, "P2 auto-attack should deal 2 damage to adjacent enemy unit"

    # Regression: auto-attack spending AP must not prevent movement.
    ok = game.move_unit_to("p2", Pos(4, 1))
    assert ok, "P2 should still be able to move after auto-attack"


def main() -> None:
    tests = [
        ("first_hit_line_attack", test_first_hit_line_attack),
        ("hard_terrain_blocks_attack", test_hard_terrain_blocks_attack),
        ("defender_protection_requires_two_hits", test_defender_protection_requires_two_hits),
        ("hq_destruction_ends_game", test_hq_destruction_ends_game),
        ("auto_attack_after_move_hits_adjacent_hq_and_spends_ap", test_auto_attack_after_move_hits_adjacent_hq_and_spends_ap),
        ("auto_attack_after_move_strips_protected_resource_tile", test_auto_attack_after_move_strips_protected_resource_tile),
        ("auto_attack_after_move_can_hit_adjacent_enemy_unit", test_auto_attack_after_move_can_hit_adjacent_enemy_unit),
        ("auto_attack_at_turn_start_works_for_next_player", test_auto_attack_at_turn_start_works_for_next_player),
    ]

    for name, test_fn in tests:
        test_fn()
        print(f"PASS: {name}")

    print("All Old Mick core smoke tests passed.")


if __name__ == "__main__":
    main()
