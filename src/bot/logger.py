# src/bot/logger.py (Version 2.0 - Production Singleton)

import logging
import os
from datetime import datetime
import sys

# --- MODIFIED: A true singleton pattern ---

# Get the root logger
logger = logging.getLogger("ProjectChimera")

# Check if the logger has already been configured to prevent duplicate handlers
if not logger.handlers:
    logger.setLevel(logging.DEBUG)  # Set the lowest level on the logger itself

    # --- Use a consistent, daily log file ---
    log_filename = f'logs/bot_{datetime.now().strftime("%Y-%m-%d")}.log'

    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # --- Configure Handlers ---
    # File handler (detailed logs)
    file_handler = logging.FileHandler(log_filename, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)  # Log everything to the file
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(detailed_formatter)

    # Console handler (simple, INFO-level logs)
    console_handler = logging.StreamHandler(sys.stdout)  # Explicitly use stdout
    console_handler.setLevel(logging.INFO)  # Only show INFO and above in the console
    simple_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S")
    console_handler.setFormatter(simple_formatter)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("Logger configured successfully.")
