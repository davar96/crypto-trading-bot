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
        # The list of coins you want to trade
        symbols = [
            'BTC/USDT', 
            'ETH/USDT',
            'SOL/USDT',
            'BNB/USDT',
            'XRP/USDT',
            'ADA/USDT',
            'LINK/USDT',
            'AVAX/USDT'
        ]

        logger.info("Starting Trading Bot...")
        logger.info(f"Trading symbols: {', '.join(symbols)}")
        
        # Create and run the bot
        bot = TradingBot(api_key=api_key, secret_key=secret_key, symbols=symbols)
        bot.run()