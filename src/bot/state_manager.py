import json
import os
from datetime import datetime
from src.bot.logger import logger


class StateManager:
    """
    Manages saving and loading the bot's state, including both the
    in-flight trade position and the long-term capital balance.
    """

    def __init__(self, position_state_file="data/bot_state.json", capital_file="data/capital.json"):
        self.position_state_file = position_state_file
        self.capital_file = capital_file  # <-- NEW
        logger.info("State Manager initialized.")

    def save_position_state(self, open_position):
        """Saves the details of an open position to the state file."""
        try:
            open_position["state_saved_at"] = datetime.now().isoformat()
            with open(self.position_state_file, "w") as f:
                json.dump(open_position, f, indent=4)
            logger.info(f"STATE: Successfully saved position state to {self.position_state_file}")
            return True
        except Exception as e:
            logger.error(f"STATE ERROR: Failed to save position state. Reason: {e}")
            return False

    def load_position_state(self):
        """Loads a position state from the file if it exists."""
        if os.path.exists(self.position_state_file):
            try:
                with open(self.position_state_file, "r") as f:
                    state = json.load(f)
                logger.info(f"STATE: Successfully loaded position state from {self.position_state_file}")
                return state
            except Exception as e:
                logger.error(f"STATE ERROR: Failed to load position state file. Reason: {e}")
                return None
        return None

    def clear_position_state(self):
        """Deletes the position state file upon a successful trade exit."""
        if os.path.exists(self.position_state_file):
            try:
                os.remove(self.position_state_file)
                logger.info(f"STATE: Successfully cleared position state file.")
                return True
            except Exception as e:
                logger.error(f"STATE ERROR: Failed to clear position state file. Reason: {e}")
                return False
        return True

    def save_capital(self, current_capital):
        """Saves the current capital to the capital file."""
        try:
            state = {"last_known_capital": current_capital, "timestamp": datetime.now().isoformat()}
            with open(self.capital_file, "w") as f:
                json.dump(state, f, indent=4)
            # We don't log this every time to avoid spamming the logs.
            return True
        except Exception as e:
            logger.error(f"STATE ERROR: Failed to save capital. Reason: {e}")
            return False

    def load_capital(self, starting_capital):
        """
        Loads the last known capital from the file.
        If the file doesn't exist, it returns the starting_capital.
        """
        if os.path.exists(self.capital_file):
            try:
                with open(self.capital_file, "r") as f:
                    state = json.load(f)
                    capital = state.get("last_known_capital")
                    logger.info(f"STATE: Successfully loaded last known capital: ${capital:.2f}")
                    return capital
            except Exception as e:
                logger.error(f"STATE ERROR: Failed to load capital file. Reason: {e}")
                return starting_capital

        logger.info("STATE: No capital file found. Using starting capital.")
        return starting_capital
