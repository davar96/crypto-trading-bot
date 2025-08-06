import time
import ccxt
from dotenv import load_dotenv
import os
import sys

from src.bot.notifier import Notifier


class DataFeedManager:
    """
    Manages a robust connection to the exchange's data feeds.

    Handles time synchronization, disconnections with exponential backoff,
    and sends critical alerts via the Notifier.
    """

    def __init__(self, exchange, notifier):
        self.exchange = exchange
        self.notifier = notifier
        self.reconnect_attempts = 0
        self.max_reconnects = 5
        self.connection_status = "DISCONNECTED"
        self.time_offset = 0  # Difference between local and server time in ms
        print("Data Feed Manager initialized.")

    def connect(self):
        """Establishes connection and performs initial time sync."""
        print("Attempting to connect to data feed...")

        # --- NEW: Perform time sync on every connection attempt ---
        if not self.verify_time_sync():
            print("Connection aborted due to time sync failure.")
            return False

        self.connection_status = "CONNECTED"
        self.reconnect_attempts = 0
        print("Data feed connected successfully.")
        self.notifier.send_message("✅ Data Feed CONNECTED.")
        return True

    # --- NEW METHOD ---
    def verify_time_sync(self):
        """
        Checks the local system time against the exchange's server time.
        """
        print("Verifying time synchronization...")
        try:
            server_time = self.exchange.fetch_time()
            local_time = int(time.time() * 1000)
            self.time_offset = server_time - local_time

            print(f"  - Server Time: {server_time}, Local Time: {local_time}")
            print(f"  - Time Drift: {self.time_offset} ms")

            if abs(self.time_offset) > 1000:  # More than 1 second drift
                error_message = f"🚨 CRITICAL: Time sync error! Drift is {self.time_offset}ms. Funding calculations may be inaccurate."
                print(error_message)
                self.notifier.send_message(error_message)
                return False

            print("  - Time sync is OK.")
            return True
        except Exception as e:
            print(f"Could not verify time sync. Reason: {e}")
            self.notifier.send_message(f"⚠️ WARNING: Could not verify time sync with exchange.")
            return False  # Fail safely

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
            self.connect()  # Reconnect will re-verify time sync
        else:
            print("CRITICAL: Maximum reconnect attempts reached. Shutting down.")
            self.notifier.send_message("🚨 CRITICAL: Max reconnects reached. Bot requires manual intervention!")
            raise SystemExit("DataFeedManager: Could not maintain data feed.")

    def get_funding_rate_data(self, symbol, limit):
        """
        Primary data fetching method.
        """
        if self.connection_status != "CONNECTED":
            print("Warning: Cannot fetch data, currently disconnected.")
            return None
        try:
            perp_symbol = f"{symbol.split('/')[0]}/USDT:USDT"
            history = self.exchange.fetch_funding_rate_history(perp_symbol, limit=limit)

            # Placeholder for future sanity checks
            if not self.validate_funding_rates(history):
                self.notifier.send_message(f"⚠️ WARNING: Suspicious funding rate detected for {symbol}.")
                pass
            return history
        except Exception as e:
            print(f"Data Feed Error: Could not fetch data for {symbol}. {e}")
            self.disconnect()
            return None

    def validate_funding_rates(self, data):
        # This is a simple sanity check, not a full validation yet.
        for record in data:
            if abs(float(record["fundingRate"])) > 0.01:  # >1% funding rate is very high
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

    print("\n--- Testing Time Sync and Connection ---")
    feed_manager.connect()

    if feed_manager.connection_status == "CONNECTED":
        print("\n--- DataFeedManager Time Sync test passed! ---")
    else:
        print("\n--- DataFeedManager Time Sync test FAILED. ---")
