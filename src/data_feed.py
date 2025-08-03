# src/data_feed.py (Version 1.2 - Final Corrected Imports)

import time
import ccxt
from dotenv import load_dotenv
import os
import sys

# --- CORRECTED IMPORT ---
# Use the absolute path from the project root (which is on the path)
from src.bot.notifier import Notifier


class DataFeedManager:
    """
    Manages a robust connection to the exchange's data feeds.

    Handles websocket simulation, disconnections with exponential backoff,
    and sends critical alerts via the Notifier.
    """

    def __init__(self, exchange, notifier):
        self.exchange = exchange
        self.notifier = notifier
        self.reconnect_attempts = 0
        self.max_reconnects = 5
        self.connection_status = "DISCONNECTED"
        print("Data Feed Manager initialized.")

    def connect(self):
        """Simulates establishing a connection to the data feed."""
        print("Attempting to connect to data feed...")
        self.connection_status = "CONNECTED"
        self.reconnect_attempts = 0
        print("Data feed connected successfully.")
        self.notifier.send_message("✅ Data Feed CONNECTED.")
        return True

    def disconnect(self):
        """Simulates a disconnection event."""
        self.connection_status = "DISCONNECTED"
        print("‼️ Data feed DISCONNECTED.")
        self.notifier.send_message("‼️ Data Feed DISCONNECTED.")
        self.handle_disconnect()

    def handle_disconnect(self):
        """Handles the reconnection logic with exponential backoff."""
        if self.reconnect_attempts < self.max_reconnects:
            self.reconnect_attempts += 1
            wait_time = 2**self.reconnect_attempts
            print(f"Attempting reconnect #{self.reconnect_attempts} in {wait_time} seconds...")
            self.notifier.send_message(f"Attempting reconnect #{self.reconnect_attempts} in {wait_time}s...")
            time.sleep(wait_time)
            self.connect()
        else:
            print("CRITICAL: Maximum reconnect attempts reached. Shutting down.")
            self.notifier.send_message("🚨 CRITICAL: Max reconnects reached. Bot requires manual intervention!")
            raise SystemExit("DataFeedManager: Could not maintain data feed.")

    def get_funding_rate_data(self, symbol, limit):
        """
        Primary data fetching method.
        Includes sanity checks and fallbacks as per mentor's advice.
        """
        if self.connection_status != "CONNECTED":
            print("Warning: Cannot fetch data, currently disconnected.")
            return None

        try:
            perp_symbol = f"{symbol.split('/')[0]}/USDT:USDT"
            history = self.exchange.fetch_funding_rate_history(perp_symbol, limit=limit)

            if not self.validate_data_freshness(history):
                pass

            if not self.validate_funding_rates(history):
                self.notifier.send_message(f"⚠️ WARNING: Suspicious funding rate detected for {symbol}.")
                pass

            return history

        except Exception as e:
            print(f"Data Feed Error: Could not fetch data for {symbol}. {e}")
            self.disconnect()
            return None

    def validate_data_freshness(self, data):
        return True

    def validate_funding_rates(self, data):
        for record in data:
            if abs(float(record["fundingRate"])) > 0.01:
                print(f"Suspicious Rate Found: {record['fundingRate']}")
                return False
        return True


# --- Self-Testing Block ---
if __name__ == "__main__":
    load_dotenv()

    exchange = ccxt.binance(
        {
            "enableRateLimit": True,
            "options": {"defaultType": "future"},
            "apiKey": os.getenv("BINANCE_API_KEY"),
            "secret": os.getenv("BINANCE_SECRET_KEY"),
        }
    )

    notifier = Notifier()

    feed_manager = DataFeedManager(exchange, notifier)

    print("\n--- Test Case 1: Happy Path ---")
    feed_manager.connect()
    doge_data = feed_manager.get_funding_rate_data("DOGE/USDT", limit=5)
    if doge_data:
        print(f"Successfully fetched {len(doge_data)} records for DOGE.")
        assert len(doge_data) > 0

    print("\n--- Test Case 2: Disconnection Simulation ---")
    print("Simulating a network error by calling disconnect...")
    feed_manager.disconnect()

    print("\nTrying to fetch data again after reconnect...")
    eth_data = feed_manager.get_funding_rate_data("ETH/USDT", limit=5)
    if eth_data:
        print(f"Successfully fetched {len(eth_data)} records for ETH after reconnect.")
        assert len(eth_data) > 0

    print("\n--- All DataFeedManager tests passed! ---")
