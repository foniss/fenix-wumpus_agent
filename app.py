from flask import Flask, jsonify, request, render_template
from logic import Grid, Agent

app = Flask(__name__)

# This holds our active game in memory
current_agent = None

def init_game(rows=4, cols=4):
    """Helper function to create a fresh grid and agent."""
    global current_agent
    grid = Grid(rows=rows, cols=cols)
    current_agent = Agent(grid)

@app.route('/')
def home():
    # Serves Fenix's UI from the /templates folder
    return render_template('index.html')

@app.route('/state', methods=['GET'])
def get_state():
    """Returns the current game state. Starts a new game if one doesn't exist."""
    global current_agent
    if current_agent is None:
        init_game()
    return jsonify(current_agent.get_state())

@app.route('/init', methods=['POST'])
def reset():
    """Starts a brand new episode based on UI settings."""
    data = request.get_json()
    rows = data.get('rows', 4)
    cols = data.get('cols', 4)
    init_game(rows, cols)
    return jsonify(current_agent.get_state())

@app.route('/move/<direction>', methods=['POST'])
def move(direction):
    """Moves the agent and returns the updated state."""
    global current_agent
    if current_agent is None:
        init_game()
        
    current_agent.move(direction)
    return jsonify(current_agent.get_state())

# Vercel requires the app variable to exist, but if running locally:
if __name__ == '__main__':
    app.run(debug=True)