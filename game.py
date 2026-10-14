"""Game state and rules. No web code in here: this should be playable from a terminal."""
from dataclasses import dataclass, field
from board import Board, Hex, Vertex, Edge
import random

WIN_POINTS = 10
BANK_RATE = 4
RESOURCES = ["ingot", "plank", "pelt", "corn", "metal"]
ACTIONS = {
    "roll": lambda s, p, a: roll_dice(s, p),
    "build_house": lambda s, p, a: build_house(s, p, _to_vertex(_need(a, "vertex", p), p)),
    "build_road": lambda s, p, a: build_road(s, p, _to_edge(_need(a, "edge", p), p)),
    "upgrade_house": lambda s, p, a: upgrade_house(s, p, _to_vertex(_need(a, "vertex", p), p)),
    "bank_trade": lambda s, p, a: bank_trade(
        s, p, _need_resource(a, "give", p), _need_resource(a, "get", p)
    ),
    "end_turn": lambda s, p, a: end_turn(s, p),
}

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
    winner: int | None = None

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
    """Setup: a free house, with a road owed afterwards. Playing: a paid house that
    touches one of your own roads."""
    # 1. phase gate (checks only)
    if state.phase == "setup":
        if state.current_player() != player_idx:
            raise IllegalMove("Not your turn", player_idx)
        if state.last_settle is not None:
            raise IllegalMove("Place your road first", player_idx)
    elif state.phase == "playing":
        check_can_act(state, player_idx)
    else:
        raise IllegalMove("The game is not in progress", player_idx)

    # 2. board checks, both phases
    player = state.players[player_idx]
    if vertex not in state.board.vertices:
        raise IllegalMove("Vertex not on board", player_idx)
    if vertex in state.buildings:
        raise IllegalMove("Vertex is already taken", player_idx)
    if player.houses_left <= 0:
        raise IllegalMove("You have no houses left", player_idx)
    for nbor in state.board.adjacent_vertices(vertex):
        if nbor in state.buildings:
            raise IllegalMove("Right next to another house", player_idx)

    # 3. playing-only checks
    if state.phase == "playing":
        if not any(state.roads.get(e) == player_idx for e in state.board.adjacent_edges(vertex)):
            raise IllegalMove("Your house must touch one of your roads", player_idx)
        if not afford(player, "house"):
            raise IllegalMove("Not enough resources for a house", player_idx)

    # 4. every check has passed: now change the state
    state.buildings[vertex] = Building(player_idx, "house")
    player.houses_left -= 1
    if state.phase == "setup":
        state.last_settle = vertex
    else:
        pay(player, "house")
    if state.phase == "setup":
        count = sum(1 for b in state.buildings.values() if b.owner == player_idx)
        if count == 2:
            pay_starting_resources(state, player_idx, vertex)
    check_winner(state, player_idx)


def check_can_act(state: GameState, player_idx: int):
    """Playing phase: it must be your turn and you must have rolled first."""
    if state.phase != "playing":
        raise IllegalMove("Not in the playing phase", player_idx)
    if state.current_player() != player_idx:
        raise IllegalMove("Not your turn", player_idx)
    if not state.has_rolled:
        raise IllegalMove("Please roll the dice before placing", player_idx)


def afford(player: Player, build_type: str) -> bool:
    if build_type not in COSTS:
        raise ValueError(f"Unknown building type: {build_type}")
    return all(player.resources[r] >= n for r, n in COSTS[build_type].items())


def pay(player: Player, build_type: str):
    if not afford(player, build_type):
        raise ValueError(f"Player can't afford: {build_type}")
    for resource, n in COSTS[build_type].items():
        player.resources[resource] -= n


def road_connects(state: GameState, player_idx: int, edge: Edge) -> bool:
    """A road must touch your own building, or extend your own road through a
    vertex that no opponent has built on."""
    for v in state.board.common_vertices(edge):
        building = state.buildings.get(v)
        if building is not None:
            if building.owner == player_idx:
                return True
            continue  # an opponent's building blocks the chain through here
        for other in state.board.adjacent_edges(v):
            if state.roads.get(other) == player_idx:
                return True
    return False


def build_road(state: GameState, player_idx: int, edge: Edge):
    """Setup: a free road touching the house just placed. Playing: a paid road
    connected to your own buildings or roads."""
    if state.phase == "setup":
        if state.current_player() != player_idx:
            raise IllegalMove("Not your turn", player_idx)
        if state.last_settle is None:
            raise IllegalMove("Place a house first", player_idx)
    elif state.phase == "playing":
        check_can_act(state, player_idx)
    else:
        raise IllegalMove("The game is not in progress", player_idx)

    player = state.players[player_idx]
    if edge not in state.board.edges:
        raise IllegalMove("Edge not on board", player_idx)
    if edge in state.roads:
        raise IllegalMove("Edge already taken", player_idx)
    if player.roads_left <= 0:
        raise IllegalMove("No roads left", player_idx)

    if state.phase == "setup":
        if state.last_settle not in state.board.common_vertices(edge):
            raise IllegalMove("Road must connect to your new house", player_idx)
    else:
        if not road_connects(state, player_idx, edge):
            raise IllegalMove("Road must connect to your houses or roads", player_idx)
        if not afford(player, "road"):
            raise IllegalMove("Not enough resources for a road", player_idx)

    # every check has passed: now change the state
    state.roads[edge] = player_idx
    player.roads_left -= 1
    if state.phase == "setup":
        state.last_settle = None
        state.turn_index += 1
        if state.turn_index >= len(state.turn_order):
            state.phase = "playing"
    else:
        pay(player, "road")


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


def upgrade_house(state, player_idx, vertex):
    check_can_act(state, player_idx)
    building = state.buildings.get(vertex)
    if building is None:
        raise IllegalMove("No house at this vertex", player_idx)
    if building.owner != player_idx:
        raise IllegalMove("You don't own this house", player_idx)
    if building.kind != "house":
        raise IllegalMove("Building not a house", player_idx)
    pl = state.players[player_idx]
    if pl.cities_left <= 0:
        raise IllegalMove("You have no mansions left", player_idx)
    if not afford(pl, "mansion"):
        raise IllegalMove("Can't afford mansion", player_idx)
    pay(pl, "mansion")
    state.buildings[vertex].kind = "mansion"
    pl.houses_left += 1
    pl.cities_left -= 1
    check_winner(state, player_idx)


def points_winner(state, player_idx):
    amount = 0
    for build in state.buildings.values():
        if build.owner == player_idx:
            if build.kind == "house":
                amount += 1
            elif build.kind == "mansion":
                amount += 2
    return amount


def check_winner(state, player_idx):
    if points_winner(state, player_idx) >= WIN_POINTS:
        state.winner = player_idx
        state.phase = "finished"


def bank_trade(state: GameState, player_idx: int, give: str, get: str):
    """Trade BANK_RATE of one resource for 1 of another."""
    check_can_act(state, player_idx)
    if give not in RESOURCES or get not in RESOURCES:
        raise IllegalMove("Not a resource", player_idx)
    if give == get:
        raise IllegalMove("Can't trade a resource for itself", player_idx)
    player = state.players[player_idx]
    if player.resources[give] < BANK_RATE:
        raise IllegalMove(f"You need {BANK_RATE} {give} to trade", player_idx)
    player.resources[give] -= BANK_RATE
    player.resources[get] += 1


def pay_starting_resources(state: GameState, player_idx: int, vertex: Vertex):
    """Second setup house: one card from each land hex touching it."""
    for h in vertex:
        tile = state.tiles.get(h)  # off-board hexes have no tile
        if tile is None or tile.resource is None:
            continue
        state.players[player_idx].resources[tile.resource] += 1

def _to_hex(value, player_idx) -> Hex:
    """JSON gives [q, r]; the engine uses (q, r)."""
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 2
        or not all(isinstance(n, int) and not isinstance(n, bool) for n in value)
    ):
        raise IllegalMove("Malformed position in request", player_idx)
    return (value[0], value[1])


def _to_vertex(value, player_idx) -> Vertex:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise IllegalMove("A vertex needs three hexes", player_idx)
    hexes = [_to_hex(h, player_idx) for h in value]
    if len(set(hexes)) != 3:
        raise IllegalMove("A vertex needs three different hexes", player_idx)
    return tuple(sorted(hexes))  # the engine's canonical (sorted) name


def _to_edge(value, player_idx) -> Edge:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise IllegalMove("An edge needs two hexes", player_idx)
    hexes = [_to_hex(h, player_idx) for h in value]
    if hexes[0] == hexes[1]:
        raise IllegalMove("An edge needs two different hexes", player_idx)
    return tuple(sorted(hexes))


def _need(action: dict, field_name: str, player_idx):
    if field_name not in action:
        raise IllegalMove(f"Missing '{field_name}' in request", player_idx)
    return action[field_name]


def _need_resource(action: dict, field_name: str, player_idx) -> str:
    value = _need(action, field_name, player_idx)
    if not isinstance(value, str):
        raise IllegalMove(f"'{field_name}' must be a resource name", player_idx)
    return value

def apply_action(state: GameState, player_idx: int, action):
    """Run one action from a client. player_idx comes from the server's record of
    which connection sent it, never from the message. Bad input raises IllegalMove."""
    if (
        not isinstance(player_idx, int)
        or isinstance(player_idx, bool)
        or not 0 <= player_idx < len(state.players)
    ):
        raise IllegalMove("Unknown player", None)
    if not isinstance(action, dict):
        raise IllegalMove("Malformed request", player_idx)
    handler = ACTIONS.get(action.get("type")) if isinstance(action.get("type"), str) else None
    if handler is None:
        raise IllegalMove("Unknown action", player_idx)
    return handler(state, player_idx, action)