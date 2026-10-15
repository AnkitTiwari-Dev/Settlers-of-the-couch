from dataclasses import dataclass, field
from game import GameState, Player, IllegalMove, new_game
import secrets,string

MIN_PLAYERS = 1
MAX_PLAYERS = 4
COLORS = ["blue","pink","grey","orange"]
MAX_NAME_LENGTH = 20
@dataclass
class RoomPlayer:
    name: str
    color: str
    token: str
@dataclass
class Room:
    room_code: str
    host_token: str
    game: GameState | None = None
    players: list[RoomPlayer] = field(default_factory=list)
    @property
    def leader(self) -> RoomPlayer | None:
        return self.players[0] if self.players else None
 
    def has_started(self) -> bool:
        return self.game is not None

rooms:dict[str,Room] = {}


def make_code() -> str:
    main_list = list(string.digits)  + list(string.ascii_uppercase)
    confusing_chars = {"0", "O", "1", "I", "L"}
    cleaned_list = [char for char in main_list if char not in confusing_chars]
    while True:
        pin = ""
        for i in range(4):
            choose = secrets.choice(cleaned_list)
            pin += choose
        if pin not in rooms:
            return pin
    

def create_room() -> Room:
    code = make_code()
    token = secrets.token_hex(32)
    r = Room(room_code=code,host_token=token)
    rooms[code] = r
    return r



def join_room(code:str,name:str,color:str) -> str:
    r = find_room(code)
    if r.has_started():
        raise IllegalMove("Game already started")
    if len(r.players) >= MAX_PLAYERS:
        raise IllegalMove("Room is full")
    if not isinstance(name, str):
        raise IllegalMove("Name is not a string")
    name = name.strip()
    if not name:
        raise IllegalMove("Name cannot be empty.")
    if len(name) > MAX_NAME_LENGTH:
        raise IllegalMove(
            f"Name cannot exceed {MAX_NAME_LENGTH} characters."
        )
    if any(player.name.casefold() == name.casefold()
           for player in r.players):
        raise IllegalMove("That name is already taken.")

    if color not in COLORS:
        raise IllegalMove("Invalid color.")

    if any(player.color == color for player in r.players):
        raise IllegalMove("That color is already taken.")
    
    token = secrets.token_urlsafe(32)
    player = RoomPlayer(name,color,token)
    r.players.append(player)
    return token

def find_room(code:str) -> Room:
    if not isinstance(code,str):
        raise IllegalMove("Code must be a string")
    code = code.strip().upper()
    r = rooms.get(code)
    if r is None:
        raise IllegalMove("Room does not exist")
    return r
def tokens_match(given, stored: str) -> bool:
    """True only if `given` is a string equal to `stored`. Never raises, whatever `given` is."""
    if not isinstance(given, str):
        return False
    return secrets.compare_digest(given.encode("utf-8", errors="replace"),
                                  stored.encode("utf-8", errors="replace"))

def start_game(code:str,token:str):
    r = find_room(code)
    if r.leader is None:
        raise IllegalMove("No players in lobby")
    if r.has_started():
        raise IllegalMove("Game already started")
    if not tokens_match(token,r.leader.token):
        raise IllegalMove("Only leader can start the game")
    if MIN_PLAYERS > len(r.players):
        raise IllegalMove(f"You need at least {MIN_PLAYERS} players")
    players = [Player(p.name, p.color) for p in r.players]
    game = new_game(players)
    r.game = game
    return game

def public_view(r: Room) -> dict:
    return {
        "room_code": r.room_code,
        "started": r.has_started(),
        "leader": r.leader.name if r.leader else None,
        "players": [
            {
                "name": p.name,
                "color": p.color
            }
            for p in r.players
        ]
    }

def player_index(r: Room, token: str) -> int:
    for i, p in enumerate(r.players):
        if tokens_match(token, p.token):
            return i
    raise IllegalMove("Unknown player token")
