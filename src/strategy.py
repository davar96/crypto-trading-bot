# src/strategy.py (Version 1.0)

import ccxt
import pandas as pd
from dotenv import load_dotenv
import os


class FundingArbStrategy:
    """
    The brain of the funding rate arbitrage bot.

    This class holds the optimal parameters for our profitable assets,
    determines which assets are eligible to trade based on capital,
    and generates entry signals based on live market data.
    """

    def __init__(self, exchange):
        self.exchange = exchange

        # The "Golden" parameters discovered during our optimization phase.
        self.optimal_params = {
            "BTC/USDT": {"entry_apr": 15.0, "exit_apr": 3.0, "filter_periods": 3},
            "ETH/USDT": {"entry_apr": 15.0, "exit_apr": 3.0, "filter_periods": 12},
            "SOL/USDT": {"entry_apr": 12.0, "exit_apr": 3.0, "filter_periods": 9},
            "DOGE/USDT": {"entry_apr": 12.0, "exit_apr": 4.0, "filter_periods": 3},
        }

        # Mentor's "Progressive Capital" strategy for unlocking assets.
        # Tiers are sorted by capital required, from lowest to highest.
        self.capital_tiers = {
            100: ["DOGE/USDT"],
            200: ["DOGE/USDT", "SOL/USDT"],
            500: ["DOGE/USDT", "SOL/USDT", "ETH/USDT"],
            1000: ["DOGE/USDT", "SOL/USDT", "ETH/USDT", "BTC/USDT"],
        }

    def get_eligible_assets(self, current_capital):
        """
        Determines which assets are eligible to trade based on the current capital.
        """
        eligible_assets = []
        # Find the highest capital tier we qualify for.
        for threshold, assets in sorted(self.capital_tiers.items()):
            if current_capital >= threshold:
                eligible_assets = assets
        return eligible_assets

    def check_signals(self, current_capital):
        """
        Checks for entry signals on all eligible assets.

        Returns:
            list: A list of signal dictionaries. Each dictionary represents a
                  valid entry opportunity. Returns an empty list if no signals.
        """
        eligible_assets = self.get_eligible_assets(current_capital)

        if not eligible_assets:
            print("Capital too low to trade any assets.")
            return []

        print(f"Capital: €{current_capital:.2f}. Eligible assets to scan: {eligible_assets}")

        signals = []

        for symbol in eligible_assets:
            params = self.optimal_params.get(symbol)
            if not params:
                continue

            try:
                # We need historical data to calculate the rolling average.
                # Fetch a bit more than needed for safety.
                limit = params["filter_periods"] + 5
                perp_symbol = f"{symbol.split('/')[0]}/USDT:USDT"

                # Fetch recent funding rate history
                history = self.exchange.fetch_funding_rate_history(perp_symbol, limit=limit)
                if len(history) < params["filter_periods"]:
                    print(f"Not enough historical data for {symbol} to form a signal. Skipping.")
                    continue

                # Process the data just like in our backtester
                df = pd.DataFrame(history)
                df["apr"] = (df["fundingRate"].astype(float) * 3 * 365) * 100
                df["rolling_apr_avg"] = df["apr"].rolling(window=params["filter_periods"]).mean()

                # Get the most recent, complete data point
                latest_data = df.iloc[-1]

                current_apr = latest_data["apr"]
                rolling_avg = latest_data["rolling_apr_avg"]
                entry_threshold = params["entry_apr"]

                print(
                    f"  - {symbol}: Current APR={current_apr:.2f}%, Avg APR={rolling_avg:.2f}%, Entry Threshold={entry_threshold:.2f}%"
                )

                # The core entry condition
                if current_apr > entry_threshold and rolling_avg > entry_threshold:
                    signal = {"symbol": symbol, "current_apr": current_apr, "action": "ENTER"}
                    signals.append(signal)
                    print(f"  >>> Signal FOUND for {symbol}! <<<")

            except Exception as e:
                print(f"Could not process signal for {symbol}. Reason: {e}")

        return signals


# --- Self-Testing Block ---
if __name__ == "__main__":
    # This allows us to test the Strategy module independently.
    load_dotenv()

    # Configure CCXT to use the production environment for live data
    exchange = ccxt.binance(
        {
            "enableRateLimit": True,
            "options": {"defaultType": "future"},
            "apiKey": os.getenv("BINANCE_API_KEY"),
            "secret": os.getenv("BINANCE_SECRET_KEY"),
        }
    )

    strategy = FundingArbStrategy(exchange)

    print("\n--- Testing with €100 Capital ---")
    signals_100 = strategy.check_signals(current_capital=100)
    if not signals_100:
        print("No signals found for €100 capital.")
    else:
        print("Found Signals:", signals_100)

    print("\n--- Testing with €500 Capital ---")
    signals_500 = strategy.check_signals(current_capital=500)
    if not signals_500:
        print("No signals found for €500 capital.")
    else:
        print("Found Signals:", signals_500)

    print("\n--- Testing with €1000 Capital ---")
    signals_1000 = strategy.check_signals(current_capital=1000)
    if not signals_1000:
        print("No signals found for €1000 capital.")
    else:
        print("Found Signals:", signals_1000)
