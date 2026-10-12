import random

from game import Building, Player, Tile, new_game, produce

INLAND = ((0, 0), (1, -1), (1, 0))          # all three hexes are on the board
OPPOSITE = ((-1, 0), (-1, 1), (0, 0))       # also touches (0, 0), far from INLAND
FAR_HEX = (-2, 2)                           # somewhere harmless to park the robber


def make_state(n=2):
    """A game where every tile is a quiet metal 2, so tests set only what they need."""
    random.seed(0)
    state = new_game([Player(f"p{i}", f"c{i}") for i in range(n)])
    for h in state.tiles:
        state.tiles[h] = Tile("metal", 2)
    state.robber = FAR_HEX
    return state


def build(state, owner, vertex, kind="house"):
    state.buildings[vertex] = Building(owner, kind)


def total(player):
    return sum(player.resources.values())


def test_settlement_pays_one():
    state = make_state()
    state.tiles[(0, 0)] = Tile("corn", 8)
    build(state, 0, INLAND)
    produce(state, 8)
    assert state.players[0].resources["corn"] == 1
    assert total(state.players[0]) == 1


def test_city_pays_two():
    state = make_state()
    state.tiles[(0, 0)] = Tile("corn", 8)
    build(state, 0, INLAND, "mansion")
    produce(state, 8)
    assert state.players[0].resources["corn"] == 2


def test_two_players_on_same_hex_both_paid():
    state = make_state()
    state.tiles[(0, 0)] = Tile("corn", 8)
    build(state, 0, INLAND)
    build(state, 1, OPPOSITE)
    produce(state, 8)
    assert state.players[0].resources["corn"] == 1
    assert state.players[1].resources["corn"] == 1


def test_robber_hex_pays_nothing():
    state = make_state()
    state.tiles[(0, 0)] = Tile("corn", 8)
    state.robber = (0, 0)
    build(state, 0, INLAND)
    produce(state, 8)
    assert total(state.players[0]) == 0


def test_robber_blocks_only_its_own_hex():
    state = make_state()
    state.tiles[(0, 0)] = Tile("corn", 8)
    state.tiles[(1, 0)] = Tile("plank", 8)
    state.robber = (0, 0)
    build(state, 0, INLAND)
    produce(state, 8)
    assert state.players[0].resources["corn"] == 0
    assert state.players[0].resources["plank"] == 1


def test_roll_matching_nothing_pays_nothing():
    state = make_state()
    state.tiles[(0, 0)] = Tile("corn", 8)
    build(state, 0, INLAND)
    produce(state, 4)
    assert total(state.players[0]) == 0


def test_seven_pays_nothing_even_next_to_wasteland():
    state = make_state()
    state.tiles[(0, 0)] = Tile(None, None)
    build(state, 0, INLAND)
    produce(state, 7)
    assert total(state.players[0]) == 0


def test_building_on_two_matching_hexes_is_paid_twice():
    state = make_state()
    state.tiles[(0, 0)] = Tile("corn", 8)
    state.tiles[(1, 0)] = Tile("plank", 8)
    build(state, 0, INLAND)
    produce(state, 8)
    assert state.players[0].resources["corn"] == 1
    assert state.players[0].resources["plank"] == 1


def test_production_adds_to_existing_hand():
    state = make_state()
    state.tiles[(0, 0)] = Tile("corn", 8)
    state.players[0].resources["corn"] = 3
    build(state, 0, INLAND)
    produce(state, 8)
    assert state.players[0].resources["corn"] == 4


def test_coastal_vertex_with_off_board_hexes():
    state = make_state()
    coastal = next(
        v for v in sorted(state.board.vertices)
        if sum(h in state.tiles for h in v) == 1
    )
    land = next(h for h in coastal if h in state.tiles)
    state.tiles[land] = Tile("pelt", 9)
    state.robber = next(h for h in state.tiles if h != land)
    build(state, 0, coastal)
    produce(state, 9)
    assert state.players[0].resources["pelt"] == 1