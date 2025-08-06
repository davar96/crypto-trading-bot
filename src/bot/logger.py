import logging
import os
from datetime import datetime
import sys

logger = logging.getLogger("ProjectChimera")

# Check if the logger has already been configured to prevent duplicate handlers
if not logger.handlers:
    logger.setLevel(logging.DEBUG)

    # --- Use a consistent, daily log file ---
    log_filename = f'logs/bot_{datetime.now().strftime("%Y-%m-%d")}.log'

    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # --- Configure Handlers ---
    file_handler = logging.FileHandler(log_filename, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(detailed_formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    simple_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S")
    console_handler.setFormatter(simple_formatter)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("Logger configured successfully.")
