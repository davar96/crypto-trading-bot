# src/research/multi_frame_backtester.py (Version 1.2 - Corrected Data Alignment)

import pandas as pd
import numpy as np
import random
import os
import sys
import matplotlib.pyplot as plt
import datetime

TIMEFRAME_CONFIG = {
    "1d": {
        "sma_period": 200,
        "rsi_period": 14,
        "rsi_entry_max": 70,
        "stop_loss": 0.07,
        "take_profit": 0.20,
        "position_size_pct": 25,
    },
    "4h": {
        "sma_period": 120,
        "rsi_period": 14,
        "rsi_entry_max": 65,
        "stop_loss": 0.04,
        "take_profit": 0.12,
        "position_size_pct": 15,
    },
    "1h": {
        "sma_period": 100,
        "rsi_period": 14,
        "rsi_entry_max": 60,
        "stop_loss": 0.025,
        "take_profit": 0.075,
        "position_size_pct": 10,
    },
}
RISK_CONFIG = {
    "max_total_exposure_pct": 60,
    "min_cash_reserve_pct": 30,
    "max_positions_per_timeframe": 1,
    "max_positions_total": 3,
}


class MultiFrameBacktester:
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

    def __init__(self, symbol, data, start_capital=100.0):
        self.symbol = symbol
        self.data = data
        self.capital = start_capital
        self.equity_curve, self.trades, self.open_positions = [], [], {}
        self.spread, self.slippage, self.fee_rate = 0.0005, 0.0005, 0.001
        self.aligned_data = self._align_data()

    def _align_data(self):
        print("--- Aligning Multi-Timeframe Data ---")
        # --- BUG FIX: A more robust alignment method ---
        # First, calculate indicators on each separate dataframe
        for tf, config in TIMEFRAME_CONFIG.items():
            self._calculate_indicators(self.data[tf], config)

        # Then, use the 1h data as the primary loop driver
        aligned_df = self.data["1h"].copy()

        # Merge higher timeframes, adding suffixes to their columns
        for tf in ["4h", "1d"]:
            # Rename columns BEFORE the merge
            tf_data_renamed = self.data[tf].rename(columns=lambda c: f"{c}_{tf}")
            aligned_df = pd.merge_asof(
                aligned_df, tf_data_renamed, left_index=True, right_index=True, direction="backward"
            )

        aligned_df.dropna(inplace=True)
        print("Data alignment complete.")
        return aligned_df
        # --- END BUG FIX ---

    def _calculate_indicators(self, df, config):
        # This function no longer needs the 'tf' parameter as it operates on one df at a time
        df[f'sma_{config["sma_period"]}'] = df["close"].rolling(window=config["sma_period"]).mean()
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=config["rsi_period"]).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=config["rsi_period"]).mean()
        df["rsi"] = 100 - (100 / (1 + (gain / loss)))
        df[f"volume_sma_20"] = df["volume"].rolling(window=20).mean()
        tr_df = pd.DataFrame(
            {
                "hl": df["high"] - df["low"],
                "hc": np.abs(df["high"] - df["close"].shift()),
                "lc": np.abs(df["low"] - df["close"].shift()),
            }
        )
        df["atr_14"] = tr_df.max(axis=1).rolling(window=14).mean()
        df["candle_extended"] = (df["close"] - df["open"]) / df["open"] > 0.05
        df["volatility_high"] = (df["atr_14"] / df["close"]) > 0.03
        df["is_fomc"] = df.index.strftime("%Y-%m-%d").isin(self.FOMC_DATES)
        # Note: We dropna() in the alignment step, not here.

    def _check_signal(self, row, tf, config):
        suffix = f"_{tf}" if tf != "1h" else ""
        if f"{self.symbol}_{tf}" in self.open_positions:
            return None

        # Construct the column names correctly based on the suffix
        close_col = f"close{suffix}"
        sma_col = f'sma_{config["sma_period"]}{suffix}'
        rsi_col = f"rsi{suffix}"
        candle_col = f"candle_extended{suffix}"
        vol_col = f"volatility_high{suffix}"
        fomc_col = f"is_fomc{suffix}"
        volume_col = f"volume{suffix}"
        volume_sma_col = f"volume_sma_20{suffix}"

        if row[candle_col] or row[vol_col] or row[fomc_col]:
            return None

        if row[close_col] > row[sma_col] and row[rsi_col] < config["rsi_entry_max"]:
            if row[volume_col] > row[volume_sma_col]:
                return "BUY"
        return None

    # ... (The rest of the file remains identical to the last version)
    # The run_backtest, _resolve_signals, _get_execution_price, _calculate_stats, and _plot_results methods are unchanged.
    def _resolve_signals(self, signals):
        if signals.get("1d") == "SELL":
            return []
        for tf in ["1d", "4h", "1h"]:
            if signals.get(tf) == "BUY":
                if (
                    f"{self.symbol}_{tf}" not in self.open_positions
                    and len(self.open_positions) < RISK_CONFIG["max_positions_total"]
                ):
                    return [tf]
        return []

    def _get_execution_price(self, ideal_price, side, atr_pct=0):
        if side == "buy":
            price = ideal_price * (1 + self.spread + self.slippage)
        elif side == "sell":
            price = ideal_price * (1 - self.spread - self.slippage)
        elif side == "stop_loss":
            volatility_slippage = self.slippage * (1 + atr_pct * 5)
            price = ideal_price * (1 - self.spread - self.slippage - volatility_slippage)
        return price

    def run_backtest(self, show_plot=True):
        print(f"--- Running Backtest for {self.symbol} ---")
        for i, row in self.aligned_data.iterrows():
            timestamp = i
            positions_to_close = []
            for pos_key, pos in self.open_positions.items():
                exit_reason, exit_price = None, None
                if row["low"] <= pos["stop_loss"]:
                    exit_reason, atr_pct = "Stop Loss", row["atr_14"] / pos["stop_loss"]
                    exit_price = self._get_execution_price(pos["stop_loss"], "stop_loss", atr_pct)
                elif row["high"] >= pos["take_profit"]:
                    exit_reason, exit_price = "Take Profit", self._get_execution_price(pos["take_profit"], "sell")
                if exit_reason:
                    pnl = (exit_price - pos["entry_price"]) * pos["size"]
                    total_fees = (pos["entry_price"] * pos["size"] + exit_price * pos["size"]) * self.fee_rate
                    net_pnl = pnl - total_fees
                    self.capital += net_pnl
                    pos.update(
                        {
                            "exit_date": timestamp,
                            "exit_price": exit_price,
                            "pnl": net_pnl,
                            "exit_reason": exit_reason,
                            "net_pnl": net_pnl,
                        }
                    )
                    self.trades.append(pos)
                    positions_to_close.append(pos_key)
            for key in positions_to_close:
                del self.open_positions[key]
            signals = {tf: self._check_signal(row, tf, config) for tf, config in TIMEFRAME_CONFIG.items()}
            signals_to_take = self._resolve_signals(signals)
            for tf in signals_to_take:
                if random.random() < 0.05:
                    continue
                config = TIMEFRAME_CONFIG[tf]
                atr_pct = row["atr_14"] / row["close"]
                entry_price = self._get_execution_price(row["close"], "buy", atr_pct)
                position_size_usd = self.capital * (config["position_size_pct"] / 100.0)
                size_in_asset = position_size_usd / entry_price
                stop_loss_price, take_profit_price = entry_price * (1 - config["stop_loss"]), entry_price * (
                    1 + config["take_profit"]
                )
                position_key = f"{self.symbol}_{tf}"
                position = {
                    "key": position_key,
                    "tf": tf,
                    "entry_date": timestamp,
                    "entry_price": entry_price,
                    "size": size_in_asset,
                    "stop_loss": stop_loss_price,
                    "take_profit": take_profit_price,
                    "notional": position_size_usd,
                }
                self.open_positions[position_key] = position
            self.equity_curve.append({"timestamp": timestamp, "equity": self.capital})
        return self._calculate_stats(show_plot=show_plot)

    def _calculate_stats(self, show_plot=True):
        if not self.trades:
            return {"error": "No trades were executed."}
        equity_df = pd.DataFrame(self.equity_curve).set_index("timestamp")
        total_return = (self.capital / 100.0) - 1
        daily_returns = equity_df["equity"].pct_change().dropna()
        sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(365) if daily_returns.std() > 0 else 0
        max_drawdown = abs((equity_df["equity"] / equity_df["equity"].cummax() - 1).min())
        pnls = [t["net_pnl"] for t in self.trades]
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
        if show_plot:
            self._plot_results(equity_df, stats)
        return stats

    def _plot_results(self, equity_df, stats):
        plt.figure(figsize=(15, 7))
        equity_df["equity"].plot()
        plt.title(
            f"Multi-Timeframe Strategy Backtest\nSharpe: {stats['Sharpe Ratio']:.2f} | Max DD: {stats['Max Drawdown (%)']:.2f}% | Trades: {stats['Total Trades']}"
        )
        plt.ylabel("Portfolio Value ($)"), plt.xlabel("Date"), plt.grid(True), plt.show()


if __name__ == "__main__":

    def load_data(symbol, timeframes):
        data = {}
        for tf in timeframes:
            filename = f"data/{symbol.replace('/', '_')}_{tf}_ohlcv.csv"
            try:
                data[tf] = pd.read_csv(filename, index_col="timestamp", parse_dates=True)
            except FileNotFoundError:
                print(f"ERROR: Missing data file: {filename}. Please run data collector.")
                sys.exit()
        return data

    SYMBOL, TIMEFRAMES = "BTC/USDT", ["1d", "4h", "1h"]
    btc_data = load_data(SYMBOL, TIMEFRAMES)
    backtester = MultiFrameBacktester(symbol=SYMBOL, data=btc_data)
    final_stats = backtester.run_backtest(show_plot=True)

    print("\n--- Backtest Finished ---")
    print("--- Performance Report ---")
    if "error" not in final_stats:
        for key, value in final_stats.items():
            print(f"{key:<20}: {value:.2f}")
