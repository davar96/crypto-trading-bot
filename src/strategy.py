# src/strategy.py (Version 1.2 - With Signal Validation)

import ccxt
import pandas as pd
from dotenv import load_dotenv
import os
import time


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

    # --- NEW VALIDATION METHOD ---
    def validate_signal(self, symbol, latest_data):
        """
        Performs sanity checks on the data before confirming a signal.
        Returns True if the signal is valid, False otherwise.
        """
        try:
            # Check 1: Data Freshness (using the timestamp from the funding rate data)
            data_timestamp_ms = latest_data["timestamp"]
            current_timestamp_ms = int(time.time() * 1000)
            time_diff_seconds = (current_timestamp_ms - data_timestamp_ms) / 1000

            # Funding data is typically 8 hours old. We'll allow up to 9 hours to be safe.
            if time_diff_seconds > 9 * 3600:
                print(f"  - VALIDATION FAILED for {symbol}: Data is stale ({time_diff_seconds / 3600:.2f} hours old).")
                return False

            # Check 2: Reasonable Funding Rate (APR between 5% and 1500%)
            # We use a slightly lower bound to ensure the signal is strong enough.
            current_apr = latest_data["apr"]
            if not (5.0 < current_apr < 1500.0):
                print(
                    f"  - VALIDATION FAILED for {symbol}: APR ({current_apr:.2f}%) is outside reasonable range (5%-1500%)."
                )
                return False

            # Check 3: Basis Spread (placeholder for now, as it requires more API calls)
            # This is a good place to add the check in a future version.

            return True  # All checks passed
        except Exception as e:
            print(f"  - VALIDATION ERROR for {symbol}: {e}")
            return False

    def get_eligible_assets(self, current_capital):
        eligible_assets = []
        for threshold, assets in sorted(self.capital_tiers.items()):
            if current_capital >= threshold:
                eligible_assets = assets
        return eligible_assets

    def check_entry_signals(self, current_capital):
        eligible_assets = self.get_eligible_assets(current_capital)
        if not eligible_assets:
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
                    continue

                df = pd.DataFrame(history)
                df["apr"] = (df["fundingRate"].astype(float) * 3 * 365) * 100
                df["rolling_apr_avg"] = df["apr"].rolling(window=params["filter_periods"]).mean()
                latest_data = df.iloc[-1]

                print(
                    f"  - {symbol}: Current APR={latest_data['apr']:.2f}%, Avg APR={latest_data['rolling_apr_avg']:.2f}%, Entry Threshold={params['entry_apr']:.2f}%"
                )

                # --- MODIFIED: Added validation step ---
                if self.validate_signal(symbol, latest_data):
                    if (
                        latest_data["apr"] > params["entry_apr"]
                        and latest_data["rolling_apr_avg"] > params["entry_apr"]
                    ):
                        signals.append({"symbol": symbol, "current_apr": latest_data["apr"], "action": "ENTER"})
                        print(f"  >>> Signal VALIDATED and CONFIRMED for {symbol}! <<<")
                else:
                    print(f"  - Signal for {symbol} REJECTED due to failed validation.")

            except Exception as e:
                print(f"Could not process signal for {symbol}. Reason: {e}")
        return signals

    def check_exit_signal(self, open_position):
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
