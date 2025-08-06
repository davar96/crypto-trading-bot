import pandas as pd
import itertools
from tqdm import tqdm
import os
import sys

# Correctly import the backtester from its location
from .trend_backtester import TrendBacktester

PARAMETER_GRID = {
    "entry_setup": ["A", "B", "C"],  # The three different strategies to test
    "sma_period": [200],
    "rsi_period": [14],
    "rsi_entry_max": [65, 70, 75],
    "stop_loss_pct": [3, 5, 7],
    "take_profit_pct": [10, 15, 20, 25],
    "position_size_pct": [25, 33],
    "max_positions": [1, 2, 3],
}

# --- Configuration ---
SYMBOL = "BTC/USDT"
DATA_FILE = f"data/{SYMBOL.replace('/', '_')}_1d_ohlcv.csv"
RESULTS_FILE = "research_results/dynamic_optimizer_report.csv"


def run_trend_optimizer(data_df):
    """
    Runs the dynamic TrendBacktester with multiple parameter combinations and entry
    setups to find the optimal overall strategy.
    """
    print("--- Starting DYNAMIC ENGINE Optimizer ---")

    keys, values = zip(*PARAMETER_GRID.items())
    param_combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]

    print(f"Generated {len(param_combinations)} unique parameter combinations to test for {SYMBOL}.")

    all_results = []

    for params in tqdm(param_combinations, desc=f"Optimizing {SYMBOL}"):
        test_name = f"Setup_{params['entry_setup']}_SL{params['stop_loss_pct']}_TP{params['take_profit_pct']}"
        backtester = TrendBacktester(data=data_df, params=params, test_name=test_name)

        results = backtester.run_backtest(show_plot=False)

        if "error" in results:
            continue

        results.update(params)
        all_results.append(results)

    if not all_results:
        print("Optimization run failed to produce results.")
        return

    results_df = pd.DataFrame(all_results)

    num_years = (data_df.index[-1] - data_df.index[0]).days / 365.25
    results_df["Annualized Return (%)"] = results_df["Total Return (%)"] / num_years

    results_df_sorted = results_df.sort_values(by="Sharpe Ratio", ascending=False)

    report_columns = [
        "Sharpe Ratio",
        "Annualized Return (%)",
        "Max Drawdown (%)",
        "Win Rate (%)",
        "Profit Factor",
        "Total Trades",
        "entry_setup",
        "rsi_entry_max",
        "stop_loss_pct",
        "take_profit_pct",
        "position_size_pct",
        "max_positions",
    ]
    results_df_sorted = results_df_sorted[report_columns]

    if not os.path.exists("research_results"):
        os.makedirs("research_results")

    results_df_sorted.to_csv(RESULTS_FILE, index=False)
    print(f"\nFull optimization report saved to {RESULTS_FILE}")

    print("\n--- Top 15 Parameter Combinations by Sharpe Ratio ---")
    print(results_df_sorted.head(15).to_string(index=False))


if __name__ == "__main__":
    try:
        btc_data_df = pd.read_csv(DATA_FILE, index_col="timestamp", parse_dates=True)
    except FileNotFoundError:
        print(f"ERROR: Data file not found at {DATA_FILE}")
        sys.exit()

    run_trend_optimizer(btc_data_df)
