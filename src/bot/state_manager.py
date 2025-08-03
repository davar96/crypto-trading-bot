# src/bot/state_manager.py

import json
import os
from datetime import datetime


class StateManager:
    """
    Manages saving and loading the bot's state to a JSON file.
    Ensures that the bot can recover its position after a restart.
    """

    def __init__(self, state_file="data/bot_state.json"):
        self.state_file = state_file
        print("State Manager initialized.")

    def save_state(self, open_position):
        """Saves the details of an open position to the state file."""
        try:
            # Add a timestamp for recovery purposes
            open_position["state_saved_at"] = datetime.now().isoformat()

            with open(self.state_file, "w") as f:
                json.dump(open_position, f, indent=4)
            print(f"STATE: Successfully saved position state to {self.state_file}")
            return True
        except Exception as e:
            print(f"STATE ERROR: Failed to save state. Reason: {e}")
            return False

    def load_state(self):
        """Loads a position state from the file if it exists."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    state = json.load(f)
                print(f"STATE: Successfully loaded position state from {self.state_file}")
                return state
            except Exception as e:
                print(f"STATE ERROR: Failed to load state file. Reason: {e}")
                return None
        return None

    def clear_state(self):
        """Deletes the state file upon a successful trade exit."""
        if os.path.exists(self.state_file):
            try:
                os.remove(self.state_file)
                print(f"STATE: Successfully cleared position state file.")
                return True
            except Exception as e:
                print(f"STATE ERROR: Failed to clear state file. Reason: {e}")
                return False
        return True
