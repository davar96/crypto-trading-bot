import json
import os
from datetime import datetime
from .logger import logger


class StateManager:
    """Handles saving and loading bot state to disk"""

    def __init__(self, state_file="data/bot_state.json"):
        self.state_file = state_file
        # Ensure data directory exists
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        logger.info(f"StateManager: Initialized with state file: {state_file}")

    def save_state(self, risk_manager, performance_data=None):
        """Save current bot state to file"""
        try:
            state = {
                "timestamp": datetime.now().isoformat(),
                "positions": risk_manager.positions,
                "performance": performance_data or {},
                "version": "1.0",
            }

            # Write to temporary file first (atomic write)
            temp_file = f"{self.state_file}.tmp"
            with open(temp_file, "w") as f:
                json.dump(state, f, indent=2)

            # Rename to actual file (atomic on most systems)
            os.replace(temp_file, self.state_file)

            logger.debug(f"State saved successfully at {state['timestamp']}")

        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def load_state(self):
        """Load bot state from file"""
        try:
            if not os.path.exists(self.state_file):
                logger.info("No previous state file found. Starting fresh.")
                return None

            with open(self.state_file, "r") as f:
                state = json.load(f)

            logger.info(f"Loaded state from {state['timestamp']}")
            return state

        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return None

    def backup_state(self):
        """Create a backup of current state file"""
        try:
            if os.path.exists(self.state_file):
                backup_file = f"{self.state_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.copy(self.state_file, backup_file)
                logger.info(f"State backed up to {backup_file}")

        except Exception as e:
            logger.error(f"Failed to backup state: {e}")
