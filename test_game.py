import random
from collections import Counter

import pytest

from game import (
    IllegalMove,
    Player,
    build_road,
    build_house,
    new_game,
    snake_order,
)

OFF_BOARD_VERTEX = ((10, 10), (10, 11), (11, 10))
OFF_BOARD_EDGE = ((10, 10), (10, 11))


def make_game(n=4, seed=0):
    random.seed(seed)
    players = [Player(f"p{i}", f"colour{i}") for i in range(n)]
    return new_game(players)


def legal_vertex(state):
    """First vertex that is empty and has no settlement next to it."""
    for v in sorted(state.board.vertices):
        if v in state.buildings:
            continue
        if any(n in state.buildings for n in state.board.adjacent_vertices(v)):
            continue
        return v
    raise AssertionError("no legal vertex left")


def snapshot(state):
    return (
        dict(state.buildings),
        dict(state.roads),
        [(p.houses_left, p.roads_left) for p in state.players],
        state.last_settle,
        state.turn_index,
        state.phase,
    )


# ---- snake_order and new_game ----

def test_snake_order():
    assert snake_order(4) == [0, 1, 2, 3, 3, 2, 1, 0]
    assert snake_order(3) == [0, 1, 2, 2, 1, 0]
    assert snake_order(2) == [0, 1, 1, 0]


def test_new_game_tiles():
    state = make_game()
    assert len(state.tiles) == 19
    counts = Counter(t.resource for t in state.tiles.values())
    assert counts[None] == 1
    assert counts["plank"] == counts["pelt"] == counts["corn"] == 4
    assert counts["ingot"] == counts["metal"] == 3
    numbers = sorted(t.number for t in state.tiles.values() if t.resource is not None)
    assert numbers == sorted([2, 12] + [3, 4, 5, 6, 8, 9, 10, 11] * 2)
    assert 7 not in numbers


def test_new_game_start_state():
    state = make_game()
    assert state.tiles[state.robber].resource is None
    assert state.phase == "setup"
    assert state.turn_index == 0
    assert state.current_player() == 0
    assert state.last_settle is None
    assert len(state.turn_order) == 8


def test_same_seed_same_board():
    assert make_game(seed=5).tiles == make_game(seed=5).tiles


# ---- settlements ----

def test_legal_settlement():
    state = make_game()
    v = legal_vertex(state)
    build_house(state, 0, v)
    assert state.buildings[v].owner == 0
    assert state.buildings[v].kind == "house"
    assert state.players[0].houses_left == 4
    assert state.last_settle == v


def test_settlement_wrong_player():
    state = make_game()
    with pytest.raises(IllegalMove):
        build_house(state, 1, legal_vertex(state))


def test_settlement_off_board():
    state = make_game()
    with pytest.raises(IllegalMove):
        build_house(state, 0, OFF_BOARD_VERTEX)


def test_settlement_second_before_road():
    state = make_game()
    build_house(state, 0, legal_vertex(state))
    with pytest.raises(IllegalMove):
        build_house(state, 0, legal_vertex(state))


def test_settlement_taken_and_too_close():
    state = make_game()
    v = legal_vertex(state)
    build_house(state, 0, v)
    build_road(state, 0, state.board.adjacent_edges(v)[0])
    with pytest.raises(IllegalMove):
        build_house(state, 1, v)  # taken
    for n in state.board.adjacent_vertices(v):
        with pytest.raises(IllegalMove):
            build_house(state, 1, n)  # too close


# ---- roads ----

def test_legal_road():
    state = make_game()
    v = legal_vertex(state)
    build_house(state, 0, v)
    e = state.board.adjacent_edges(v)[0]
    build_road(state, 0, e)
    assert state.roads[e] == 0
    assert state.players[0].roads_left == 14
    assert state.last_settle is None
    assert state.turn_index == 1
    assert state.current_player() == 1


def test_road_before_settlement():
    state = make_game()
    with pytest.raises(IllegalMove):
        build_road(state, 0, sorted(state.board.edges)[0])


def test_road_wrong_player():
    state = make_game()
    v = legal_vertex(state)
    build_house(state, 0, v)
    with pytest.raises(IllegalMove):
        build_road(state, 1, state.board.adjacent_edges(v)[0])


def test_road_off_board():
    state = make_game()
    build_house(state, 0, legal_vertex(state))
    with pytest.raises(IllegalMove):
        build_road(state, 0, OFF_BOARD_EDGE)


def test_road_not_touching_settlement():
    state = make_game()
    v = legal_vertex(state)
    build_house(state, 0, v)
    far = next(e for e in sorted(state.board.edges) if v not in state.board.common_vertices(e))
    with pytest.raises(IllegalMove):
        build_road(state, 0, far)


def test_road_edge_taken():
    state = make_game()
    v = legal_vertex(state)
    build_house(state, 0, v)
    e = state.board.adjacent_edges(v)[0]
    build_road(state, 0, e)
    v2 = legal_vertex(state)
    build_house(state, 1, v2)
    with pytest.raises(IllegalMove):
        build_road(state, 1, e)


# ---- failures change nothing ----

def test_failed_moves_leave_state_unchanged():
    state = make_game()
    before = snapshot(state)
    for bad in (
        lambda: build_house(state, 1, legal_vertex(state)),
        lambda: build_house(state, 0, OFF_BOARD_VERTEX),
        lambda: build_road(state, 0, sorted(state.board.edges)[0]),
    ):
        with pytest.raises(IllegalMove):
            bad()
    assert snapshot(state) == before

    v = legal_vertex(state)
    build_house(state, 0, v)
    before = snapshot(state)
    far = next(e for e in sorted(state.board.edges) if v not in state.board.common_vertices(e))
    with pytest.raises(IllegalMove):
        build_road(state, 0, far)
    with pytest.raises(IllegalMove):
        build_house(state, 0, legal_vertex(state))
    assert snapshot(state) == before


# ---- whole setup phase ----

def test_full_four_player_setup():
    state = make_game()
    for turn in range(8):
        assert state.phase == "setup"
        player = state.current_player()
        assert player == state.turn_order[turn]
        v = legal_vertex(state)
        build_house(state, player, v)
        edge = next(e for e in state.board.adjacent_edges(v) if e not in state.roads)
        build_road(state, player, edge)
    assert state.phase == "playing"
    assert len(state.buildings) == 8
    assert len(state.roads) == 8
    for p in state.players:
        assert p.houses_left == 3
        assert p.roads_left == 13