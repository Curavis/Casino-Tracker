from flask import Flask, render_template, request, redirect, url_for
import json
import os

# --- Configuration & Global Data ---
app = Flask(__name__)

# FINAL DATA FIX: Use the persistent disk path on Render
# You MUST configure a disk named '/var/data' on Render for this to work.
DATA_FILE = "/var/data/casino_data.json" 

# --- Game Parameters ---
BET_AMOUNT = 25000
TOTAL_PAYOUT = 225000
NET_CASINO_COST = TOTAL_PAYOUT - BET_AMOUNT

# Global variables will be updated by load_data()
net_profit = 0
loss_streak = 0
leaderboard_data = {}
profit_history = []
total_wins = 0 # NEW: Variable to track total wins

SAVED_MESSAGES = {
    "Hot Wheel": "The wheel is hot! It's got to be ready any spin now!", 
    "Loss Streak Alert": "This is a placeholder.",
    "Chance": "Anyone care to take a chance on the wheel?" 
}


# --- Data Persistence Functions ---
def load_data():
    """Loads profit data from the JSON file if it exists."""
    global net_profit, loss_streak, leaderboard_data, profit_history, total_wins
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                net_profit = data.get("net_profit", 0)
                loss_streak = data.get("loss_streak", 0)
                leaderboard_data = data.get("leaderboard_data", {})
                profit_history = data.get("profit_history", [0]) 
                total_wins = data.get("total_wins", 0) # NEW: Load total wins
        except json.JSONDecodeError:
            print("Error reading data file. Starting fresh.")

def save_data():
    """Saves the current profit data to the JSON file."""
    data = {
        "net_profit": net_profit,
        "loss_streak": loss_streak,
        "leaderboard_data": leaderboard_data,
        "profit_history": profit_history,
        "total_wins": total_wins # NEW: Save total wins
    }
    # Ensure the directory exists before saving (for the first run)
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def update_leaderboard(player_name):
    """Adds or updates player winnings."""
    global leaderboard_data
    
    current_winnings = leaderboard_data.get(player_name, 0)
    current_winnings += NET_CASINO_COST
    leaderboard_data[player_name] = current_winnings

def format_currency(number):
    """Formats a number as a string with commas."""
    return "{:,.0f}".format(number)

# --- Flask Routes ---

@app.route('/')
def index():
    """Main page route - Loads data, formats numbers, and renders the HTML interface."""
    load_data() 
    
    # Calculate Total Spins and Win/Loss Ratios
    total_spins = len(profit_history) - 1 # History includes the starting point (0), so subtract 1
    
    if total_spins > 0:
        total_losses = total_spins - total_wins
        win_percent = round((total_wins / total_spins) * 100)
        loss_percent = 100 - win_percent
        # Format the display string
        win_loss_display = f"{total_wins} Wins / {total_losses} Losses"
    else:
        win_percent = 0
        loss_percent = 0
        win_loss_display = "Start Spinning!"
    
    # Sort leaderboard for display
    sorted_leaderboard = sorted(leaderboard_data.items(), key=lambda item: item[1], reverse=True)
    
    # Format all necessary numbers in Python before sending them to HTML
    formatted_leaderboard = [(name, format_currency(winnings)) for name, winnings in sorted_leaderboard]
    
    # Data passed to the HTML template
    context = {
        'net_profit_f': format_currency(net_profit),
        'bet_amount_f': format_currency(BET_AMOUNT),
        'net_casino_cost_f': format_currency(NET_CASINO_COST),
        'leaderboard_f': formatted_leaderboard,
        
        'loss_streak': loss_streak,
        'messages': SAVED_MESSAGES,
        'profit_history': profit_history,
        
        # NEW: Win/Loss Ratio Data
        'win_percent': win_percent,
        'loss_percent': loss_percent,
        'total_spins': total_spins,
        'win_loss_display': win_loss_display
    }
    
    return render_template('index.html', **context)


@app.route('/lose', methods=['POST'])
def player_loses_route():
    """Handles the Player LOSES button click."""
    global net_profit, loss_streak, profit_history
    
    load_data()
    
    net_profit += BET_AMOUNT
    loss_streak += 1
    
    profit_history.append(net_profit)
    
    save_data()
    
    return redirect(url_for('index'))


@app.route('/win', methods=['POST'])
def player_wins_route():
    """Handles the Player WINS button click and winner input."""
    global net_profit, loss_streak, profit_history, total_wins
    
    load_data()
    
    winner_name = request.form.get('winner_name')
    
    net_profit -= NET_CASINO_COST
    loss_streak = 0
    total_wins += 1 # NEW: Increment total wins
    
    profit_history.append(net_profit)
    
    if winner_name and winner_name.strip():
        update_leaderboard(winner_name.strip())
    
    save_data()
    
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
