"""Game state and rules. No web code in here: this should be playable from a terminal."""
from dataclasses import dataclass, field
from board import Board, Hex, Vertex, Edge
import random

RESOURCES = ["ingot", "plank", "pelt", "corn", "metal"]

# Keys match Building.kind ("house", "mansion") so no translation is ever needed.
COSTS = {
    "house": {"ingot": 1, "plank": 1, "pelt": 1, "corn": 1},
    "road": {"plank": 1, "ingot": 1},
    "mansion": {"metal": 3, "corn": 2},
}


@dataclass
class Tile:
    resource: str | None  # None for the wasteland
    number: int | None  # dice token, None for the wasteland


@dataclass
class Building:
    owner: int  # index into GameState.players
    kind: str  # "house" or "mansion"


@dataclass
class Player:
    name: str
    colour: str
    resources: dict[str, int] = field(default_factory=lambda: {r: 0 for r in RESOURCES})
    houses_left: int = 5
    cities_left: int = 4
    roads_left: int = 15


@dataclass
class GameState:
    board: Board
    players: list[Player]
    tiles: dict[Hex, Tile]
    buildings: dict[Vertex, Building] = field(default_factory=dict)
    roads: dict[Edge, int] = field(default_factory=dict)  # edge -> owner index
    last_settle: Vertex | None = None  # setup: house placed, road still owed
    robber: Hex = (0, 0)
    phase: str = "setup"  # "setup", "playing", "finished"
    turn_order: list[int] = field(default_factory=list)  # setup snake order
    turn_index: int = 0  # position in turn_order during setup
    current_turn: int = 0  # player index during the playing phase
    has_rolled: bool = False
    last_roll: int | None = None

    def current_player(self) -> int:
        """Index of the player whose turn it is."""
        if self.phase == "setup":
            return self.turn_order[self.turn_index]
        return self.current_turn


class IllegalMove(Exception):
    """Raised when a player attempts an invalid action"""

    def __init__(self, message: str, player_index: int | None = None):
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
    """Setup turn order, e.g. 4 players -> [0, 1, 2, 3, 3, 2, 1, 0]."""
    order = list(range(num_players))
    order.extend(order[::-1])
    return order


def new_game(players: list[Player]) -> GameState:
    """Build the board and tiles, set the setup turn order, robber on the wasteland."""
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


def build_house(state: GameState, player_idx: int, vertex: Vertex):
    """Setup phase: place a free house. The road must follow before the turn ends."""
    if state.phase != "setup":
        raise IllegalMove("Not in the setup phase", player_idx)
    if state.current_player() != player_idx:
        raise IllegalMove("Not your turn", player_idx)
    if state.last_settle is not None:
        raise IllegalMove("Place your road first", player_idx)
    if vertex not in state.board.vertices:
        raise IllegalMove("Vertex not on board", player_idx)
    if vertex in state.buildings:
        raise IllegalMove("Vertex is already taken", player_idx)
    for nbor in state.board.adjacent_vertices(vertex):
        if nbor in state.buildings:
            raise IllegalMove("Right next to another house", player_idx)
    state.buildings[vertex] = Building(player_idx, "house")
    state.players[player_idx].houses_left -= 1
    state.last_settle = vertex


def build_road(state: GameState, player_idx: int, edge: Edge):
    """Setup phase: place a free road touching the house just placed."""
    if state.phase != "setup":
        raise IllegalMove("Not in the setup phase", player_idx)
    if state.current_player() != player_idx:
        raise IllegalMove("Not your turn", player_idx)
    if state.last_settle is None:
        raise IllegalMove("Place a house first", player_idx)
    if edge not in state.board.edges:
        raise IllegalMove("Edge not on board", player_idx)
    if edge in state.roads:
        raise IllegalMove("Edge already taken", player_idx)
    player = state.players[player_idx]
    if player.roads_left <= 0:
        raise IllegalMove("No roads left", player_idx)
    if state.last_settle not in state.board.common_vertices(edge):
        raise IllegalMove("Road must connect to your new house", player_idx)
    state.roads[edge] = player_idx
    player.roads_left -= 1
    state.last_settle = None
    state.turn_index += 1
    if state.turn_index >= len(state.turn_order):
        state.phase = "playing"


def produce(state: GameState, roll: int):
    """Pay every building on a hex whose number matches the roll (not the robber's hex)."""
    for vertex, building in state.buildings.items():
        player = state.players[building.owner]
        amount = 2 if building.kind == "mansion" else 1
        for hex_ in vertex:
            tile = state.tiles.get(hex_)  # off-board hexes have no tile
            if tile is None or tile.number != roll or hex_ == state.robber:
                continue
            player.resources[tile.resource] += amount


def apply_roll(state: GameState, player_idx: int, roll: int) -> int:
    """Apply a given roll. Tests call this directly; the server only calls roll_dice."""
    if state.phase != "playing":
        raise IllegalMove("The game is not in the playing phase", player_idx)
    if state.current_player() != player_idx:
        raise IllegalMove("Not your turn", player_idx)
    if state.has_rolled:
        raise IllegalMove("You have already rolled this turn", player_idx)
    state.last_roll = roll
    state.has_rolled = True
    if roll != 7:  # a 7 starts the robber instead (not written yet)
        produce(state, roll)
    return roll


def roll_dice(state: GameState, player_idx: int) -> int:
    """Roll two dice for this player and apply the result."""
    return apply_roll(state, player_idx, random.randint(1, 6) + random.randint(1, 6))


def end_turn(state: GameState, player_idx: int):
    """Finish the current player's turn and pass to the next player."""
    if state.phase != "playing":
        raise IllegalMove("The game is not in the playing phase", player_idx)
    if state.current_player() != player_idx:
        raise IllegalMove("Not your turn", player_idx)
    if not state.has_rolled:
        raise IllegalMove("Please roll the dice before ending your turn", player_idx)
    state.has_rolled = False
    state.last_roll = None
    state.current_turn = (state.current_turn + 1) % len(state.players)