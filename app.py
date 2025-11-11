from flask import Flask, render_template, request, redirect, url_for
import json
import os

# --- Configuration & Global Data ---
app = Flask(__name__)

# FINAL DATA FIX: Use the persistent disk path on Render
DATA_FILE = "/var/data/casino_data.json" 

# --- Fixed Game Parameters ---
TOTAL_PAYOUT_MULTIPLIER = 9 # Payout is 9x the bet amount (225000 / 25000 = 9)
DEFAULT_BET_AMOUNT = 25000 # Used for initialization if needed

# Global variables will be updated by load_data()
net_profit = 0
loss_streak = 0
leaderboard_data = {}
profit_history = []
total_wins = 0 

SAVED_MESSAGES = {
    "Hot Wheel": "The wheel is hot! It's got to be ready any spin now!", 
    "Loss Streak Alert": "This is a placeholder.",
    "Chance": "Anyone care to take a chance on the wheel?" 
}


# --- Utility Functions ---
def calculate_net_cost(bet_amount):
    """Calculates the net cost to the casino for a win, based on the bet."""
    bet_amount = int(bet_amount)
    total_payout = bet_amount * TOTAL_PAYOUT_MULTIPLIER
    net_casino_cost = total_payout - bet_amount
    return net_casino_cost

def format_currency(number):
    """Formats a number as a string with commas."""
    return "{:,.0f}".format(number)

# --- Data Persistence Functions ---
def load_data():
    """Loads profit data from the JSON file if it exists and initializes total_wins."""
    global net_profit, loss_streak, leaderboard_data, profit_history, total_wins
    
    data_loaded = False
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                net_profit = data.get("net_profit", 0)
                loss_streak = data.get("loss_streak", 0)
                leaderboard_data = data.get("leaderboard_data", {})
                profit_history = data.get("profit_history", [0]) 
                total_wins = data.get("total_wins", -1) 

                data_loaded = True
        except json.JSONDecodeError:
            print("Error reading data file. Starting fresh.")

    # --- HISTORICAL DATA RECALCULATION FIX ---
    # Recalculation logic remains the same
    if data_loaded and total_wins == -1:
        calculated_wins = 0
        # NOTE: This historical calculation is based on the original BET_AMOUNT logic.
        # Since we don't have historical bet amounts, we must assume a fixed win cost (225000 - 25000).
        HISTORICAL_NET_CASINO_COST = 200000 
        
        for i in range(1, len(profit_history)):
            current_profit = profit_history[i]
            previous_profit = profit_history[i-1]
            
            # If the profit dropped by the fixed historical cost, it was a win.
            if previous_profit - current_profit == HISTORICAL_NET_CASINO_COST:
                calculated_wins += 1
        
        total_wins = calculated_wins
        print(f"Historical total_wins calculated: {total_wins}")
        save_data() 
    
def save_data():
    """Saves the current profit data to the JSON file."""
    data = {
        "net_profit": net_profit,
        "loss_streak": loss_streak,
        "leaderboard_data": leaderboard_data,
        "profit_history": profit_history,
        "total_wins": total_wins
    }
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def update_leaderboard(player_name, net_casino_cost):
    """Adds or updates player winnings."""
    global leaderboard_data
    
    current_winnings = leaderboard_data.get(player_name, 0)
    current_winnings += net_casino_cost
    leaderboard_data[player_name] = current_winnings

# --- Flask Routes ---

@app.route('/')
def index():
    """Main page route - Loads data, formats numbers, and renders the HTML interface."""
    load_data() 
    
    # Calculate Total Spins and Win/Loss Ratios
    total_spins = len(profit_history) - 1
    
    if total_spins > 0:
        total_losses = total_spins - total_wins
        win_percent = round((total_wins / total_spins) * 100)
        loss_percent = 100 - win_percent
        win_loss_display = f"{total_wins} Wins / {total_losses} Losses"
    else:
        win_percent = 0
        loss_percent = 0
        win_loss_display = "Start Spinning!"
    
    # Sort leaderboard for display
    sorted_leaderboard = sorted(leaderboard_data.items(), key=lambda item: item[1], reverse=True)
    formatted_leaderboard = [(name, format_currency(winnings)) for name, winnings in sorted_leaderboard]
    
    # Data passed to the HTML template
    context = {
        'net_profit_f': format_currency(net_profit),
        'leaderboard_f': formatted_leaderboard,
        'loss_streak': loss_streak,
        'messages': SAVED_MESSAGES,
        'profit_history': profit_history,
        'win_percent': win_percent,
        'loss_percent': loss_percent,
        'total_spins': total_spins,
        'win_loss_display': win_loss_display,
        
        # NEW: Betting options for the template
        'bet_options': [i * 25000 for i in range(1, 11)], # 25000 up to 250000
        'default_bet': DEFAULT_BET_AMOUNT # For initial display
    }
    
    return render_template('index.html', **context)


@app.route('/lose', methods=['POST'])
def player_loses_route():
    """Handles the Player LOSES button click."""
    global net_profit, loss_streak, profit_history
    
    load_data()
    
    # NEW: Get bet amount from the form
    try:
        bet_amount = int(request.form.get('bet_amount_hidden'))
    except (ValueError, TypeError):
        bet_amount = DEFAULT_BET_AMOUNT
    
    net_profit += bet_amount
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
    
    # NEW: Get bet amount and calculate net cost
    try:
        bet_amount = int(request.form.get('bet_amount_hidden'))
    except (ValueError, TypeError):
        bet_amount = DEFAULT_BET_AMOUNT
        
    net_casino_cost = calculate_net_cost(bet_amount)
    
    net_profit -= net_casino_cost
    loss_streak = 0
    total_wins += 1 
    
    profit_history.append(net_profit)
    
    if winner_name and winner_name.strip():
        # Pass the calculated cost to the leaderboard update function
        update_leaderboard(winner_name.strip(), net_casino_cost)
    
    save_data()
    
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
