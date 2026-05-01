from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from logic import Grid, Agent

app = FastAPI()

game_grid = None
game_agent = None

class InitConfig(BaseModel):
    rows: int
    cols: int

def init_game(rows=4, cols=4):
    global game_grid, game_agent
    game_grid = Grid(rows, cols)
    game_agent = Agent(game_grid)

init_game()

@app.get("/")
def serve_ui():
    return FileResponse("index.html")

@app.post("/init")
def reset_grid(config: InitConfig):
    init_game(config.rows, config.cols)
    return game_agent.get_state()

@app.get("/state")
def get_state():
    return game_agent.get_state()

@app.post("/move/{direction}")
def move_agent(direction: str):
    game_agent.move(direction)
    return game_agent.get_state()

if __name__ == "__main__":
    import uvicorn
    print("Starting Optimized Server...")
    uvicorn.run(app, host="127.0.0.1", port=8000)