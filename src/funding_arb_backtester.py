# src/funding_arb_backtester.py (Version 2.8 - With Kill Switch)

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import sys

# The '.' tells Python to look for strategy.py inside the same package (src).
from .strategy import FundingArbStrategy


def run_funding_arb_backtest(
    symbol,
    start_year,
    optimal_params,
    initial_capital=100.0,
    leverage=1.0,
    show_plot=True,
    verbose=True,
):
    """
    Runs a backtest for the Funding Rate Arbitrage strategy.
    V2.8 includes a critical "Kill Switch" to exit on negative funding rates.
    """
    # --- Extract parameters from the strategy object ---
    params = optimal_params.get(symbol)
    if not params:
        return {"error": f"No optimal parameters found for {symbol}"}

    entry_apr_threshold = params["entry_apr"]
    exit_apr_threshold = params["exit_apr"]
    regime_filter_periods = params["filter_periods"]

    if verbose:
        print(f"\n--- Running Backtest for {symbol} (Since {start_year}) ---")
        print(
            f"Params: entry_apr={entry_apr_threshold}%, exit_apr={exit_apr_threshold}%, filter_periods={regime_filter_periods}"
        )

    # --- Load & Align Data ---
    try:
        ohlcv_file = f"data/{symbol.replace('/', '_')}_1h_ohlcv.csv"
        funding_file = f"data/{symbol.replace('/', '_')}_funding_rates.csv"
        df_ohlcv = pd.read_csv(ohlcv_file, index_col="timestamp", parse_dates=True)
        df_funding = pd.read_csv(funding_file, index_col="timestamp", parse_dates=True)
    except FileNotFoundError as e:
        print(f"ERROR: Missing data file: {e}")
        return {"error": str(e)}

    df_ohlcv_8h = df_ohlcv["close"].resample("8H").last().ffill()
    df = pd.concat([df_ohlcv_8h, df_funding], axis=1).dropna()
    df = df[df.index.year >= start_year]
    df["apr"] = (df["fundingRate"] * 3 * 365) * 100
    df["rolling_apr_avg"] = df["apr"].rolling(window=regime_filter_periods).mean()
    df.dropna(inplace=True)

    # --- Configuration for PnL Calculation ---
    ROUND_TRIP_FEES = 0.001 * 4
    ROUND_TRIP_SLIPPAGE = 0.0005 * 2

    # Use the same sizing logic as the live bot
    if initial_capital < 300:
        capital_to_deploy_pct = 0.6
    elif initial_capital < 1000:
        capital_to_deploy_pct = 0.7
    else:
        capital_to_deploy_pct = 0.8

    # --- Corrected Simulation Loop ---
    equity = initial_capital
    equity_curve = []
    trades = []
    in_position = False
    current_trade = {}

    for i, row in df.iterrows():
        # --- Handle PnL and Exit Conditions for Open Position ---
        if in_position:
            # PnL calculation is correct; it handles negative rates automatically.
            funding_pnl = current_trade["notional_value"] * row["fundingRate"]
            current_trade["gross_pnl"] += funding_pnl
            current_trade["funding_payments_received"] += 1

            # Exit Condition 1: APR fell below the profit-taking threshold (Normal Exit)
            if row["apr"] < exit_apr_threshold:
                costs = current_trade["notional_value"] * (ROUND_TRIP_FEES + ROUND_TRIP_SLIPPAGE)
                net_pnl = current_trade["gross_pnl"] - costs
                equity += net_pnl
                current_trade.update({"exit_date": i, "net_pnl": net_pnl, "exit_reason": "APR fell below threshold"})
                in_position = False
                current_trade = {}

            # --- NEW: MENTOR'S KILL SWITCH ---
            # Exit Condition 2: Funding rate turned negative (Risk Management Exit)
            elif row["fundingRate"] < 0:
                costs = current_trade["notional_value"] * (ROUND_TRIP_FEES + ROUND_TRIP_SLIPPAGE)
                net_pnl = current_trade["gross_pnl"] - costs
                equity += net_pnl
                current_trade.update(
                    {"exit_date": i, "net_pnl": net_pnl, "exit_reason": "Negative funding rate (Kill Switch)"}
                )
                in_position = False
                current_trade = {}
            # --- END OF KILL SWITCH LOGIC ---

        # --- Check for Entry Signal ---
        if not in_position and row["apr"] > entry_apr_threshold and row["rolling_apr_avg"] > entry_apr_threshold:
            notional_value = equity * capital_to_deploy_pct * leverage
            current_trade = {
                "entry_date": i,
                "notional_value": notional_value,
                "gross_pnl": 0.0,
                "funding_payments_received": 0,
            }
            trades.append(current_trade)
            in_position = True

        equity_curve.append({"timestamp": i, "equity": equity})

    # --- Performance Reporting ---
    if not trades:
        print("No trades were executed during this backtest period.")
        return {"Net Profit": 0, "Sharpe Ratio": 0, "Max Drawdown (%)": 0, "Total Trades": 0}

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
        equity_df["equity"].plot(label="Equity Curve")
        plt.title(f"Upgraded Backtest: {symbol} (Sharpe: {sharpe_ratio:.2f})")
        plt.xlabel("Date")
        plt.ylabel("Portfolio Value ($)")
        plt.grid(True)
        plt.legend()
        plt.show()

    return {
        "Net Profit": net_profit,
        "Total Return (%)": total_return,
        "Sharpe Ratio": sharpe_ratio,
        "Max Drawdown (%)": max_drawdown,
        "Total Trades": len(trades),
    }


if __name__ == "__main__":
    import warnings

    warnings.filterwarnings("ignore", category=FutureWarning)

    # --- Updated main block to test the new Kill Switch logic ---
    print("--- Running a single test case with the new Kill Switch backtester ---")

    # Use one of the aggressive parameter sets the optimizer will test
    test_params = {"DOGE/USDT": {"entry_apr": 8, "exit_apr": 3, "filter_periods": 2}}

    results = run_funding_arb_backtest(
        symbol="DOGE/USDT",
        start_year=2022,
        optimal_params=test_params,
        show_plot=True,
        verbose=True,
    )

    print("\n--- Single Run Test Report ---")
    if "error" not in results:
        for key, value in results.items():
            print(f"{key}: {value:.4f}")
    else:
        print(f"Test failed with error: {results['error']}")
