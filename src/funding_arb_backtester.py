# src/funding_arb_backtester.py (Version 2.4 - Library Version)

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os


def run_funding_arb_backtest(
    symbol,
    start_year,
    initial_capital=10000.0,
    entry_apr_threshold=10.0,
    exit_apr_threshold=5.0,
    leverage=1.0,
    min_holding_periods=3,
    regime_filter_periods=3,
    show_plot=True,
    verbose=True,
):
    """
    Runs a backtest for the Funding Rate Arbitrage strategy.
    This version is designed to be called as a function and returns its results.
    """
    if verbose:
        print(
            f"--- Running Backtest: entry={entry_apr_threshold}, exit={exit_apr_threshold}, filter={regime_filter_periods} ---"
        )

    # --- Load & Align Data ---
    ohlcv_file = f"data/{symbol.replace('/', '_')}_1h_ohlcv.csv"
    funding_file = f"data/{symbol.replace('/', '_')}_funding_rates.csv"
    try:
        df_ohlcv = pd.read_csv(ohlcv_file, index_col="timestamp", parse_dates=True)
        df_funding = pd.read_csv(funding_file, index_col="timestamp", parse_dates=True)
    except FileNotFoundError as e:
        return {"error": str(e)}

    df_ohlcv_8h = df_ohlcv["close"].resample("8H").last().ffill()
    df = pd.concat([df_ohlcv_8h, df_funding], axis=1).dropna()
    df = df[df.index.year >= start_year]
    df["apr"] = (df["fundingRate"] * 3 * 365) * 100
    df["rolling_apr_avg"] = df["apr"].rolling(window=regime_filter_periods).mean()
    df.dropna(inplace=True)

    # --- Simulation ---
    equity = initial_capital
    equity_curve = []
    trades = []
    in_position = False
    position_notional_value = 0.0
    trade_age = 0

    ROUND_TRIP_FEES = 0.001 * 4
    ROUND_TRIP_SLIPPAGE = 0.0005 * 2

    for i, row in df.iterrows():
        if in_position:
            trade_age += 1
            funding_pnl = position_notional_value * row["fundingRate"]
            equity += funding_pnl
        equity_curve.append({"timestamp": i, "equity": equity})

        if in_position and row["apr"] < exit_apr_threshold and trade_age >= min_holding_periods:
            exit_cost = position_notional_value * (ROUND_TRIP_FEES / 2 + ROUND_TRIP_SLIPPAGE / 2)
            equity -= exit_cost
            trade_pnl = equity - trades[-1]["entry_equity"]
            trades[-1].update({"exit_date": i, "pnl": trade_pnl})
            in_position, position_notional_value, trade_age = False, 0.0, 0

        if not in_position and row["apr"] > entry_apr_threshold and row["rolling_apr_avg"] > entry_apr_threshold:
            position_notional_value = equity * leverage
            entry_cost = position_notional_value * (ROUND_TRIP_FEES / 2 + ROUND_TRIP_SLIPPAGE / 2)
            equity -= entry_cost
            trades.append({"entry_date": i, "entry_equity": equity})
            in_position, trade_age = True, 0

    # --- Performance Reporting ---
    if not trades:
        return {"Net Profit": 0, "Total Return (%)": 0, "Sharpe Ratio": 0, "Max Drawdown (%)": 0, "Total Trades": 0}

    equity_df = pd.DataFrame(equity_curve).set_index("timestamp")

    net_profit = equity_df["equity"].iloc[-1] - initial_capital
    total_return = (net_profit / initial_capital) * 100
    daily_returns = equity_df["equity"].resample("D").last().pct_change().dropna()
    sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(365) if daily_returns.std() > 0 else 0
    running_max = equity_df["equity"].cummax()
    drawdown = (equity_df["equity"] - running_max) / running_max
    max_drawdown = abs(drawdown.min()) * 100

    if show_plot:
        plt.figure(figsize=(15, 7))
        equity_df["equity"].plot()
        plt.title(f"{symbol} Funding Rate Arbitrage Equity Curve")
        plt.xlabel("Date")
        plt.ylabel("Portfolio Value ($)")
        plt.grid(True)
        plt.show()

    # Return results as a dictionary
    return {
        "Net Profit": net_profit,
        "Total Return (%)": total_return,
        "Sharpe Ratio": sharpe_ratio,
        "Max Drawdown (%)": max_drawdown,
        "Total Trades": len(trades),
    }


if __name__ == "__main__":
    import warnings

    warnings.filterwarnings("ignore", category=FutureWarning, message=".*'H' is deprecated.*")

    optimal_params = {
        "symbol": "DOGE/USDT",
        "start_year": 2021,
        "entry_apr_threshold": 12.0,
        "exit_apr_threshold": 4.0,
        "regime_filter_periods": 3,
        "show_plot": True,
        "verbose": True,
    }

    results = run_funding_arb_backtest(**optimal_params)

    print("\n--- Final Optimized ETH Backtest Report ---")
    for key, value in results.items():
        print(f"{key}: {value:.2f}")
