# src/execution.py (Version 1.0)

import time
import uuid  # To generate unique order IDs for tracking


class ExecutionHandler:
    """
    Manages the lifecycle of a two-legged arbitrage trade.

    This class is designed as a state machine to be robust and fault-tolerant.
    It handles the safety-first entry/exit sequence and logs every action.
    """

    def __init__(self, exchange):
        self.exchange = exchange
        self.state = "IDLE"  # Can be IDLE, ENTERING, IN_POSITION, EXITING, EMERGENCY_CLOSING
        self.current_position = {}
        print("Execution Handler initialized in IDLE state.")

    def get_state(self):
        return self.state

    def open_trade(self, sized_order):
        """
        Attempts to execute the full, two-legged entry for a trade.

        Args:
            sized_order (dict): A dictionary from the PositionSizer.
        """
        if self.state != "IDLE":
            print(f"Execution Error: Cannot open a new trade while in state '{self.state}'.")
            return False

        print("\n--- Initiating Trade Entry ---")
        self.state = "ENTERING"
        symbol = sized_order["symbol"]
        perp_symbol = f"{symbol.split('/')[0]}/USDT:USDT"
        quantity = sized_order["asset_quantity"]

        # --- Step 1: Place the Perpetual Leg (Limit Order) ---
        print(f"Step 1: Placing PERP LIMIT SELL order for {quantity:.6f} {perp_symbol}.")
        try:
            # For a short, we sell at the best bid price to increase fill probability
            perp_order_id = self.exchange.create_limit_sell_order(perp_symbol, quantity)
            print(f"   - Perp order placed successfully. Order ID: {perp_order_id}")
        except Exception as e:
            print(f"   - FAILED to place perp order: {e}")
            self.state = "IDLE"
            return False

        # --- Step 2: Poll for the Perpetual Leg Fill ---
        print(f"Step 2: Polling for fill on order {perp_order_id}...")
        order_filled = self.exchange.poll_for_fill(perp_order_id, timeout_seconds=10)

        if not order_filled:
            print("   - FAILED: Perp order did not fill within timeout.")
            print("   - Cancelling perp order...")
            # NOTE: In a real system, we'd add logic here to handle a partial fill.
            self.exchange.cancel_order(perp_order_id)
            print("   - Perp order cancelled.")
            self.state = "IDLE"
            return False

        print("   - SUCCESS: Perp order filled.")

        # --- Step 3: Place the Spot Leg (Market Order) ---
        print(f"Step 3: Placing SPOT MARKET BUY order for {quantity:.6f} {symbol}.")
        try:
            spot_order_id = self.exchange.create_market_buy_order(symbol, quantity)
            print(f"   - SUCCESS: Spot order placed. Order ID: {spot_order_id}")
        except Exception as e:
            print(f"   - FAILED to place spot order: {e}")
            # --- CRITICAL: Handle the failed leg ---
            # This is where the "panic_close_perp" logic would go.
            # For V1.0, we will just log the critical error.
            print("\n   >>> CRITICAL ERROR: PERP LEG FILLED, SPOT LEG FAILED. MANUAL INTERVENTION REQUIRED! <<<")
            self.state = "EMERGENCY_CLOSING"
            return False

        # --- Final Step: Success ---
        self.state = "IN_POSITION"
        self.current_position = sized_order
        print(f"--- Trade Entry SUCCESSFUL. State is now {self.state}. Position: {self.current_position} ---")
        return True


# --- Self-Testing Block ---
if __name__ == "__main__":

    # A Mock Exchange to simulate the API without network calls
    class MockExchange:
        def __init__(self, should_perp_fill, should_spot_fail):
            self.should_perp_fill = should_perp_fill
            self.should_spot_fail = should_spot_fail
            self.open_orders = {}
            print(
                f"MockExchange initialized: Perp will fill={'Yes' if should_perp_fill else 'No'}, Spot will fail={'Yes' if should_spot_fail else 'No'}"
            )

        def create_limit_sell_order(self, symbol, quantity):
            order_id = str(uuid.uuid4())
            self.open_orders[order_id] = {"status": "open"}
            return order_id

        def poll_for_fill(self, order_id, timeout_seconds):
            if self.should_perp_fill:
                self.open_orders[order_id]["status"] = "closed"
                return True
            return False

        def cancel_order(self, order_id):
            self.open_orders.pop(order_id, None)
            return True

        def create_market_buy_order(self, symbol, quantity):
            if self.should_spot_fail:
                raise Exception("Network error: Unable to reach exchange.")
            return str(uuid.uuid4())

    # Example sized order from the PositionSizer
    dummy_sized_order = {
        "symbol": "DOGE/USDT",
        "notional_value_usd": 60.0,
        "asset_quantity": 400.0,
        "asset_price": 0.15,
    }

    # --- Test Case 1: "Happy Path" - Everything works ---
    print("\n--- Test Case 1: Happy Path ---")
    mock_exchange_ok = MockExchange(should_perp_fill=True, should_spot_fail=False)
    handler_ok = ExecutionHandler(mock_exchange_ok)
    success_1 = handler_ok.open_trade(dummy_sized_order)
    assert success_1 is True
    assert handler_ok.get_state() == "IN_POSITION"

    # --- Test Case 2: Perp order fails to fill ---
    print("\n--- Test Case 2: Perp order does not fill ---")
    mock_exchange_perp_fail = MockExchange(should_perp_fill=False, should_spot_fail=False)
    handler_perp_fail = ExecutionHandler(mock_exchange_perp_fail)
    success_2 = handler_perp_fail.open_trade(dummy_sized_order)
    assert success_2 is False
    assert handler_perp_fail.get_state() == "IDLE"

    # --- Test Case 3: Spot leg fails after perp fills (DANGER) ---
    print("\n--- Test Case 3: Spot leg fails (CRITICAL) ---")
    mock_exchange_spot_fail = MockExchange(should_perp_fill=True, should_spot_fail=True)
    handler_spot_fail = ExecutionHandler(mock_exchange_spot_fail)
    success_3 = handler_spot_fail.open_trade(dummy_sized_order)
    assert success_3 is False
    assert handler_spot_fail.get_state() == "EMERGENCY_CLOSING"

    print("\n--- All ExecutionHandler tests passed! ---")
