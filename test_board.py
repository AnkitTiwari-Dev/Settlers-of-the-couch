from board import Board
 
# TODO: write these before the functions.
# - there are exactly 19 hexes
# - (0, 0) has six neighbours, all on the board
# - a corner hex such as (2, 0): count by hand how many neighbours are on
#   the board, then assert that number
 
def test_19_hexes():
    b = Board()
    assert len(b.hexes) == 19

def test_center_hex_neighbors_follow_directions_order():
    b = Board()
    assert b.neighbors((0, 0)) == [(1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1)]

def test_hexes_on_board():
    b = Board()
    assert b.on_board((0,0))
    assert b.on_board((1,1))
    assert b.on_board((0,2))

def test_hex_vertex():
    b = Board()
    assert b.hex_vertices((0,0)) == [((0, 0), (1, -1), (1, 0)), ((0, 0), (0, 1), (1, 0)), ((-1, 1), (0, 0), (0, 1)), ((-1, 0), (-1, 1), (0, 0)), ((-1, 0), (0, -1), (0, 0)), ((0, -1), (0, 0), (1, -1))]

def test_edge_list():
    b = Board()
    assert b.hex_edges((0,0)) == [((0, 0), (1, -1)), ((0, 0), (1, 0)), ((0, 0), (0, 1)), ((-1, 1), (0, 0)), ((-1, 0), (0, 0)), ((0, -1), (0, 0))]

def test_board_edge_vertices():
    b = Board()
    edge_set = set()
    vrtx_set = set()
    for hex in b.hexes:
        edge_set.update(b.hex_edges(hex))
        vrtx_set.update(b.hex_vertices(hex))
    assert len(edge_set) == 72
    assert len(vrtx_set) == 54