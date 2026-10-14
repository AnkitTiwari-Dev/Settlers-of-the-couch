import random

import pytest

from game import (
    Building, IllegalMove, Player, Tile, afford, build_road, check_can_act,
    new_game, pay,
)

V = ((0, 0), (1, -1), (1, 0))      # inland vertex
OFF_EDGE = ((10, 10), (10, 11))


def playing_state(n=2):
    random.seed(0)
    state = new_game([Player(f"p{i}", f"c{i}") for i in range(n)])
    for h in state.tiles:
        state.tiles[h] = Tile("metal", 2)
    state.phase = "playing"
    state.has_rolled = True
    return state


def give(player, **cards):
    for r, n in cards.items():
        player.resources[r] += n


def road_cost_hand(state, idx=0):
    give(state.players[idx], plank=1, ingot=1)


def snapshot(state):
    return (dict(state.roads),
            [(dict(p.resources), p.roads_left) for p in state.players])


# ---- helpers ----

def test_afford_exact_short_and_unknown():
    p = Player("a", "b")
    assert not afford(p, "road")
    give(p, plank=1, ingot=1)
    assert afford(p, "road")
    p.resources["plank"] = 0
    assert not afford(p, "road")
    with pytest.raises(ValueError):
        afford(p, "castle")


def test_pay_takes_exact_cost_only():
    p = Player("a", "b")
    give(p, plank=2, ingot=1, corn=3)
    pay(p, "road")
    assert p.resources == {"ingot": 0, "plank": 1, "pelt": 0, "corn": 3, "metal": 0}


def test_pay_when_broke_changes_nothing():
    p = Player("a", "b")
    give(p, plank=1)
    with pytest.raises(ValueError):
        pay(p, "road")
    assert p.resources["plank"] == 1


def test_check_can_act():
    state = playing_state()
    check_can_act(state, 0)  # fine
    with pytest.raises(IllegalMove):
        check_can_act(state, 1)  # not your turn
    state.has_rolled = False
    with pytest.raises(IllegalMove):
        check_can_act(state, 0)  # has not rolled
    state.has_rolled = True
    state.phase = "setup"
    with pytest.raises(IllegalMove):
        check_can_act(state, 0)


# ---- playing-phase roads ----

def test_road_next_to_own_house():
    state = playing_state()
    state.buildings[V] = Building(0, "house")
    road_cost_hand(state)
    e = state.board.adjacent_edges(V)[0]
    build_road(state, 0, e)
    assert state.roads[e] == 0
    assert state.players[0].roads_left == 14
    assert state.players[0].resources["plank"] == 0
    assert state.players[0].resources["ingot"] == 0


def test_road_extends_own_road():
    state = playing_state()
    e1 = state.board.adjacent_edges(V)[0]
    state.roads[e1] = 0
    far_end = next(v for v in state.board.common_vertices(e1) if v != V)
    e2 = next(e for e in state.board.adjacent_edges(far_end) if e != e1)
    road_cost_hand(state)
    build_road(state, 0, e2)
    assert state.roads[e2] == 0


def test_road_touching_nothing_of_yours_fails():
    state = playing_state()
    road_cost_hand(state)
    with pytest.raises(IllegalMove):
        build_road(state, 0, state.board.adjacent_edges(V)[0])


def test_cannot_connect_to_opponents_road_or_house():
    state = playing_state()
    state.buildings[V] = Building(1, "house")
    e1 = state.board.adjacent_edges(V)[0]
    state.roads[e1] = 1
    road_cost_hand(state)
    e2 = state.board.adjacent_edges(V)[1]
    with pytest.raises(IllegalMove):
        build_road(state, 0, e2)


def test_opponent_house_blocks_extension_through_it():
    state = playing_state()
    e1 = state.board.adjacent_edges(V)[0]
    state.roads[e1] = 0                       # my road
    v2 = next(v for v in state.board.common_vertices(e1) if v != V)
    state.buildings[v2] = Building(1, "house")  # opponent sits at its far end
    e2 = next(e for e in state.board.adjacent_edges(v2) if e != e1)
    road_cost_hand(state)
    with pytest.raises(IllegalMove):
        build_road(state, 0, e2)


def test_road_errors_leave_state_unchanged():
    state = playing_state()
    state.buildings[V] = Building(0, "house")
    e = state.board.adjacent_edges(V)[0]
    before = snapshot(state)
    with pytest.raises(IllegalMove):
        build_road(state, 0, e)              # cannot afford
    with pytest.raises(IllegalMove):
        build_road(state, 1, e)              # not your turn
    with pytest.raises(IllegalMove):
        build_road(state, 0, OFF_EDGE)       # off the board
    state.has_rolled = False
    road_cost_hand(state)
    before = snapshot(state)
    with pytest.raises(IllegalMove):
        build_road(state, 0, e)              # has not rolled
    assert snapshot(state) == before


def test_taken_edge_and_no_roads_left():
    state = playing_state()
    state.buildings[V] = Building(0, "house")
    e1, e2 = state.board.adjacent_edges(V)[:2]
    road_cost_hand(state)
    build_road(state, 0, e1)
    road_cost_hand(state)
    with pytest.raises(IllegalMove):
        build_road(state, 0, e1)             # taken
    state.players[0].roads_left = 0
    with pytest.raises(IllegalMove):
        build_road(state, 0, e2)             # none left


def test_setup_road_still_free_and_advances():
    random.seed(0)
    state = new_game([Player("a", "b"), Player("c", "d")])
    from game import build_house
    build_house(state, 0, V)
    e = state.board.adjacent_edges(V)[0]
    build_road(state, 0, e)
    assert state.players[0].resources["plank"] == 0
    assert state.turn_index == 1 and state.phase == "setup"