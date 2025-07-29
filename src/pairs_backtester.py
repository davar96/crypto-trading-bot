# src/pairs_backtester.py

import pandas as pd
import numpy as np
import sys
import os
from statsmodels.tsa.stattools import coint
from tqdm import tqdm

# --- Strategy & Backtest Configuration ---

# -- Core Parameters --
SYMBOL_A = "ETH/USDT"
SYMBOL_B = "BTC/USDT"
START_YEAR = 2021

# -- Strategy Parameters --
COINT_WINDOW = 250 * 24  # Rolling window for cointegration test (hours)
ZSCORE_LOOKBACK = 50  # Lookback for calculating the z-score
ENTRY_ZSCORE = 2.0  # Z-score threshold to open a position
EXIT_ZSCORE = 0.0  # Z-score threshold to close a position
STOP_LOSS_ZSCORE = 3.5  # Z-score threshold for stop-loss

# -- Portfolio & Risk Parameters --
INITIAL_CAPITAL = 10000.0
TRADE_VALUE = 1000.0  # Value of each leg of the pair trade in USDT
TRANSACTION_FEE = 0.001  # 0.1% fee per trade
SLIPPAGE = 0.0005  # 0.05% slippage per trade


def run_pairs_backtest(symbol_a, symbol_b, start_year):
    print("--- Starting Pairs Trading Backtest ---")
    print(f"Pair: {symbol_a} vs {symbol_b}")
    print(f"Data Period: {start_year} to Present")

    # --- 1. Load and Prepare Data ---
    print("\n--- Loading and Preparing Data ---")
    try:
        df_a = pd.read_csv(f'data/{symbol_a.replace("/", "_")}_1h.csv', index_col="timestamp", parse_dates=True)
        df_b = pd.read_csv(f'data/{symbol_b.replace("/", "_")}_1h.csv', index_col="timestamp", parse_dates=True)
    except FileNotFoundError as e:
        print(f"Error: {e}. Run collect_data.py for both symbols from {start_year} first.")
        return

    df = pd.concat([df_a["close"], df_b["close"]], axis=1, keys=[symbol_a, symbol_b])
    df.dropna(inplace=True)

    # Filter data from the specified start year
    df = df[df.index.year >= start_year]

    # --- 2. Pre-calculate Strategy Indicators (Vectorized) ---
    print("--- Pre-calculating Indicators (Cointegration, Z-Score)... ---")

    # Rolling Cointegration (this is the slowest part)
    p_values = pd.Series(index=df.index, dtype=float)
    for i in tqdm(range(COINT_WINDOW, len(df)), desc="Calculating Rolling Cointegration"):
        window = df.iloc[i - COINT_WINDOW : i]
        _, p_value, _ = coint(window[symbol_a], window[symbol_b])
        p_values.iloc[i] = p_value
    df["p_value"] = p_values
    df["is_tradeable"] = df["p_value"] < 0.05

    # Z-Score Calculation
    df["ratio"] = df[symbol_a] / df[symbol_b]
    df["moving_average"] = df["ratio"].rolling(window=ZSCORE_LOOKBACK).mean()
    df["std_dev"] = df["ratio"].rolling(window=ZSCORE_LOOKBACK).std()
    df["z_score"] = (df["ratio"] - df["moving_average"]) / df["std_dev"]

    # Drop initial rows with NaN values from rolling calculations
    df.dropna(inplace=True)

    # --- 3. Simulation Setup ---
    print("\n--- Running Simulation ---")
    cash = INITIAL_CAPITAL
    position = None  # Can be 'LONG' (long A, short B) or 'SHORT' (short A, long B)
    trades = []
    equity = pd.Series(index=df.index, dtype=float).fillna(INITIAL_CAPITAL)

    # --- 4. Main Simulation Loop ---
    for i, row in tqdm(df.iterrows(), total=len(df), desc="Simulating Trades"):
        # Copy previous equity value
        equity.loc[i] = equity.iloc[equity.index.get_loc(i) - 1] if equity.index.get_loc(i) > 0 else INITIAL_CAPITAL

        # --- Position Management (Exits) ---
        if position:
            pnl = 0
            # Check for stop-loss
            if (position == "LONG" and row["z_score"] < -STOP_LOSS_ZSCORE) or (
                position == "SHORT" and row["z_score"] > STOP_LOSS_ZSCORE
            ):
                pnl = close_position(position, row, open_trade)
                print_trade(i, "STOP LOSS", pnl, cash + pnl)
                cash += pnl
                trades.append(pnl)
                position = None

            # Check for exit signal (reversion to mean)
            elif (position == "LONG" and row["z_score"] >= EXIT_ZSCORE) or (
                position == "SHORT" and row["z_score"] <= EXIT_ZSCORE
            ):
                pnl = close_position(position, row, open_trade)
                print_trade(i, "TAKE PROFIT", pnl, cash + pnl)
                cash += pnl
                trades.append(pnl)
                position = None

        # --- Entry Logic ---
        if not position and row["is_tradeable"]:
            # Signal to go LONG the pair (Buy A, Sell B)
            if row["z_score"] < -ENTRY_ZSCORE:
                position = "LONG"
                open_trade = open_position("LONG", row)
                print_trade(i, "ENTER LONG", 0, cash)

            # Signal to go SHORT the pair (Sell A, Buy B)
            elif row["z_score"] > ENTRY_ZSCORE:
                position = "SHORT"
                open_trade = open_position("SHORT", row)
                print_trade(i, "ENTER SHORT", 0, cash)

        # Update equity with PnL from this step
        if position:
            current_pnl = calculate_unrealized_pnl(position, row, open_trade)
            equity.loc[i] = cash + current_pnl
        else:
            equity.loc[i] = cash

    # --- Helper functions for PnL calculation with costs ---
    def open_position(pos_type, row):
        price_a = row[symbol_a] * (1 + SLIPPAGE) if pos_type == "LONG" else row[symbol_a] * (1 - SLIPPAGE)
        price_b = row[symbol_b] * (1 - SLIPPAGE) if pos_type == "LONG" else row[symbol_b] * (1 + SLIPPAGE)

        size_a = TRADE_VALUE / price_a
        size_b = TRADE_VALUE / price_b

        cost_a = size_a * price_a * (1 + TRANSACTION_FEE)
        cost_b = size_b * price_b * (1 + TRANSACTION_FEE)

        return {
            "price_a": price_a,
            "price_b": price_b,
            "size_a": size_a,
            "size_b": size_b,
            "initial_value": (cost_a - cost_b) if pos_type == "LONG" else (cost_b - cost_a),
        }

    def close_position(pos_type, row, trade_info):
        # Opposite slippage on close
        price_a = row[symbol_a] * (1 - SLIPPAGE) if pos_type == "LONG" else row[symbol_a] * (1 + SLIPPAGE)
        price_b = row[symbol_b] * (1 + SLIPPAGE) if pos_type == "LONG" else row[symbol_b] * (1 - SLIPPAGE)

        value_a = trade_info["size_a"] * price_a * (1 - TRANSACTION_FEE)
        value_b = trade_info["size_b"] * price_b * (1 - TRANSACTION_FEE)

        if pos_type == "LONG":  # Bought A, Sold B
            pnl_a = value_a - (trade_info["size_a"] * trade_info["price_a"])
            pnl_b = (trade_info["size_b"] * trade_info["price_b"]) - value_b  # Profit from shorting
        else:  # Sold A, Bought B
            pnl_a = (trade_info["size_a"] * trade_info["price_a"]) - value_a
            pnl_b = value_b - (trade_info["size_b"] * trade_info["price_b"])

        return pnl_a + pnl_b

    def calculate_unrealized_pnl(pos_type, row, trade_info):
        price_a = row[symbol_a]
        price_b = row[symbol_b]

        current_value_a = trade_info["size_a"] * price_a
        current_value_b = trade_info["size_b"] * price_b

        initial_value_a = trade_info["size_a"] * trade_info["price_a"]
        initial_value_b = trade_info["size_b"] * trade_info["price_b"]

        if pos_type == "LONG":
            pnl_a = current_value_a - initial_value_a
            pnl_b = initial_value_b - current_value_b
        else:
            pnl_a = initial_value_a - current_value_a
            pnl_b = current_value_b - initial_value_b

        return pnl_a + pnl_b

    def print_trade(timestamp, event, pnl, current_cash):
        print(f"{timestamp.strftime('%Y-%m-%d %H:%M')} | {event:<12} | PnL: ${pnl:7.2f} | Cash: ${current_cash:10.2f}")

    # --- 5. Performance Analysis ---
    print("\n--- Pairs Trading Backtest Finished ---")
    if not trades:
        print("No trades were executed.")
        return

    trades = pd.Series(trades)

    # Calculate Metrics
    net_profit = trades.sum()
    total_return = (net_profit / INITIAL_CAPITAL) * 100
    wins = trades[trades > 0]
    losses = trades[trades <= 0]
    win_rate = (len(wins) / len(trades)) * 100 if trades.any() else 0
    profit_factor = wins.sum() / abs(losses.sum()) if losses.any() else float("inf")

    daily_returns = equity.resample("D").last().pct_change().dropna()
    sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(365) if daily_returns.std() > 0 else 0

    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max
    max_drawdown = abs(drawdown.min()) * 100

    # Print Report
    print("\n--- Performance Report ---")
    print(f"Total Net Profit: ${net_profit:,.2f} ({total_return:.2f}%)")
    print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
    print(f"Max Drawdown: {max_drawdown:.2f}%")
    print(f"Profit Factor: {profit_factor:.2f}")
    print(f"Total Trades: {len(trades)}")
    print(f"Win Rate: {win_rate:.2f}%")

    # Plot Equity Curve
    plt.figure(figsize=(15, 7))
    equity.plot()
    plt.title(f"{symbol_a}/{symbol_b} Pairs Trading Equity Curve")
    plt.xlabel("Date")
    plt.ylabel("Portfolio Value ($)")
    plt.grid(True)
    plot_filename = f"research_results/{symbol_a.replace('/', '_')}_{symbol_b.replace('/', '_')}_equity_curve.png"
    plt.savefig(plot_filename)
    plt.show()


if __name__ == "__main__":
    sym_a = sys.argv[1] if len(sys.argv) > 1 else SYMBOL_A
    sym_b = sys.argv[2] if len(sys.argv) > 2 else SYMBOL_B
    s_year = int(sys.argv[3]) if len(sys.argv) > 3 else START_YEAR

    run_pairs_backtest(sym_a, sym_b, s_year)
