# src/bot/strategy.py

import pandas as pd
from .logger import logger
import numpy as np  # It's good practice to import numpy for NaN


class Strategy:
    def __init__(
        self,
        sma_period=20,
        rsi_period=14,
        atr_period=14,
        rsi_overbought=70,
        rsi_oversold=40,
    ):
        self.sma_period = sma_period
        self.rsi_period = rsi_period
        self.atr_period = atr_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        logger.info(f"Strategy: Initialized with SMA({sma_period}), RSI({rsi_period}), ATR({atr_period})")

    def _calculate_rsi(self, data, period):
        delta = data["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        # Avoid division by zero
        rs = gain / loss
        rs[loss == 0] = np.inf  # If loss is 0, RS is infinite

        return 100 - (100 / (1 + rs))

    def _calculate_atr(self, data, period):
        """Calculates the Average True Range (ATR)"""
        high_low = data["high"] - data["low"]
        high_close = (data["high"] - data["close"].shift()).abs()
        low_close = (data["low"] - data["close"].shift()).abs()

        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

        return tr.rolling(window=period).mean()

    def get_signal(self, ohlcv_data, current_price):
        """
        MODIFIED: "Buy the Dip" in an uptrend.
        """
        if len(ohlcv_data) < max(self.sma_period, self.rsi_period, self.atr_period) + 10:
            return {"signal": "HOLD", "sma": None, "rsi": None, "atr": None}

        df = pd.DataFrame(ohlcv_data, columns=["timestamp", "open", "high", "low", "close", "volume"])

        # --- Indicator Calculations (no change) ---
        df["sma"] = df["close"].rolling(window=self.sma_period).mean()
        df["rsi"] = self._calculate_rsi(df, period=self.rsi_period)
        df["atr"] = self._calculate_atr(df, period=self.atr_period)
        df["sma_slope"] = df["sma"].diff(5) / df["sma"].shift(5) * 100

        # --- Get Latest Values (no change) ---
        latest_sma = df["sma"].iloc[-1]
        latest_rsi = df["rsi"].iloc[-1]
        prev_rsi = df["rsi"].iloc[-2]  # Get previous RSI to detect crossover
        latest_slope = df["sma_slope"].iloc[-1]
        latest_atr = df["atr"].iloc[-1]

        signal = "HOLD"

        # --- NEW "BUY THE DIP" CONDITIONS ---
        # 1. Overall trend must be up.
        is_uptrend = current_price > latest_sma and latest_slope > 0.05  # Loosened slope slightly

        # 2. We are looking for a dip (RSI was low) and is now recovering.
        #    This is a classic "buy the dip" signal.
        rsi_buy_signal = latest_rsi > self.rsi_oversold and prev_rsi <= self.rsi_oversold

        if is_uptrend and rsi_buy_signal:
            signal = "BUY"
            logger.debug(f"BUY (Pullback) signal: RSI crossed above {self.rsi_oversold}. Trend is UP.")

        # --- SELL CONDITIONS (still disabled in bot, but kept for completeness) ---
        elif current_price < latest_sma or latest_rsi > self.rsi_overbought:
            signal = "SELL"

        return {
            "signal": signal,
            "sma": latest_sma,
            "rsi": latest_rsi,
            "slope": latest_slope,
            "atr": latest_atr,
        }
