# src/research/optimizer.py

import pandas as pd
import itertools
from tqdm import tqdm
import os
import sys

# Add the parent directory to the path to allow importing the backtester
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from funding_arb_backtester import run_funding_arb_backtest

# --- Configuration ---
SYMBOL_TO_OPTIMIZE = "DOGE/USDT"
START_YEAR = 2021
RESULTS_FILE = "research_results/optimizer_report_DOGE.csv"

# --- Parameter Ranges to Test ---
# NOTE: More values will result in a much longer run time.
ENTRY_THRESHOLDS = [8, 10, 12, 15]
EXIT_THRESHOLDS = [3, 4, 5, 6]
REGIME_FILTER_PERIODS = [3, 6, 9, 12]  # Corresponds to 24h, 48h, 72h, 96h


def run_optimizer():
    """
    Runs the funding rate backtester with multiple parameter combinations
    to find the optimal settings.
    """
    print("--- Starting Parameter Optimizer ---")

    # Generate all unique combinations of parameters
    param_combinations = list(itertools.product(ENTRY_THRESHOLDS, EXIT_THRESHOLDS, REGIME_FILTER_PERIODS))

    # Filter out invalid combinations where exit threshold is >= entry threshold
    valid_combinations = [p for p in param_combinations if p[1] < p[0]]

    print(f"Generated {len(valid_combinations)} unique parameter combinations to test.")

    all_results = []

    # Use tqdm for a progress bar
    for params in tqdm(valid_combinations, desc="Optimizing Parameters"):
        entry_apr, exit_apr, filter_periods = params

        # Run the backtest with the current set of parameters
        # show_plot and verbose are False to keep the output clean
        result = run_funding_arb_backtest(
            symbol=SYMBOL_TO_OPTIMIZE,
            start_year=START_YEAR,
            entry_apr_threshold=entry_apr,
            exit_apr_threshold=exit_apr,
            regime_filter_periods=filter_periods,
            show_plot=False,
            verbose=False,
        )

        # Add the parameters to the results dictionary for reporting
        result["Entry APR"] = entry_apr
        result["Exit APR"] = exit_apr
        result["Filter Periods"] = filter_periods

        all_results.append(result)

    # --- Reporting ---
    if not all_results:
        print("Optimization run failed to produce results.")
        return

    results_df = pd.DataFrame(all_results)

    # Sort by Sharpe Ratio (descending) as our primary metric
    results_df_sorted = results_df.sort_values(by="Sharpe Ratio", ascending=False)

    # Create the research_results directory if it doesn't exist
    if not os.path.exists("research_results"):
        os.makedirs("research_results")

    # Save the full report to a CSV file
    results_df_sorted.to_csv(RESULTS_FILE, index=False)
    print(f"\nFull optimization report saved to {RESULTS_FILE}")

    print("\n--- Top 10 Parameter Combinations by Sharpe Ratio ---")
    print(results_df_sorted.head(10).to_string())


if __name__ == "__main__":
    run_optimizer()
