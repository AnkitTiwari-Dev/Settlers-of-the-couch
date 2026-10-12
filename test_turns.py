import random

import pytest

from game import (
    COSTS, RESOURCES, Building, IllegalMove, Player, Tile,
    apply_roll, end_turn, new_game, roll_dice,
)

V = ((0, 0), (1, -1), (1, 0))


def playing_state(n=3):
    random.seed(0)
    state = new_game([Player(f"p{i}", f"c{i}") for i in range(n)])
    for h in state.tiles:
        state.tiles[h] = Tile("metal", 2)
    state.robber = (-2, 2)
    state.phase = "playing"
    return state


def test_costs_use_known_resources_and_building_kinds():
    for cost in COSTS.values():
        assert set(cost) <= set(RESOURCES)
    assert set(COSTS) == {"house", "road", "mansion"}


def test_current_player_in_playing_phase():
    state = playing_state()
    state.current_turn = 2
    assert state.current_player() == 2


def test_roll_sets_state_and_returns_number():
    state = playing_state()
    assert apply_roll(state, 0, 8) == 8
    assert state.last_roll == 8 and state.has_rolled


def test_random_roll_is_between_2_and_12():
    for seed in range(50):
        random.seed(seed)
        state = playing_state()
        assert 2 <= roll_dice(state, 0) <= 12


def test_roll_pays_out():
    state = playing_state()
    state.tiles[(0, 0)] = Tile("corn", 8)
    state.buildings[V] = Building(0, "house")
    apply_roll(state, 0, 8)
    assert state.players[0].resources["corn"] == 1


def test_seven_pays_nothing():
    state = playing_state()
    state.tiles[(0, 0)] = Tile("corn", 7)
    state.buildings[V] = Building(0, "house")
    apply_roll(state, 0, 7)
    assert sum(state.players[0].resources.values()) == 0


def test_roll_errors_and_no_change():
    state = playing_state()
    with pytest.raises(IllegalMove):
        apply_roll(state, 1, 8)  # not your turn
    assert not state.has_rolled and state.last_roll is None
    apply_roll(state, 0, 8)
    with pytest.raises(IllegalMove):
        apply_roll(state, 0, 9)  # already rolled
    assert state.last_roll == 8
    state.phase = "setup"
    state.has_rolled = False
    with pytest.raises(IllegalMove):
        apply_roll(state, 0, 8)


def test_end_turn_needs_roll_and_right_player():
    state = playing_state()
    with pytest.raises(IllegalMove):
        end_turn(state, 0)  # has not rolled
    apply_roll(state, 0, 8)
    with pytest.raises(IllegalMove):
        end_turn(state, 1)  # not your turn
    assert state.current_turn == 0


def test_end_turn_advances_and_wraps():
    state = playing_state(3)
    for expected_next in (1, 2, 0):
        player = state.current_turn
        apply_roll(state, player, 8)
        end_turn(state, player)
        assert state.current_turn == expected_next
        assert not state.has_rolled and state.last_roll is None