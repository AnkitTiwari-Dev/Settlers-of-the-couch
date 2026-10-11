from board import Board

from fastapi import FastAPI

app = FastAPI()

@app.get("/board")
def build_board(size:int = 2):
    b = Board(2)
    Hexes = {"hexes" : b.hexes}
    return Hexes