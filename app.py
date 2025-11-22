# --- Python Flask Backend: app.py ---

from flask import Flask, render_template, request, redirect, url_for
import json
import os
import re # Import the regex module for better parsing

# --- Configuration & Global Data ---
app = Flask(__name__)

# FINAL DATA FIX: Use the persistent disk path
DATA_FILE = "/var/data/casino_data.json" 
# Path for the uploaded music file
MUSIC_ID_FILE = "Roblox Song ID's.txt" 

# --- Game Parameters (Spinning Wheel) ---
TOTAL_PAYOUT_MULTIPLIER = 9 # Payout is 9x the bet amount 
DEFAULT_BET_AMOUNT = 25000 

# --- Game Parameters (Odds or Evens) ---
ODD_EVEN_PAYOUT_MULTIPLIER = 1.8 # Payout is 1.8x the bet amount

# Global variables (Spinning Wheel)
net_profit = 0
loss_streak = 0
leaderboard_data = {}
profit_history = []
total_wins = 0 

# NEW Global variables (Odds or Evens)
oe_net_profit = 0
oe_profit_history = []
oe_total_wins = 0

# NEW Global variable for music list
roblox_music_list = []

SAVED_MESSAGES = {
    "Hot Wheel": "The wheel is hot! It's got to be ready any spin now!", 
    "Loss Streak Alert": "This is a placeholder.",
    "Chance": "Anyone care to take a chance on the wheel?" 
}


# --- Utility Functions ---
def calculate_wheel_net_cost(bet_amount):
    """Calculates the net cost to the casino for a SPINNING WHEEL win."""
    bet_amount = int(bet_amount)
    total_payout = bet_amount * TOTAL_PAYOUT_MULTIPLIER
    net_casino_cost = total_payout - bet_amount
    return net_casino_cost

def calculate_oe_net_cost(bet_amount):
    """Calculates the net cost to the casino for an ODD/EVEN win (1.8x payout)."""
    bet_amount = int(bet_amount)
    # The amount the player wins is (1.8 * bet) - bet
    player_profit = (ODD_EVEN_PAYOUT_MULTIPLIER - 1) * bet_amount
    return round(player_profit) # Round to prevent float errors

def format_currency(number):
    """Formats a number as a string with commas."""
    return "{:,.0f}".format(number)

def update_leaderboard(player_name, net_casino_cost):
    """Adds or updates player winnings (for Spinning Wheel only)."""
    global leaderboard_data
    
    # CRITICAL: Normalize the name to lowercase for storage
    player_name = player_name.lower()
    
    current_winnings = leaderboard_data.get(player_name, 0)
    current_winnings += net_casino_cost
    leaderboard_data[player_name] = current_winnings

def parse_roblox_music_file():
    """
    Parses the uploaded TXT file into a list of dictionaries.
    Handles lines that are:
    1. ID-Name (most common, uses regex for robust parsing)
    2. ID only
    3. Name only (ignores these, e.g., 'Back', 'Rave')
    """
    global roblox_music_list
    roblox_music_list = []
    
    if not os.path.exists(MUSIC_ID_FILE):
        print(f"Music ID file not found at: {MUSIC_ID_FILE}")
        return

    try:
        with open(MUSIC_ID_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # 1. Attempt to parse ID-Name (Robustly handle mixed separators/spaces)
                # Looks for a numerical string (\d+) followed by a hyphen or space (\s*[-\s]\s*), followed by a name (.+)
                # This should handle all variations like "123-Song" or "123 - Song" or "123 Song"
                match = re.match(r'(\d+)\s*[-\s]\s*(.+)', line)
                if match:
                    id_part = match.group(1).strip()
                    name_part = match.group(2).strip()
                    
                    if id_part and name_part:
                        roblox_music_list.append({
                            'id': id_part,
                            'name': name_part
                        })
                        continue

                # 2. Check for lines that are just a number (ID only)
                if line.isdigit():
                    roblox_music_list.append({
                        'id': line,
                        'name': 'Unknown Song'
                    })
                    continue
                
                # 3. Handle cases where the ID and name are separated by something else, or if the name contains non-word characters.
                # Example: "135329216833864-No Hook" (already handled by regex)
                # We need to make sure we don't accidentally ignore valid entries.
                
                # FINAL CHECK: If the line contains a number and a hyphen/space, but the primary regex failed, 
                # we assume it's malformed or just a name (e.g., 'Back', 'Rave'). The primary regex is robust enough.
                
    except Exception as e:
        print(f"An error occurred while reading the music file: {e}")


# --- Data Persistence Functions ---
def load_data():
    """Loads all game data from the JSON file."""
    global net_profit, loss_streak, leaderboard_data, profit_history, total_wins
    global oe_net_profit, oe_profit_history, oe_total_wins 
    
    data_loaded = False
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                
                # Spinning Wheel Data
                net_profit = data.get("net_profit", 0)
                loss_streak = data.get("loss_streak", 0)
                leaderboard_data = data.get("leaderboard_data", {})
                profit_history = data.get("profit_history", [0]) 
                total_wins = data.get("total_wins", -1) 

                # Odds/Evens Data
                oe_net_profit = data.get("oe_net_profit", 0)
                oe_profit_history = data.get("oe_profit_history", [0])
                oe_total_wins = data.get("oe_total_wins", -1)
                
                data_loaded = True
        except json.JSONDecodeError:
            print("Error reading data file. Starting fresh.")

    # --- Data Normalization: Leaderboard Cleanup (Merges names like "John" and "john") ---
    if data_loaded and leaderboard_data:
        normalized_leaderboard = {}
        for player, winnings in leaderboard_data.items():
            lower_name = player.lower()
            normalized_leaderboard[lower_name] = normalized_leaderboard.get(lower_name, 0) + winnings
        
        needs_save = len(leaderboard_data) != len(normalized_leaderboard) or any(name != name.lower() for name in leaderboard_data.keys())

        leaderboard_data.clear()
        leaderboard_data.update(normalized_leaderboard)

        if needs_save:
             print("Leaderboard names normalized (all lowercase for storage). Saving data.")
             save_data()


    # --- HISTORICAL DATA RECALCULATION FIX (Spinning Wheel) ---
    if data_loaded and total_wins == -1:
        calculated_wins = 0
        HISTORICAL_NET_CASINO_COST = calculate_wheel_net_cost(DEFAULT_BET_AMOUNT) 
        
        for i in range(1, len(profit_history)):
            current_profit = profit_history[i]
            previous_profit = profit_history[i-1]
            if previous_profit - current_profit == HISTORICAL_NET_CASINO_COST:
                calculated_wins += 1
        
        total_wins = calculated_wins
        print(f"Historical Spinning Wheel total_wins calculated: {total_wins}")
        save_data() 
        
    # --- HISTORICAL DATA INITIALIZATION FIX (Odds or Evens) ---
    if data_loaded and oe_total_wins == -1:
        # Initialize to 0 if the key was missing (it's a new game mode)
        oe_total_wins = 0
        save_data()


def save_data():
    """Saves the current profit data to the JSON file."""
    data = {
        # Spinning Wheel Data
        "net_profit": net_profit,
        "loss_streak": loss_streak,
        # Leaderboard keys are now guaranteed to be lowercase
        "leaderboard_data": leaderboard_data, 
        "profit_history": profit_history,
        "total_wins": total_wins,
        
        # Odds/Evens Data
        "oe_net_profit": oe_net_profit,
        "oe_profit_history": oe_profit_history,
        "oe_total_wins": oe_total_wins
    }
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)


# --- Flask Routes ---

@app.route('/')
def index():
    """Main page route - Loads data, formats numbers, and renders the HTML interface."""
    load_data() 
    parse_roblox_music_file() # Load music IDs on every request
    
    # CRITICAL FIX 1: Capture the active tab from the URL query string, default to 'wheel'
    active_tab = request.args.get('active_tab', 'wheel')
    
    # --- SPINNING WHEEL CALCULATIONS ---
    sw_total_spins = len(profit_history) - 1
    if sw_total_spins > 0:
        sw_total_losses = sw_total_spins - total_wins
        sw_win_percent = round((total_wins / sw_total_spins) * 100)
        sw_loss_percent = 100 - sw_win_percent
        sw_win_loss_display = f"{total_wins} Wins / {sw_total_losses} Losses"
    else:
        sw_win_percent, sw_loss_percent = 0, 0
        sw_win_loss_display = "Start Spinning!"

    # --- ODDS OR EVENS CALCULATIONS ---
    oe_total_spins = len(oe_profit_history) - 1
    if oe_total_spins > 0:
        oe_total_losses = oe_total_spins - oe_total_wins
        oe_win_percent = round((oe_total_wins / oe_total_spins) * 100)
        oe_loss_percent = 100 - oe_win_percent
        oe_win_loss_display = f"{oe_total_wins} Wins / {oe_total_losses} Losses"
    else:
        oe_win_percent, oe_loss_percent = 0, 0
        oe_win_loss_display = "Start Betting!"
        
    # Sort leaderboard for display
    sorted_leaderboard = sorted(leaderboard_data.items(), key=lambda item: item[1], reverse=True)
    # CRITICAL CHANGE: Use .title() to capitalize the name for display purposes
    formatted_leaderboard = [(name.title(), format_currency(winnings)) for name, winnings in sorted_leaderboard]
    
    # Data passed to the HTML template
    context = {
        # Spinning Wheel Context
        'net_profit_f': format_currency(net_profit),
        'leaderboard_f': formatted_leaderboard, # Now uses title case for display
        'loss_streak': loss_streak,
        'profit_history': profit_history,
        'sw_win_percent': sw_win_percent,
        'sw_loss_percent': sw_loss_percent,
        'sw_total_spins': sw_total_spins,
        'sw_win_loss_display': sw_win_loss_display,
        
        # Odds or Evens Context
        'oe_net_profit_f': format_currency(oe_net_profit),
        'oe_profit_history': oe_profit_history,
        'oe_win_percent': oe_win_percent,
        'oe_loss_percent': oe_loss_percent,
        'oe_total_spins': oe_total_spins,
        'oe_win_loss_display': oe_win_loss_display,
        
        # Music Context (NEW)
        'roblox_music_list': roblox_music_list,
        
        # General Context
        'messages': SAVED_MESSAGES,
        'bet_options': [i * 25000 for i in range(1, 11)], 
        'default_bet': DEFAULT_BET_AMOUNT,
        # CRITICAL FIX 2: Pass the active tab back to the template
        'active_tab': active_tab 
    }
    
    return render_template('index.html', **context)

# --- SPINNING WHEEL ROUTES (No change needed for redirects) ---
@app.route('/lose', methods=['POST'])
def player_loses_route():
    global net_profit, loss_streak, profit_history
    load_data()
    
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
    global net_profit, loss_streak, profit_history, total_wins
    load_data()
    
    winner_name = request.form.get('winner_name')
    
    try:
        bet_amount = int(request.form.get('bet_amount_hidden'))
    except (ValueError, TypeError):
        bet_amount = DEFAULT_BET_AMOUNT
        
    net_casino_cost = calculate_wheel_net_cost(bet_amount)
    
    net_profit -= net_casino_cost
    loss_streak = 0
    total_wins += 1 
    
    profit_history.append(net_profit)
    
    if winner_name and winner_name.strip():
        # update_leaderboard handles the lowercase conversion
        update_leaderboard(winner_name.strip(), net_casino_cost) 
    
    save_data()
    
    return redirect(url_for('index'))

# --- ODDS OR EVENS ROUTES (Redirects updated to include active_tab) ---
@app.route('/odd_even_loses', methods=['POST'])
def odd_even_loses_route():
    """Handles the Odd/Even Player LOSES button click."""
    global oe_net_profit, oe_profit_history
    load_data()
    
    try:
        bet_amount = int(request.form.get('bet_amount_hidden'))
    except (ValueError, TypeError):
        bet_amount = DEFAULT_BET_AMOUNT
    
    oe_net_profit += bet_amount # Casino gains the full bet
    oe_profit_history.append(oe_net_profit)
    save_data()
    
    # CRITICAL FIX 3: Redirect back to index with the 'odds' tab active
    return redirect(url_for('index', active_tab='odds'))

@app.route('/odd_even_wins', methods=['POST'])
def odd_even_wins_route():
    """Handles the Odd/Even Player WINS button click."""
    global oe_net_profit, oe_profit_history, oe_total_wins
    load_data()
    
    try:
        bet_amount = int(request.form.get('bet_amount_hidden'))
    except (ValueError, TypeError):
        bet_amount = DEFAULT_BET_AMOUNT
        
    net_casino_cost = calculate_oe_net_cost(bet_amount)
    
    oe_net_profit -= net_casino_cost # Casino pays out the net cost
    oe_total_wins += 1 
    
    oe_profit_history.append(oe_net_profit)
    save_data()
    
    # CRITICAL FIX 4: Redirect back to index with the 'odds' tab active
    return redirect(url_for('index', active_tab='odds'))


# --- CRITICAL FIX: Add gunicorn_starter.py to enable proper deployment ---
# This file tells gunicorn which application to run.
# The app will run under gunicorn in the Canvas environment if a file named gunicorn_starter.py exists.
@app.route('/health')
def health_check():
    return "OK", 200

# Add a check for running locally vs running under a web server
if __name__ == '__main__':
    load_data() # Load initial data on startup
    parse_roblox_music_file() # Load music IDs on startup
    # Note: Flask runs on a specific port in a local environment.
    app.run(host='0.0.0.0', port=5000, debug=True)
