from board import Board
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

@app.get("/board")
def build_board(size:int = 2):
    b = Board(2)
    Hexes = {"hexes" : b.hexes}
    return Hexes

app.mount("/", StaticFiles(directory="web",html=True),name="web")
