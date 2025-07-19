import logging
import os
from datetime import datetime


def setup_logger():
    """Sets up the logging configuration for the bot"""

    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # Create logger
    logger = logging.getLogger("TradingBot")
    logger.setLevel(logging.DEBUG)

    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    simple_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )

    # File handler (detailed logs) - with UTF-8 encoding
    file_handler = logging.FileHandler(
        f'logs/bot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
        encoding="utf-8",  # This ensures the log file can handle emojis
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)

    # Console handler (simple logs) - with safe encoding for Windows
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)

    # Add a filter to remove emojis from console output on Windows
    if os.name == "nt":  # Windows

        class NoEmojiFilter(logging.Filter):
            def filter(self, record):
                # Remove common emojis from the message
                emoji_chars = [
                    "✅",
                    "❌",
                    "🔵",
                    "💰",
                    "📉",
                    "🟢",
                    "🔴",
                    "🤖",
                    "💹",
                    "📊",
                    "📈",
                    "🛡️",
                    "⚠️",
                    "💥",
                    "🧹",
                    "🔄",
                ]
                for emoji in emoji_chars:
                    record.msg = record.msg.replace(emoji, "")
                return True

        console_handler.addFilter(NoEmojiFilter())

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Create a single logger instance to be imported
logger = setup_logger()
