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

    def get_signal(self, ohlcv_5m, ohlcv_1h, current_price):
        """
        MODIFIED V5: Optimized Entry Logic.
        Removes the 5m trend filter to better catch dips and uses a lookback for the RSI crossover.
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

        # --- 2. The Lower Timeframe (5-Minute) Entry Trigger (MODIFIED) ---
        if len(ohlcv_5m) < max(self.sma_period, self.rsi_period, self.atr_period) + 10:
            return {"signal": "HOLD", "h1_trend": "UP"}

        df_5m = pd.DataFrame(ohlcv_5m, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df_5m["sma"] = df_5m["close"].rolling(window=self.sma_period).mean()
        df_5m["rsi"] = self._calculate_rsi(df_5m, period=self.rsi_period)
        df_5m["atr"] = self._calculate_atr(df_5m, period=self.atr_period)

        latest_5m = df_5m.iloc[-1]

        signal = "HOLD"

        # --- NEW OPTIMIZED ENTRY LOGIC ---

        # Condition 1: Look for an RSI crossover within the last 3 closed candles.
        rsi_crossed_up = False
        # We check the 3 most recent closed candles (indices -4, -3, -2)
        for i in range(-4, -1):
            if df_5m.iloc[i + 1]["rsi"] > self.rsi_oversold and df_5m.iloc[i]["rsi"] <= self.rsi_oversold:
                rsi_crossed_up = True
                break

        # Condition 2: The most recent closed candle must be a green confirmation candle.
        prev_5m = df_5m.iloc[-2]
        is_confirmation_candle = prev_5m["close"] > prev_5m["open"]

        # We no longer require the 5m trend to be up, as a dip can temporarily break it.
        # The H1 trend is our primary directional filter.
        if rsi_crossed_up and is_confirmation_candle:
            signal = "BUY"
            logger.debug(f"BUY (Optimized MTA) signal: H1 Trend is UP. 5m confirmed dip entry.")

        return {"signal": signal, "atr": latest_5m["atr"], "h1_trend": "UP"}
