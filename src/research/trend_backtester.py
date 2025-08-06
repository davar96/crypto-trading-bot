# src/research/trend_backtester.py (Version 1.6 - Dynamic Engine)

import pandas as pd
import numpy as np
import random
from datetime import datetime
import matplotlib.pyplot as plt
import sys
import os

FOMC_DATES = [
    "2022-01-26",
    "2022-03-16",
    "2022-05-04",
    "2022-06-15",
    "2022-07-27",
    "2022-09-21",
    "2022-11-02",
    "2022-12-14",
    "2023-02-01",
    "2023-03-22",
    "2023-05-03",
    "2023-06-14",
    "2023-07-26",
    "2023-09-20",
    "2023-11-01",
    "2023-12-13",
    "2024-01-31",
    "2024-03-20",
    "2024-05-01",
    "2024-06-12",
    "2024-07-31",
    "2024-09-18",
    "2024-11-07",
    "2024-12-18",
]


class TrendBacktester:
    """
    A dynamic backtester that can test multiple, complex entry setups as per
    the mentor's final specifications.
    """

    def __init__(self, data, params, test_name="Default"):
        self.data = data.copy()
        self.params = params
        self.test_name = test_name
        self.spread, self.slippage, self.fee_rate = 0.0005, 0.0005, 0.001
        self.equity, self.equity_curve, self.trades, self.open_positions = 100.0, [], [], []

    def _calculate_indicators(self):
        """Calculates all indicators needed for all possible setups."""
        # --- Standard Indicators ---
        self.data["sma_200"] = self.data["close"].rolling(window=self.params.get("sma_period", 200)).mean()
        self.data["sma_50"] = self.data["close"].rolling(window=50).mean()

        delta = self.data["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=self.params.get("rsi_period", 14)).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.params.get("rsi_period", 14)).mean()
        self.data["rsi"] = 100 - (100 / (1 + (gain / loss)))

        self.data["volume_sma_20"] = self.data["volume"].rolling(window=20).mean()

        # --- ATR ---
        tr_df = pd.DataFrame(
            {
                "hl": self.data["high"] - self.data["low"],
                "hc": np.abs(self.data["high"] - self.data["close"].shift()),
                "lc": np.abs(self.data["low"] - self.data["close"].shift()),
            }
        )
        self.data["atr_14"] = tr_df.max(axis=1).rolling(window=14).mean()

        # --- Indicators for New Setups ---
        self.data["vwap"] = (self.data["volume"] * (self.data["high"] + self.data["low"]) / 2).cumsum() / self.data[
            "volume"
        ].cumsum()
        self.data["rolling_max_10d"] = self.data["close"].rolling(window=10).max()
        self.data["pullback_5pct"] = self.data["close"] < (self.data["rolling_max_10d"] * 0.95)

        self.data["is_fomc"] = self.data.index.strftime("%Y-%m-%d").isin(FOMC_DATES)
        self.data.dropna(inplace=True)

    def _check_entry_conditions(self, row):
        """Acts as a router to the correct entry setup function."""
        setup = self.params.get("entry_setup", "A")  # Default to classic trend
        if setup == "A":
            return self._check_setup_A_classic_trend(row)
        if setup == "B":
            return self._check_setup_B_pullback_to_50d(row)
        if setup == "C":
            return self._check_setup_C_volume_spike(row)
        return False

    def _check_common_filters(self, row):
        """Checks filters that apply to all strategies."""
        if len(self.open_positions) >= self.params["max_positions"]:
            return False
        candle_not_extended = (row["close"] - row["open"]) / row["open"] < 0.05
        volatility_normal = (row["atr_14"] / row["close"]) < 0.03
        not_event_day = not row["is_fomc"]
        return all([candle_not_extended, volatility_normal, not_event_day])

    def _check_setup_A_classic_trend(self, row):
        if not self._check_common_filters(row):
            return False
        above_sma = row["close"] > row["sma_200"]
        rsi_not_overbought = row["rsi"] < self.params["rsi_entry_max"]
        volume_conf = row["volume"] > row["volume_sma_20"]
        return all([above_sma, rsi_not_overbought, volume_conf])

    def _check_setup_B_pullback_to_50d(self, row):
        if not self._check_common_filters(row):
            return False
        above_50d_sma = row["close"] > row["sma_50"]
        is_pullback = row["pullback_5pct"]
        return all([above_50d_sma, is_pullback])

    def _check_setup_C_volume_spike(self, row):
        if not self._check_common_filters(row):
            return False
        price_above_vwap = row["close"] > row["vwap"]
        volume_spike = row["volume"] > (row["volume_sma_20"] * 2)  # Volume is 2x the average
        return all([price_above_vwap, volume_spike])

    def run_backtest(self, show_plot=True):
        # (The core run_backtest, _get_execution_price, _calculate_stats, etc. methods
        # remain IDENTICAL to Version 1.5, as they correctly handle the trading logic.
        # We are only changing the *signal generation* part.)
        self._calculate_indicators()
        if self.data.empty:
            return {"error": "No data available for backtest."}

        for i, row in self.data.iterrows():
            positions_to_close = []
            for pos in self.open_positions:
                exit_reason, exit_price = None, None
                if row["low"] <= pos["stop_loss"]:
                    exit_reason, atr_pct = "Stop Loss", row["atr_14"] / pos["stop_loss"]
                    exit_price = self._get_execution_price(pos["stop_loss"], "stop_loss", atr_pct)
                elif row["high"] >= pos["take_profit"]:
                    exit_reason = "Take Profit"
                    exit_price = self._get_execution_price(pos["take_profit"], "sell", 0)
                if exit_reason:
                    pnl = (exit_price - pos["entry_price"]) * pos["size"]
                    total_fees = (pos["entry_price"] * pos["size"] + exit_price * pos["size"]) * self.fee_rate
                    net_pnl = pnl - total_fees
                    self.equity += net_pnl
                    pos.update({"exit_date": i, "exit_price": exit_price, "pnl": net_pnl, "exit_reason": exit_reason})
                    self.trades.append(pos)
                    positions_to_close.append(pos)
            self.open_positions = [p for p in self.open_positions if p not in positions_to_close]
            if self._check_entry_conditions(row):
                if random.random() < 0.05:
                    continue
                atr_pct = row["atr_14"] / row["close"]
                entry_price = self._get_execution_price(row["close"], "buy", atr_pct)
                position_size_usd = self.equity * (self.params["position_size_pct"] / 100.0)
                size_in_asset = position_size_usd / entry_price
                stop_loss_price = entry_price * (1 - self.params["stop_loss_pct"] / 100.0)
                take_profit_price = entry_price * (1 + self.params["take_profit_pct"] / 100.0)
                position = {
                    "entry_date": i,
                    "entry_price": entry_price,
                    "size": size_in_asset,
                    "stop_loss": stop_loss_price,
                    "take_profit": take_profit_price,
                }
                self.open_positions.append(position)
            self.equity_curve.append({"timestamp": i, "equity": self.equity})

        return self._calculate_stats(show_plot=show_plot)

    # All helper methods like _get_execution_price, _save_trade_log, _sanity_check_results, etc.
    # are assumed to be here, identical to Version 1.5
    # For brevity, only showing the parts that changed. The full code would include them.

    def _get_execution_price(self, ideal_price, side, atr_pct):
        if side == "buy":
            price = ideal_price * (1 + self.spread + self.slippage)
        elif side == "sell":
            price = ideal_price * (1 - self.spread - self.slippage)
        elif side == "stop_loss":
            volatility_slippage = self.slippage * (1 + atr_pct * 5)
            price = ideal_price * (1 - self.spread - self.slippage - volatility_slippage)
        return price

    def _sanity_check_results(self, results, num_years):
        trades_per_year = results["Total Trades"] / num_years if num_years > 0 else 0
        if results["Sharpe Ratio"] > 2.0:
            print("  - WARNING: Sharpe Ratio > 2.0. Likely overfit.")
        if results["Max Drawdown (%)"] < 10.0 and results["Total Trades"] > 10:
            print("  - WARNING: Max Drawdown < 10%. Highly unusual.")
        if results["Win Rate (%)"] > 55.0:
            print("  - WARNING: Win Rate > 55%. Highly unusual.")
        if trades_per_year < 12 and results["Total Trades"] > 5:
            print(f"  - WARNING: Trades per year ({trades_per_year:.1f}) is low.")

    def _save_trade_log(self):
        if not self.trades:
            return
        log_df = pd.DataFrame(self.trades)
        log_df["entry_date"] = pd.to_datetime(log_df["entry_date"]).dt.strftime("%Y-%m-%d")
        log_df["exit_date"] = pd.to_datetime(log_df["exit_date"]).dt.strftime("%Y-%m-%d")
        log_df = log_df[["entry_date", "exit_date", "entry_price", "exit_price", "pnl", "exit_reason"]]
        if not os.path.exists("research_results"):
            os.makedirs("research_results")
        filename = f"research_results/trade_log_{self.test_name}.csv"
        log_df.to_csv(filename, index=False)

    def _calculate_stats(self, show_plot=True):
        self._save_trade_log()
        if not self.trades:
            return {"error": "No trades were executed."}
        equity_df = pd.DataFrame(self.equity_curve).set_index("timestamp")
        num_years = (equity_df.index[-1] - equity_df.index[0]).days / 365.25
        total_return = (self.equity / 100.0) - 1
        daily_returns = equity_df["equity"].pct_change().dropna()
        sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(365) if daily_returns.std() > 0 else 0
        max_drawdown = abs((equity_df["equity"] / equity_df["equity"].cummax() - 1).min())
        pnls = [t["pnl"] for t in self.trades]
        wins, losses = [p for p in pnls if p > 0], [p for p in pnls if p < 0]
        win_rate = len(wins) / len(pnls) if len(pnls) > 0 else 0
        profit_factor = sum(wins) / abs(sum(losses)) if sum(losses) != 0 else float("inf")
        stats = {
            "Total Return (%)": total_return * 100,
            "Sharpe Ratio": sharpe_ratio,
            "Max Drawdown (%)": max_drawdown * 100,
            "Win Rate (%)": win_rate * 100,
            "Profit Factor": profit_factor,
            "Total Trades": len(self.trades),
        }
        self._sanity_check_results(stats, num_years)
        if show_plot:
            self._plot_results(equity_df, stats)
        return stats

    def _plot_results(self, equity_df, stats):
        plt.figure(figsize=(15, 7))
        equity_df["equity"].plot()
        plt.title(
            f"Backtest: {self.test_name}\nSharpe: {stats['Sharpe Ratio']:.2f} | Max DD: {stats['Max Drawdown (%)']:.2f}% | Trades: {stats['Total Trades']}"
        )
        plt.ylabel("Portfolio Value ($)"), plt.xlabel("Date"), plt.grid(True), plt.show()


if __name__ == "__main__":
    print("===== DYNAMIC ENGINE: SINGLE TEST RUN =====")
    try:
        full_data_df = pd.read_csv("data/BTC_USDT_1d_ohlcv.csv", index_col="timestamp", parse_dates=True)
    except FileNotFoundError:
        print("ERROR: Please download BTC/USDT 1-day OHLCV data starting from 2018.")
        sys.exit()

    # --- Test ONE of the new setups to ensure it works ---
    test_params = {
        "entry_setup": "B",  # Test the "Pullback to 50d" strategy
        "sma_period": 200,
        "rsi_period": 14,
        "rsi_entry_max": 75,  # Still needed for filters
        "stop_loss_pct": 5,
        "take_profit_pct": 15,
        "position_size_pct": 25,
        "max_positions": 2,
    }

    backtester = TrendBacktester(data=full_data_df, params=test_params, test_name="Setup_B_Pullback_Test")
    final_stats = backtester.run_backtest(show_plot=True)

    print("\n--- Single Test Finished ---")
    if "error" not in final_stats:
        for key, value in final_stats.items():
            print(f"{key:<20}: {value:.2f}")
