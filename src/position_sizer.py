# src/position_sizer.py (Version 1.0)

import ccxt
from dotenv import load_dotenv
import os
import sys

# Add the parent directory to the path to allow importing the Strategy module for testing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.strategy import FundingArbStrategy

# --- Configuration ---
# A conservative minimum notional value for a trade.
# Binance requires ~$10 per leg, so we'll set the total to $25 to be safe.
MIN_NOTIONAL_TRADE_SIZE_USD = 25.0


def select_and_size_position(signals, current_capital_usd, exchange):
    """
    Selects the single best trade from a list of signals and calculates its size.

    Args:
        signals (list): A list of signal dictionaries from the Strategy module.
        current_capital_usd (float): The total current equity in USD.
        exchange (ccxt.Exchange): An initialized CCXT exchange object to fetch tickers.

    Returns:
        dict: A dictionary representing the final, sized trade order, or None.
    """
    if not signals:
        return None

    # --- 1. Prioritize Signals ---
    # Select the single best opportunity by sorting by the highest current APR.
    best_signal = sorted(signals, key=lambda x: x["current_apr"], reverse=True)[0]
    print(f"Position Sizer: Best signal found is {best_signal['symbol']} with APR {best_signal['current_apr']:.2f}%.")

    # --- 2. Apply Progressive Sizing Logic ---
    if current_capital_usd < 300:
        capital_to_deploy_pct = 0.6  # Use 60% of capital
    elif current_capital_usd < 1000:
        capital_to_deploy_pct = 0.7  # Use 70% of capital
    else:
        capital_to_deploy_pct = 0.8  # Use 80% of capital

    notional_trade_value = current_capital_usd * capital_to_deploy_pct
    print(
        f"Position Sizer: Capital is ${current_capital_usd:.2f}. Deploying {capital_to_deploy_pct*100}% -> ${notional_trade_value:.2f}."
    )

    # --- 3. Enforce Minimum Trade Size ---
    if notional_trade_value < MIN_NOTIONAL_TRADE_SIZE_USD:
        print(
            f"Position Sizer: Calculated trade value ${notional_trade_value:.2f} is below minimum of ${MIN_NOTIONAL_TRADE_SIZE_USD}. Skipping trade."
        )
        return None

    # --- 4. Calculate Final Asset Quantity ---
    try:
        ticker = exchange.fetch_ticker(best_signal["symbol"])
        asset_price = ticker["last"]
        if asset_price is None or asset_price <= 0:
            raise ValueError("Invalid asset price")

        asset_quantity = notional_trade_value / asset_price

    except Exception as e:
        print(f"Position Sizer: Could not fetch price for {best_signal['symbol']}. Reason: {e}")
        return None

    # --- 5. Return Actionable Trade Order ---
    final_trade = {
        "symbol": best_signal["symbol"],
        "notional_value_usd": notional_trade_value,
        "asset_quantity": asset_quantity,
        "asset_price": asset_price,
    }

    print(f"Position Sizer: Final trade calculated: {final_trade}")
    return final_trade


# --- Self-Testing Block ---
if __name__ == "__main__":
    # This block allows us to test the PositionSizer module independently.
    load_dotenv()

    # Use a dummy exchange object for testing without live API calls
    class MockExchange:
        def fetch_ticker(self, symbol):
            # Return dummy prices for testing purposes
            prices = {"DOGE/USDT": 0.15, "SOL/USDT": 150.0, "ETH/USDT": 3000.0}
            return {"last": prices.get(symbol)}

    mock_exchange = MockExchange()

    # --- Test Case 1: Single Signal, Sufficient Capital ---
    print("\n--- Test Case 1: Single DOGE signal, €100 capital ---")
    signals_1 = [{"symbol": "DOGE/USDT", "current_apr": 25.0, "action": "ENTER"}]
    sized_trade_1 = select_and_size_position(signals_1, 100, mock_exchange)  # Using 100 USD for simplicity
    assert sized_trade_1 is not None
    assert sized_trade_1["notional_value_usd"] == 60.0

    # --- Test Case 2: Multiple Signals, Sufficient Capital ---
    print("\n--- Test Case 2: Multiple signals, €500 capital ---")
    signals_2 = [
        {"symbol": "SOL/USDT", "current_apr": 18.0, "action": "ENTER"},
        {"symbol": "ETH/USDT", "current_apr": 22.0, "action": "ENTER"},  # ETH has higher APR
    ]
    sized_trade_2 = select_and_size_position(signals_2, 500, mock_exchange)
    assert sized_trade_2 is not None
    assert sized_trade_2["symbol"] == "ETH/USDT"  # Should select ETH
    assert sized_trade_2["notional_value_usd"] == 350.0  # 70% of 500

    # --- Test Case 3: Insufficient Capital ---
    print("\n--- Test Case 3: Single signal, €30 capital (too low) ---")
    signals_3 = [{"symbol": "DOGE/USDT", "current_apr": 25.0, "action": "ENTER"}]
    sized_trade_3 = select_and_size_position(signals_3, 30, mock_exchange)
    assert sized_trade_3 is None  # Should return None

    print("\n--- All PositionSizer tests passed! ---")
