# src/pairs_backtester.py

import pandas as pd
import numpy as np
import sys
import os
from statsmodels.tsa.stattools import coint
from tqdm import tqdm
import matplotlib.pyplot as plt

# --- Configuration ---
# --- CHANGE: Symbols are now passed as arguments, removed hardcoded symbols ---
START_YEAR = 2021
# -- Strategy Parameters --
COINT_WINDOW = 60 * 24
ZSCORE_LOOKBACK = 50
BETA_WINDOW = 100
ENTRY_ZSCORE = 2.0
EXIT_ZSCORE = 0.0
STOP_LOSS_ZSCORE = 4.0
# -- Professional Risk Management Parameters --
RISK_PER_TRADE_PCT = 0.01  # Risk 1% of current equity per trade
TIME_STOP_LOOKBACK = 250 * 24
MAX_HOLDING_PERIOD_MULTIPLIER = 2.0

# -- Portfolio & Cost Parameters --
INITIAL_CAPITAL = 10000.0
TRANSACTION_FEE = 0.001
SLIPPAGE = 0.0005


def calculate_half_life(series):
    """Calculates the half-life of mean reversion for a time series."""
    lagged = series.shift(1).fillna(0)
    delta = series - lagged
    delta.dropna(inplace=True)
    lagged = lagged.loc[delta.index]

    X = lagged.values.reshape(-1, 1)
    Y = delta.values

    if len(X) == 0:
        return np.inf

    try:
        model = np.linalg.lstsq(X, Y, rcond=None)
        lambda_ = model[0][0]
    except np.linalg.LinAlgError:
        return np.inf

    if lambda_ >= 0:
        return np.inf
    return -np.log(2) / lambda_


# --- CHANGE: Function now accepts symbol_a and symbol_b as arguments ---
def run_pairs_backtest(symbol_a, symbol_b, start_year):
    print(f"--- Starting Professional Pairs Trading Backtest for {symbol_a} / {symbol_b} ---")

    # --- CHANGE: Cache file name is now dynamic ---
    cache_file = f"data/precalculated_pro_{symbol_a.replace('/', '_')}_{symbol_b.replace('/', '_')}_{start_year}.pkl"
    if os.path.exists(cache_file):
        print("\n--- Loading Pre-calculated Data from Cache ---")
        df = pd.read_pickle(cache_file)
    else:
        print("\n--- Loading Data & Pre-calculating Indicators ---")
        try:
            # --- CHANGE: Data is loaded using dynamic symbol names ---
            df_a = pd.read_csv(f'data/{symbol_a.replace("/", "_")}_1h.csv', index_col="timestamp", parse_dates=True)
            df_b = pd.read_csv(f'data/{symbol_b.replace("/", "_")}_1h.csv', index_col="timestamp", parse_dates=True)
        except FileNotFoundError as e:
            print(f"Error: {e}. Please run collect_data.py for both symbols from {start_year} first.")
            return

        df = pd.concat([df_a["close"], df_b["close"]], axis=1, keys=[symbol_a, symbol_b]).dropna()
        df = df[df.index.year >= start_year]

        p_values = pd.Series(index=df.index, dtype=float)
        for i in tqdm(range(COINT_WINDOW, len(df)), desc="Calculating Rolling Cointegration"):
            window = df.iloc[i - COINT_WINDOW : i]
            _, p_value, _ = coint(window[symbol_a], window[symbol_b])
            p_values.iloc[i] = p_value
        df["p_value"] = p_values
        df["is_tradeable"] = df["p_value"] < 0.05

        returns_a = df[symbol_a].pct_change()
        returns_b = df[symbol_b].pct_change()
        df["beta"] = returns_a.rolling(window=BETA_WINDOW).cov(returns_b) / returns_b.rolling(window=BETA_WINDOW).var()
        df["spread"] = df[symbol_a] - df["beta"] * df[symbol_b]

        df["spread_mean"] = df["spread"].ewm(span=ZSCORE_LOOKBACK).mean()
        df["spread_std"] = df["spread"].ewm(span=ZSCORE_LOOKBACK).std()
        df["z_score"] = (df["spread"] - df["spread_mean"]) / df["spread_std"]

        half_lives = pd.Series(index=df.index, dtype=float)
        for i in tqdm(range(TIME_STOP_LOOKBACK, len(df)), desc="Calculating Rolling Half-Life"):
            window = df["spread"].iloc[i - TIME_STOP_LOOKBACK : i]
            half_lives.iloc[i] = calculate_half_life(window)
        df["half_life"] = half_lives

        df.dropna(inplace=True)
        df.to_pickle(cache_file)
        print(f"--- Pre-calculated data saved to {cache_file} ---")

    print("\n--- Running Simulation ---")

    cash = INITIAL_CAPITAL
    holdings_a = 0.0
    holdings_b = 0.0
    position = None
    open_trade_details = {}

    trades = []
    equity_curve = []

    for i, row in tqdm(df.iterrows(), total=len(df), desc="Simulating Trades"):
        current_equity = cash + (holdings_a * row[symbol_a]) + (holdings_b * row[symbol_b])
        equity_curve.append(current_equity)

        if position:
            open_trade_details["age"] += 1
            exit_signal, reason = False, ""

            if (position == "LONG" and row["z_score"] <= -STOP_LOSS_ZSCORE) or (
                position == "SHORT" and row["z_score"] >= STOP_LOSS_ZSCORE
            ):
                exit_signal, reason = True, "STOP LOSS"
            elif open_trade_details["age"] > open_trade_details["time_limit"]:
                exit_signal, reason = True, "TIME STOP"
            elif (position == "LONG" and row["z_score"] >= EXIT_ZSCORE) or (
                position == "SHORT" and row["z_score"] <= EXIT_ZSCORE
            ):
                exit_signal, reason = True, "TAKE PROFIT"

            if exit_signal:
                pnl = current_equity - open_trade_details["entry_equity"]

                if position == "LONG":
                    cash += holdings_a * row[symbol_a] * (1 - SLIPPAGE) * (1 - TRANSACTION_FEE)
                    cash -= abs(holdings_b) * row[symbol_b] * (1 + SLIPPAGE) * (1 + TRANSACTION_FEE)
                else:
                    cash -= abs(holdings_a) * row[symbol_a] * (1 + SLIPPAGE) * (1 + TRANSACTION_FEE)
                    cash += holdings_b * row[symbol_b] * (1 - SLIPPAGE) * (1 - TRANSACTION_FEE)

                trades.append({"pnl": pnl, "reason": reason})
                position, holdings_a, holdings_b = None, 0.0, 0.0

        if not position and row["is_tradeable"]:
            enter_long = row["z_score"] <= -ENTRY_ZSCORE
            enter_short = row["z_score"] >= ENTRY_ZSCORE

            if enter_long or enter_short:
                dollar_risk = current_equity * RISK_PER_TRADE_PCT
                stop_loss_spread = (
                    row["spread_mean"] - (row["spread_std"] * STOP_LOSS_ZSCORE)
                    if enter_long
                    else row["spread_mean"] + (row["spread_std"] * STOP_LOSS_ZSCORE)
                )
                risk_per_unit = abs(row["spread"] - stop_loss_spread)

                if risk_per_unit > 0:
                    size_b = dollar_risk / risk_per_unit
                    size_a = size_b * row["beta"]
                    value_a, value_b = size_a * row[symbol_a], size_b * row[symbol_b]
                    total_value = value_a + value_b

                    if current_equity > total_value:
                        position = "LONG" if enter_long else "SHORT"
                        if position == "LONG":
                            holdings_a = size_a
                            holdings_b = -size_b
                        else:
                            holdings_a = -size_a
                            holdings_b = size_b

                        cash_change_a = holdings_a * row[symbol_a] * (1 + (np.sign(holdings_a) * SLIPPAGE))
                        cash_change_b = holdings_b * row[symbol_b] * (1 + (np.sign(holdings_b) * SLIPPAGE))
                        fees = (abs(cash_change_a) + abs(cash_change_b)) * TRANSACTION_FEE
                        cash -= cash_change_a + cash_change_b + fees

                        open_trade_details = {
                            "entry_equity": current_equity,
                            "age": 0,
                            "time_limit": (
                                row["half_life"] * MAX_HOLDING_PERIOD_MULTIPLIER
                                if np.isfinite(row["half_life"])
                                else 1000
                            ),
                        }

    print(f"\n--- Backtest Finished for {symbol_a}/{symbol_b} ---")
    if not trades:
        print("No trades were executed.")
        return

    trades_df = pd.DataFrame(trades)
    equity = pd.Series(equity_curve, index=df.index)

    net_profit = trades_df["pnl"].sum()
    total_return = (net_profit / INITIAL_CAPITAL) * 100
    wins = trades_df[trades_df["pnl"] > 0]
    losses = trades_df[trades_df["pnl"] <= 0]
    win_rate = (len(wins) / len(trades_df)) * 100 if not trades_df.empty else 0
    profit_factor = (
        wins["pnl"].sum() / abs(losses["pnl"].sum()) if not losses.empty and losses["pnl"].sum() != 0 else float("inf")
    )
    daily_returns = equity.resample("D").last().pct_change().dropna()
    sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(365) if daily_returns.std() > 0 else 0
    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max
    max_drawdown = abs(drawdown.min()) * 100

    print("\n--- Performance Report ---")
    print(f"Pair: {symbol_a} / {symbol_b}")
    print(f"Total Net Profit: ${net_profit:,.2f} ({total_return:.2f}%)")
    print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
    print(f"Max Drawdown: {max_drawdown:.2f}%")
    print(f"Profit Factor: {profit_factor:.2f}")
    print(f"Total Trades: {len(trades_df)}")
    print(f"Win Rate: {win_rate:.2f}%")

    plt.figure(figsize=(15, 7))
    equity.plot()
    # --- CHANGE: Plot title is now dynamic ---
    plt.title(f"{symbol_a}/{symbol_b} Professional Pairs Trading Equity Curve")
    plt.xlabel("Date")
    plt.ylabel("Portfolio Value ($)")
    plt.grid(True)
    # --- CHANGE: Plot filename is now dynamic ---
    plot_filename = f"research_results/{symbol_a.replace('/', '_')}_{symbol_b.replace('/', '_')}_pro_equity_curve.png"
    plt.savefig(plot_filename)
    # --- CHANGE: We can hide the plot popup for batch processing ---
    # plt.show()
    plt.close()  # Close the plot to prevent it from displaying in a loop
    print(f"Equity curve saved to {plot_filename}")


if __name__ == "__main__":
    # --- CHANGE: Read symbols from command-line arguments ---
    if len(sys.argv) != 3:
        print("Usage: python src/pairs_backtester.py <SYMBOL_A> <SYMBOL_B>")
        print("Example: python src/pairs_backtester.py ETH/USDT BTC/USDT")
        sys.exit(1)

    symbol_a_arg = sys.argv[1]
    symbol_b_arg = sys.argv[2]

    # Run the backtest
    run_pairs_backtest(symbol_a_arg, symbol_b_arg, START_YEAR)
