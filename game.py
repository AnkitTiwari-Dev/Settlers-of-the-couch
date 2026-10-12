from dataclasses import dataclass, field
from board import Board, Hex, Vertex, Edge
import random

RESOURCES = ["ingot", "plank", "pelt", "corn", "metal"]

@dataclass
class Tile:
    resource: str | None
    number: int | None

@dataclass
class Building:
    owner: int
    kind: str

@dataclass
class Player:
    name: str
    colour: str
    resources: dict[str, int] = field(default_factory=lambda: {r: 0 for r in RESOURCES})
    settlements_left: int = 5
    cities_left: int = 4
    roads_left: int = 15

@dataclass
class GameState:
    board: Board
    players: list[Player]
    tiles: dict[Hex, Tile]
    buildings: dict[Vertex, Building] = field(default_factory=dict)
    roads: dict[Edge, int] = field(default_factory=dict)
    last_settle: Vertex|None = None
    robber: Hex = (0, 0)
    phase: str = "setup"  # "setup", "playing", "finished"
    turn_order: list[int] = field(default_factory=list)
    turn_index: int = 0

    def current_player(self) -> int:
        """TODO: index of the player whose turn it is, based on phase and turn_index."""
        if self.phase == "setup":
            return self.turn_order[self.turn_index]
        raise NotImplementedError
        
class IllegalMove(Exception):
    """Raised when a player attempts an invalid action"""
    def __init__(self, message:str, player_index: int | None = None):
        self.message = message
        self.player_index = player_index
        super().__init__(self.message)
    def __str__(self):
        player_str = f" by Player {self.player_index}" if self.player_index is not None else ""
        return f"IllegalMove{player_str}: {self.message}"


def make_tiles(board: Board) -> dict[Hex, Tile]:
    """Base game: 4 plank, 4 pelt, 4 corn, 3 metal, 3 ingot, 1 wasteland; 18 number tokens."""
    resources = ["plank", "pelt", "corn"] * 4
    resources.extend(["ingot", "metal"] * 3)
    resources.append("wasteland")
    tokens = [2, 12]
    tokens.extend([3, 4, 5, 6, 8, 9, 10, 11] * 2)
    random.shuffle(tokens)
    random.shuffle(resources)

    tiles = {}
    for h, resource in zip(board.hexes, resources):
        if resource == "wasteland":
            tiles[h] = Tile(resource=None, number=None)
        else:
            tiles[h] = Tile(resource=resource, number=tokens.pop())
    return tiles

def snake_order(num_players: int) -> list[int]:
    """TODO: setup turn order, e.g. 4 players -> [0, 1, 2, 3, 3, 2, 1, 0]."""
    retlst = list(range(num_players))
    retlst.extend(retlst[::-1])
    return retlst
        

def new_game(players: list[Player]) -> GameState:
    """TODO: build the board, tiles, turn order, and put the robber on the desert."""
    board = Board()
    tiles = make_tiles(board)
    robber = next(h for h, t in tiles.items() if t.resource is None)
    return GameState(
        board=board,
        players=players,
        tiles=tiles,
        robber=robber,
        turn_order=snake_order(len(players)),
    )

def build_settlement(state:GameState, player_idx:int, vertex:Vertex):
    if(state.phase != "setup"):
        raise IllegalMove("Phase not setup",player_idx)
    if(state.current_player() != player_idx):
        raise IllegalMove("Invalid player index",player_idx)
    if(state.last_settle is not None):
        raise IllegalMove("Place your road first",player_idx)
    if(vertex not in state.board.vertices):
        raise IllegalMove("Vertex not on board",player_idx)
    if(vertex in state.buildings):
        raise IllegalMove("Vertex is already taken",player_idx)
    for nbor in state.board.adjacent_vertices(vertex):
        if nbor in state.buildings:
            raise IllegalMove("Right next to another settlement",player_idx)
    build = Building(player_idx,"settlement")
    state.buildings[vertex] = build
    state.players[player_idx].settlements_left -= 1
    state.last_settle = vertex

def build_road(state:GameState, player_idx:int, edge:Edge):
    if(state.phase != "setup"):
        raise IllegalMove("Phase not setup",player_idx)
    if(state.current_player() != player_idx):
        raise IllegalMove("Invalid player index",player_idx)
    if(state.last_settle is None):
        raise IllegalMove("Last settlement not None",player_idx)
    if(edge not in state.board.edges):
        raise IllegalMove("Edge not on board",player_idx)
    if(edge in state.roads):
        raise IllegalMove("Edge already taken",player_idx)
    player = state.players[player_idx]
    if player.roads_left <= 0:
        raise IllegalMove("No roads left",player_idx)
    ends = state.board.common_vertices(edge)
    if state.last_settle not in ends:
        raise IllegalMove("Road must connect to settlement",player_idx)
    state.roads[edge] = player_idx
    player.roads_left -= 1
    state.last_settle = None
    state.turn_index += 1
    if state.turn_index >= len(state.turn_order):
        state.phase = "playing"
    