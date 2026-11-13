"""What each screen is allowed to see. The TV gets the whole board but only card
COUNTS; each phone gets its own hand and nothing about anyone else's."""
from game import COSTS, RESOURCES, GameState, IllegalMove, afford, points_winner
from room import MIN_PLAYERS, Room


def public_board(state: GameState) -> dict:
    """The shared board. JSON has no tuples, so every hex, vertex and edge is a list."""
    return {
        "tiles": [
            {"hex": list(h), "resource": tile.resource, "number": tile.number}
            for h, tile in state.tiles.items()
        ],
        "buildings": [
            {"vertex": [list(h) for h in vertex], "owner": b.owner, "kind": b.kind}
            for vertex, b in state.buildings.items()
        ],
        "roads": [
            {"edge": [list(h) for h in edge], "owner": owner}
            for edge, owner in state.roads.items()
        ],
        "robber": list(state.robber),
    }


def _winner_name(state: GameState) -> str | None:
    return state.players[state.winner].name if state.winner is not None else None


def player_summary(state: GameState, player_idx: int, on_turn: bool) -> dict:
    """Public facts about one player: their hand is a count, never the cards."""
    player = state.players[player_idx]
    return {
        "name": player.name,
        "color": player.color,
        "victory_points": points_winner(state, player_idx),
        "card_count": sum(player.resources.values()),
        "on_turn": on_turn,
    }


def host_view(room: Room) -> dict:
    """Everything the shared screen shows. Same keys before and after the game starts."""
    leader = room.leader.name if room.leader else None
    if room.game is None:
        return {
            "room_code": room.room_code,
            "phase": "lobby",
            "leader": leader,
            "winner": None,
            "current_player": None,
            "last_roll": None,
            "players": [
                {"name": p.name, "color": p.color, "victory_points": 0,
                 "card_count": 0, "on_turn": False}
                for p in room.players
            ],
            "board": None,
            "timeline": [],
        }
    state = room.game
    current = state.current_player()
    return {
        "room_code": room.room_code,
        "phase": state.phase,
        "leader": leader,
        "winner": _winner_name(state),
        "current_player": state.players[current].name,
        "last_roll": state.last_roll,
        "players": [
            player_summary(state, i, on_turn=(i == current and state.phase != "finished"))
            for i in range(len(state.players))
        ],
        "board": public_board(state),
        "timeline": [],
    }


def _next_action(state: GameState, player_idx: int) -> str:
    """One word the phone can switch on to decide which controls to show."""
    if state.phase == "finished":
        return "won" if state.winner == player_idx else "lost"
    if state.current_player() != player_idx:
        return "wait"
    if state.phase == "setup":
        return "place_road" if state.last_settle is not None else "place_house"
    return "build_or_end_turn" if state.has_rolled else "roll"


def player_view(room: Room, player_idx: int) -> dict:
    """What one phone sees. Always the same keys, whatever phase the room is in."""
    if not isinstance(player_idx, int) or isinstance(player_idx, bool):
        raise IllegalMove("Invalid player index")
    if not 0 <= player_idx < len(room.players):
        raise IllegalMove("Unknown player")

    me = room.players[player_idx]
    is_leader = room.leader is me
    state = room.game
    view = {
        "name": me.name,
        "color": me.color,
        "is_leader": is_leader,
        "can_start": is_leader and state is None and len(room.players) >= MIN_PLAYERS,
        "phase": "lobby",
        "winner": None,
        "victory_points": 0,
        "hand": {r: 0 for r in RESOURCES},
        "last_roll": None,
        "is_my_turn": False,
        "next_action": "lobby",
        "can_roll": False,
        "can_end_turn": False,
        "can_afford": [],
    }
    if state is None:
        return view

    player = state.players[player_idx]
    my_turn = state.current_player() == player_idx and state.phase != "finished"
    playing = state.phase == "playing"
    view.update(
        phase=state.phase,
        winner=_winner_name(state),
        victory_points=points_winner(state, player_idx),
        hand=dict(player.resources),  # a copy, so callers can't change the game
        last_roll=state.last_roll,
        is_my_turn=my_turn,
        next_action=_next_action(state, player_idx),
        can_roll=playing and my_turn and not state.has_rolled,
        can_end_turn=playing and my_turn and state.has_rolled,
        can_afford=[kind for kind in COSTS if afford(player, kind)],
    )
    return view