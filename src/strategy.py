# src/strategy.py (Version 1.1)

import ccxt
import pandas as pd
from dotenv import load_dotenv
import os


class FundingArbStrategy:
    def __init__(self, exchange):
        self.exchange = exchange
        self.optimal_params = {
            "BTC/USDT": {"entry_apr": 15.0, "exit_apr": 3.0, "filter_periods": 3},
            "ETH/USDT": {"entry_apr": 15.0, "exit_apr": 3.0, "filter_periods": 12},
            "SOL/USDT": {"entry_apr": 12.0, "exit_apr": 3.0, "filter_periods": 9},
            "DOGE/USDT": {"entry_apr": 12.0, "exit_apr": 4.0, "filter_periods": 3},
        }
        self.capital_tiers = {
            100: ["DOGE/USDT"],
            200: ["DOGE/USDT", "SOL/USDT"],
            500: ["DOGE/USDT", "SOL/USDT", "ETH/USDT"],
            1000: ["DOGE/USDT", "SOL/USDT", "ETH/USDT", "BTC/USDT"],
        }

    def get_eligible_assets(self, current_capital):
        eligible_assets = []
        for threshold, assets in sorted(self.capital_tiers.items()):
            if current_capital >= threshold:
                eligible_assets = assets
        return eligible_assets

    def check_entry_signals(self, current_capital):
        eligible_assets = self.get_eligible_assets(current_capital)
        if not eligible_assets:
            print("Capital too low to trade any assets.")
            return []
        print(f"Capital: €{current_capital:.2f}. Eligible assets to scan for ENTRY: {eligible_assets}")
        signals = []
        for symbol in eligible_assets:
            params = self.optimal_params.get(symbol)
            if not params:
                continue
            try:
                limit = params["filter_periods"] + 5
                perp_symbol = f"{symbol.split('/')[0]}/USDT:USDT"
                history = self.exchange.fetch_funding_rate_history(perp_symbol, limit=limit)
                if len(history) < params["filter_periods"]:
                    print(f"Not enough historical data for {symbol}. Skipping.")
                    continue
                df = pd.DataFrame(history)
                df["apr"] = (df["fundingRate"].astype(float) * 3 * 365) * 100
                df["rolling_apr_avg"] = df["apr"].rolling(window=params["filter_periods"]).mean()
                latest_data = df.iloc[-1]
                current_apr, rolling_avg, entry_threshold = (
                    latest_data["apr"],
                    latest_data["rolling_apr_avg"],
                    params["entry_apr"],
                )
                print(
                    f"  - {symbol}: Current APR={current_apr:.2f}%, Avg APR={rolling_avg:.2f}%, Entry Threshold={entry_threshold:.2f}%"
                )
                if current_apr > entry_threshold and rolling_avg > entry_threshold:
                    signals.append({"symbol": symbol, "current_apr": current_apr, "action": "ENTER"})
                    print(f"  >>> Signal FOUND for {symbol}! <<<")
            except Exception as e:
                print(f"Could not process signal for {symbol}. Reason: {e}")
        return signals

    # --- NEW METHOD ---
    def check_exit_signal(self, open_position):
        """
        Checks if an open position should be closed based on the exit APR threshold.
        """
        symbol = open_position["symbol"]
        params = self.optimal_params.get(symbol)
        if not params:
            return False

        print(f"Checking exit condition for open position: {symbol}")
        try:
            perp_symbol = f"{symbol.split('/')[0]}/USDT:USDT"
            rate_data = self.exchange.fetch_funding_rate(perp_symbol)
            current_funding_rate = rate_data.get("fundingRate")
            if current_funding_rate is None:
                return False

            current_apr = (current_funding_rate * 3 * 365) * 100
            exit_threshold = params["exit_apr"]

            print(f"  - {symbol}: Current APR={current_apr:.2f}%, Exit Threshold={exit_threshold:.2f}%")
            if current_apr < exit_threshold:
                print(f"  >>> EXIT Signal FOUND for {symbol}! <<<")
                return True
        except Exception as e:
            print(f"Could not check exit signal for {symbol}. Reason: {e}")
        return False
