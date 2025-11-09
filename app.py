from flask import Flask, render_template, request, redirect, url_for
import json
import os

# --- Configuration & Global Data ---
app = Flask(__name__)
DATA_FILE = "casino_data.json"

# --- Game Parameters ---
BET_AMOUNT = 25000
TOTAL_PAYOUT = 225000
NET_CASINO_COST = TOTAL_PAYOUT - BET_AMOUNT

# Global variables will be updated by load_data()
net_profit = 0
loss_streak = 0
leaderboard_data = {} 
SAVED_MESSAGES = {
    "Hot Wheel": "The wheel is hot! It's got to be ready any spin now!", 
    "Loss Streak Alert": "This is a placeholder.",
    "Chance": "Anyone care to take a chance on the wheel?" 
}


# --- Data Persistence Functions ---
def load_data():
    """Loads profit data from the JSON file if it exists."""
    global net_profit, loss_streak, leaderboard_data
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                net_profit = data.get("net_profit", 0)
                loss_streak = data.get("loss_streak", 0)
                leaderboard_data = data.get("leaderboard_data", {})
        except json.JSONDecodeError:
            print("Error reading data file. Starting fresh.")

def save_data():
    """Saves the current profit data to the JSON file."""
    data = {
        "net_profit": net_profit,
        "loss_streak": loss_streak,
        "leaderboard_data": leaderboard_data
    }
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def update_leaderboard(player_name):
    """Adds or updates player winnings."""
    global leaderboard_data
    
    current_winnings = leaderboard_data.get(player_name, 0)
    current_winnings += NET_CASINO_COST
    leaderboard_data[player_name] = current_winnings

# --- NEW FORMATTING FUNCTION ---
def format_currency(number):
    """Formats a number as a string with commas."""
    return "{:,.0f}".format(number)

# --- Flask Routes ---

@app.route('/')
def index():
    """Main page route - Loads data, formats numbers, and renders the HTML interface."""
    load_data() 
    
    # Sort leaderboard for display
    sorted_leaderboard = sorted(leaderboard_data.items(), key=lambda item: item[1], reverse=True)[:5]
    
    # Format all necessary numbers in Python before sending them to HTML
    formatted_leaderboard = [(name, format_currency(winnings)) for name, winnings in sorted_leaderboard]
    
    # Data passed to the HTML template
    context = {
        # FORMATTED VARIABLES
        'net_profit_f': format_currency(net_profit), # NEW FORMATTED VARIABLE
        'bet_amount_f': format_currency(BET_AMOUNT),   # NEW FORMATTED VARIABLE
        'net_casino_cost_f': format_currency(NET_CASINO_COST), # NEW FORMATTED VARIABLE
        'leaderboard_f': formatted_leaderboard, # NEW FORMATTED LEADERBOARD
        
        # UNFORMATTED VARIABLES (Still needed)
        'loss_streak': loss_streak,
        'messages': SAVED_MESSAGES,
    }
    
    return render_template('index.html', **context)


@app.route('/lose', methods=['POST'])
def player_loses_route():
    """Handles the Player LOSES button click."""
    global net_profit, loss_streak
    
    load_data()
    
    net_profit += BET_AMOUNT
    loss_streak += 1 
    
    save_data()
    
    return redirect(url_for('index'))


@app.route('/win', methods=['POST'])
def player_wins_route():
    """Handles the Player WINS button click and winner input."""
    global net_profit, loss_streak
    
    load_data()
    
    winner_name = request.form.get('winner_name')
    
    net_profit -= NET_CASINO_COST
    loss_streak = 0
    
    if winner_name and winner_name.strip():
        update_leaderboard(winner_name.strip())
    
    save_data()
    
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)