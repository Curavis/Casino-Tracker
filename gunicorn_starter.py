from app import app
import os
import json

# Define the path to your data file
DATA_FILE = "casino_data.json"

# Function to ensure the data file exists on startup
def initialize_data_file():
    """Checks for the data file and creates it with default values if it doesn't exist."""
    if not os.path.exists(DATA_FILE):
        default_data = {
            "net_profit": 0,
            "loss_streak": 0,
            "leaderboard_data": {},
            "profit_history": [0] # Initialize history list for the very first run
        }
        with open(DATA_FILE, 'w') as f:
            json.dump(default_data, f, indent=4)
        print(f"Created initial {DATA_FILE} with default values.")
    else:
        print(f"{DATA_FILE} found. Using existing live data.")

# Run the initialization check before starting the app
initialize_data_file()

if __name__ == "__main__":
    app.run()
