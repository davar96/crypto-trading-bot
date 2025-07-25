# src/main.py

from bot.trading_bot import TradingBot
from bot.logger import logger
import os
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv("TESTNET_API_KEY")
    secret_key = os.getenv("TESTNET_SECRET_KEY")

    if not api_key or not secret_key:
        logger.error("Error: TESTNET_API_KEY or TESTNET_SECRET_KEY not found.")
        logger.error("Please check your .env file.")
    else:
        # --- EXPANDED, CURATED, AND TESTNET-COMPATIBLE SYMBOL LIST ---
        symbols = [
            # Majors (The Core)
            "BTC/USDT",
            "ETH/USDT",
            "SOL/USDT",
            "BNB/USDT",
            "BCH/USDT",
            "DOT/USDT",
            "ADA/USDT",
            "NEAR/USDT",
            "AVAX/USDT",
            "LINK/USDT",
            "XRP/USDT",
            "DOGE/USDT",
            "LTC/USDT",
            "ATOM/USDT",
            "FTM/USDT",
            "RUNE/USDT",
            "UNI/USDT",
            "AAVE/USDT",
        ]
        # --- END OF CHANGE ---

        logger.info("Starting Trading Bot...")
        # Updated log message for clarity
        logger.info(f"Scanning {len(symbols)} symbols.")

        bot = TradingBot(api_key=api_key, secret_key=secret_key, symbols=symbols)
        bot.run()
