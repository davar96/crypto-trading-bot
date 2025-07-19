import pandas as pd
from .logger import logger


class Strategy:
    def __init__(self, sma_period=20, rsi_period=14, rsi_overbought=70, rsi_oversold=35):
        self.sma_period = sma_period
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        logger.info(f"Strategy: Initialized with SMA({sma_period}) and RSI({rsi_period})")

    def _calculate_rsi(self, data, period):
        delta = data["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def get_signal(self, ohlcv_data, current_price):
        """
        Improved strategy with better filters
        """
        if len(ohlcv_data) < max(self.sma_period, self.rsi_period) + 10:
            return {"signal": "HOLD", "sma": None, "rsi": None}

        df = pd.DataFrame(ohlcv_data, columns=["timestamp", "open", "high", "low", "close", "volume"])

        # Calculate indicators
        df["sma"] = df["close"].rolling(window=self.sma_period).mean()
        df["rsi"] = self._calculate_rsi(df, period=self.rsi_period)

        # Calculate trend strength
        df["sma_slope"] = df["sma"].diff(5) / df["sma"].shift(5) * 100  # 5-period SMA change %

        # Get latest values
        latest_sma = df["sma"].iloc[-1]
        latest_rsi = df["rsi"].iloc[-1]
        latest_slope = df["sma_slope"].iloc[-1]
        prev_close = df["close"].iloc[-2]

        # Price distance from SMA
        distance_from_sma = ((current_price - latest_sma) / latest_sma) * 100

        signal = "HOLD"

        # IMPROVED BUY CONDITIONS:
        # 1. Price above SMA (uptrend)
        # 2. RSI not overbought (room to grow)
        # 3. SMA is rising (trend strength)
        # 4. Price not too far from SMA (not chasing)
        # 5. Current candle is green (momentum)
        if (
            current_price > latest_sma
            and latest_rsi < self.rsi_overbought
            and latest_rsi > self.rsi_oversold  # Not oversold (avoid catching falling knife)
            and latest_slope > 0.1  # SMA rising at least 0.1%
            and distance_from_sma < 2.0  # Price within 2% of SMA
            and current_price > prev_close
        ):  # Green candle
            signal = "BUY"
            logger.debug(
                f"BUY signal: RSI={latest_rsi:.1f}, Slope={latest_slope:.2f}%, Distance={distance_from_sma:.2f}%"
            )

        # SELL CONDITIONS:
        # 1. Price below SMA
        # 2. Or RSI overbought
        # 3. Or SMA turning down
        elif current_price < latest_sma or latest_rsi > self.rsi_overbought or latest_slope < -0.1:
            signal = "SELL"

        return {
            "signal": signal,
            "sma": latest_sma,
            "rsi": latest_rsi,
            "slope": latest_slope,
            "distance": distance_from_sma,
        }
