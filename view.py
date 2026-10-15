from room import Room
from game import COSTS, RESOURCES, afford, points_winner, IllegalMove, GameState

def public_board(state:GameState) -> dict:
    tiles = [
        {
            "hex": list(h),
            "resource": tile.resource,
            "number": tile.number,
        }
        for h, tile in state.tiles.items()
    ]
    buildings = [
        {
            "vertex": [list(h) for h in vertex],
            "owner": building.owner,
            "kind": building.kind,
        }
        for vertex, building in state.buildings.items()
    ]
    roads = [
        {
            "edge": [list(h) for h in edge],
            "owner": owner,
        }
        for edge, owner in state.roads.items()
    ]
    return {
        "tiles": tiles,
        "buildings": buildings,
        "roads": roads,
        "robber": list(state.robber),
    }

def player_summary(state: GameState,player_idx: int) -> dict:
    player = state.players[player_idx]
    return {
        "name" : player.name,
        "victory_points" : points_winner(state,player_idx),
        "colour" : player.colour,
        "card_count" : sum(player.resources.values())
    }

def host_view(room: Room) -> dict:
    if room.game is None:
        return {
            "room_code": room.room_code,
            "phase": "lobby",
            "winner": None,
            "current_player": None,
            "last_roll": None,
            "players": [
                {
                    "name": p.name,
                    "victory_points": 0,
                    "colour": p.color,
                    "card_count": 0,
                }
                for p in room.players
            ],
            "board": None,
            "timeline": [],
        }

    state = room.game

    winner = (
        state.players[state.winner].name
        if state.winner is not None
        else None
    )

    current_idx = state.current_player()
    current_name = state.players[current_idx].name

    return {
        "room_code": room.room_code,
        "phase": state.phase,
        "winner": winner,
        "current_player": current_name,
        "last_roll": state.last_roll,
        "players": [
            player_summary(state, i)
            for i in range(len(state.players))
        ],
        "board": public_board(state),
        "timeline": [],
    }

def player_view(room: Room, player_idx: int) -> dict:
    if not isinstance(player_idx, int) or isinstance(player_idx, bool):
        raise IllegalMove("Invalid player index")

    if not 0 <= player_idx < len(room.players):
        raise IllegalMove("Unknown player")

    room_player = room.players[player_idx]
    if room.game is None:
        return {
            "name": room_player.name,
            "colour": room_player.color,
            "points": 0,
            "victory_points" : 0,
            "hand" : {r: 0 for r in RESOURCES},
            "phase" : "lobby",
            "last_roll" : None,
            "my_turn" : False,
            "can_roll" : False,
            "can_end_turn" : False,
            "can_afford" : []
        }
    state = room.game
    player = state.players[player_idx]
    last_roll = state.last_roll
    my_turn = state.current_player() == player_idx
    is_playing = state.phase == "playing"

    # Copy the resources so callers cannot mutate the game state.
    hand = dict(player.resources)
    can_afford = []
    for kind in COSTS:
        if afford(player,kind):
            can_afford.append(kind)

    return {
        "name": player.name,
        "colour": player.colour,
        "points": points_winner(state, player_idx),
        "hand": hand,
        "phase": state.phase,
        "last_roll": last_roll,
        "is_my_turn": my_turn,
        "can_roll": (
            is_playing
            and my_turn
            and not state.has_rolled
        ),
        "can_end_turn": (
            is_playing
            and my_turn
            and state.has_rolled
        ),
        "can_afford": can_afford,
    }
