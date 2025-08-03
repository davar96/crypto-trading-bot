# src/live_trader.py (Version 1.0 - Mock Test)

import time
import uuid
from dotenv import load_dotenv

# Import our core modules
from strategy import FundingArbStrategy
from position_sizer import select_and_size_position
from execution import ExecutionHandler

# --- Configuration ---
LOOP_INTERVAL_SECONDS = 10  # Check for opportunities every 10 seconds
STARTING_CAPITAL_USD = 100.0  # Our initial €100, treated as USD for simplicity


# --- Mock Exchange for Safe End-to-End Testing ---
# This class simulates the exchange's behavior without making real API calls.
class MockExchange:
    def __init__(self):
        print("MockExchange initialized for end-to-end testing.")

    def fetch_ticker(self, symbol):
        # Return a realistic dummy price for our test signal
        if symbol == "DOGE/USDT":
            return {"last": 0.15}
        return {"last": 0}

    def create_limit_sell_order(self, symbol, quantity):
        print(f"  MOCK: create_limit_sell_order({symbol}, {quantity})")
        return str(uuid.uuid4())

    def poll_for_fill(self, order_id, timeout_seconds):
        print(f"  MOCK: poll_for_fill({order_id}) -> Returning True")
        return True  # Assume the order always fills in the mock environment

    def cancel_order(self, order_id):
        print(f"  MOCK: cancel_order({order_id})")
        return True

    def create_market_buy_order(self, symbol, quantity):
        print(f"  MOCK: create_market_buy_order({symbol}, {quantity})")
        return str(uuid.uuid4())


def main():
    """
    The main event loop for the live trading bot.
    """
    print("--- Initializing Micro-Capital Funding Bot ---")

    # Initialize our components
    # We use the MockExchange for safe testing
    mock_exchange = MockExchange()

    # Note: In a real bot, the Strategy module would also use a real exchange object.
    # For this test, we don't need it as we will provide a mock signal.
    sizer = select_and_size_position
    executor = ExecutionHandler(mock_exchange)

    current_capital = STARTING_CAPITAL_USD

    # The main bot loop
    while True:
        print("\n----------------------------------")
        print(f"Loop start. Current State: {executor.get_state()}. Capital: ${current_capital:.2f}")

        # Only look for new trades if we are not already in a position or entering one.
        if executor.get_state() == "IDLE":

            # 1. RISK CHECK (Placeholder)
            # In a real bot, we would add the mentor's emergency shutdown logic here.

            # 2. CHECK FOR SIGNALS
            # In a real bot, we would call the Strategy module here.
            # For this test, we will inject a high-quality mock signal.
            print("Checking for signals...")
            mock_signals = [{"symbol": "DOGE/USDT", "current_apr": 25.0, "action": "ENTER"}]

            # 3. SIZE THE POSITION
            # Pass the signals and capital to the sizer.
            print("Sizing position...")
            sized_order = sizer(mock_signals, current_capital, mock_exchange)

            # 4. EXECUTE THE TRADE
            # If the sizer returns a valid trade, pass it to the executor.
            if sized_order:
                print("Executing trade...")
                executor.open_trade(sized_order)
            else:
                print("No viable trade signal found.")

        else:
            print("Execution handler is busy. Skipping signal check.")
            # NOTE: In a real bot, we would add logic here to manage the open position
            # (e.g., check for exit signals, monitor basis risk).

        # Wait for the next loop iteration
        print(f"Loop finished. Sleeping for {LOOP_INTERVAL_SECONDS} seconds...")
        time.sleep(LOOP_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
