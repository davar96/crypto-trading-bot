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

    # In src/bot/strategy.py, replace the get_signal method

    def get_signal(self, ohlcv_5m, ohlcv_1h, current_price):
        """
        MODIFIED V6: Professional Overhaul.
        Adds a minimum volatility filter to avoid chop.
        """
        # --- 1. The Higher Timeframe (1-Hour) Trend Filter (No Change) ---
        if len(ohlcv_1h) < self.sma_period:
            return {"signal": "HOLD"}
        df_1h = pd.DataFrame(ohlcv_1h, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df_1h["sma"] = df_1h["close"].rolling(window=self.sma_period).mean()
        last_1h_candle = df_1h.iloc[-2]
        is_h1_uptrend = last_1h_candle["close"] > last_1h_candle["sma"]

        if not is_h1_uptrend:
            return {"signal": "HOLD", "h1_trend": "DOWN"}

        # --- 2. The Lower Timeframe (5-Minute) Analysis ---
        if len(ohlcv_5m) < max(self.sma_period, self.rsi_period, self.atr_period) + 10:
            return {"signal": "HOLD", "h1_trend": "UP"}

        df_5m = pd.DataFrame(ohlcv_5m, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df_5m["sma"] = df_5m["close"].rolling(window=self.sma_period).mean()
        df_5m["rsi"] = self._calculate_rsi(df_5m, period=self.rsi_period)
        df_5m["atr"] = self._calculate_atr(df_5m, period=self.atr_period)

        latest_5m = df_5m.iloc[-1]
        latest_atr = latest_5m["atr"]

        # --- NEW: Volatility Filter ---
        # Don't trade if the market is dead flat (chop zone)
        # We define "flat" as an ATR less than 0.4% of the current price
        min_volatility = current_price * 0.004
        if latest_atr < min_volatility:
            logger.debug(
                f"Signal ignored for {current_price}: Low volatility. ATR ({latest_atr:.4f}) is below threshold ({min_volatility:.4f})."
            )
            return {"signal": "HOLD", "h1_trend": "UP"}
        # --- END OF NEW FILTER ---

        signal = "HOLD"

        # --- Optimized Entry Logic (No Change) ---
        rsi_crossed_up = False
        for i in range(-4, -1):
            if df_5m.iloc[i + 1]["rsi"] > self.rsi_oversold and df_5m.iloc[i]["rsi"] <= self.rsi_oversold:
                rsi_crossed_up = True
                break

        prev_5m = df_5m.iloc[-2]
        is_confirmation_candle = prev_5m["close"] > prev_5m["open"]

        if rsi_crossed_up and is_confirmation_candle:
            signal = "BUY"
            logger.debug(f"BUY (Pro) signal: H1 Trend UP, Volatility OK, Confirmed 5m dip entry.")

        return {"signal": signal, "atr": latest_atr, "h1_trend": "UP"}
