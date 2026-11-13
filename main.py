from board import Board
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi import Request
from fastapi.responses import JSONResponse
from game import IllegalMove,apply_action
import room
from pydantic import BaseModel
from fastapi import WebSocket,WebSocketDisconnect
import view
app = FastAPI()

@app.get("/board")
def build_board(size:int = 2):
    b = Board(2)
    Hexes = {"hexes" : b.hexes}
    return Hexes
class room_info(BaseModel):
    color:str
    name:str

@app.exception_handler(IllegalMove)
async def handle_room_error(request:Request,exc:IllegalMove):
    return JSONResponse(status_code=400,content={"detail":exc.message})

@app.post("/create")
def create_room():
    r = room.create_room()
    return {"code":r.room_code,"token":r.host_token}

@app.post("/join/{code}")
async def join_room(data: room_info, code: str):
    token = room.join_room(code, data.name, data.color)
    await manager.send_all(code)
    return {"token": token}

@app.get("/read/{code}")
def read_room(code:str):
    return room.public_view(room.find_room(code))



class RoomManager:
    def __init__(self):
        self.tv = {}
        self.phone = {}
    def join_play(self,name,player_idx,ws):
        self.phone.setdefault(name, {})
        self.phone[name].setdefault(player_idx, [])
        self.phone[name][player_idx].append(ws)
    def join_tv(self,name,ws):
        self.tv.setdefault(name,[]).append(ws)
    def leave_tv(self,code,ws):
        lst = self.tv.get(code,[])
        if ws in lst:
            lst.remove(ws)
    def leave_play(self,code,idx,ws):
        web = self.phone.get(code,{}).get(idx,[])
        if ws in web:
            web.remove(ws)
    async def send_all(self, code):
        r = room.find_room(code)
        c = r.room_code
        for idx, sockets in list(self.phone.get(c, {}).items()):
            payload = {"type": "view", "view": view.player_view(r, idx)}
            for ws in list(sockets):
                try:
                    await ws.send_json(payload)
                except Exception as exc:
                    print("phone send failed:", repr(exc))
                    self.leave_play(c, idx, ws)
        host_payload = {"type": "view", "view": view.host_view(r)}
        for ws in list(self.tv.get(c, [])):
            try:
                await ws.send_json(host_payload)
            except Exception as exc:
                print("tv send failed:", repr(exc))
                self.leave_tv(c, ws)
manager = RoomManager()

@app.websocket("/ws/{code}")
async def end(ws: WebSocket, code: str):
    await ws.accept()
    try:
        hello = await ws.receive_json()
        r = room.find_room(code)
        if not isinstance(hello, dict):
            raise IllegalMove("Not a dict")
        role = hello.get("role")
        token = hello.get("token")
        if role == "player":
            idx = room.player_index(r, token)
        elif role == "tv":
            if not room.tokens_match(token, r.host_token):
                raise IllegalMove("Tokens don't match")
        else:
            raise IllegalMove("Wrong role")
    except (IllegalMove, ValueError):
        await ws.close(code=1008)
        return
    except WebSocketDisconnect:
        return  # the client already left, so there is nothing to close

    c = r.room_code
    if role == "player":
        manager.join_play(c, idx, ws)
    else:
        manager.join_tv(c, ws)

    try:
        if role == "player":
            await ws.send_json({"type": "view", "view": view.player_view(r, idx)})
        else:
            await ws.send_json({"type": "view", "view": view.host_view(r)})

        while True:
            try:
                msg = await ws.receive_json()
            except ValueError:
                await ws.send_json({"type": "error", "message": "Malformed message"})
                continue

            if role != "player":
                continue  # the TV only watches; receiving is how a disconnect is noticed

            try:
                if not isinstance(msg, dict):
                    raise IllegalMove("Not a dict", idx)
                if msg.get("type") == "start":
                    room.start_game(c, token)  # the token proved at login, not one from msg
                elif r.game is None:
                    raise IllegalMove("Game has not started yet", idx)
                else:
                    apply_action(r.game, idx, msg)
            except IllegalMove as exc:
                await ws.send_json({"type": "error", "message": exc.message})
                continue

            await manager.send_all(c)
    except WebSocketDisconnect:
        pass
    finally:
        if role == "player":
            manager.leave_play(c, idx, ws)
        else:
            manager.leave_tv(c, ws)


app.mount("/", StaticFiles(directory="web", html=True), name="web")

