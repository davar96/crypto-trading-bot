# src/research/optimizer.py (Mentor-Directed Aggressive Version)

import pandas as pd
import itertools
from tqdm import tqdm
import os
import sys

# The '..' moves up from the 'research' directory to the 'src' package level,
# then finds the backtester module, which you moved there.
from ..funding_arb_backtester import run_funding_arb_backtest

# --- Configuration ---
# Let's start with DOGE as it had the highest activity in the last test.
SYMBOL_TO_OPTIMIZE = "DOGE/USDT"
START_YEAR = 2022
RESULTS_FILE = f"research_results/optimizer_report_AGGRESSIVE_{SYMBOL_TO_OPTIMIZE.replace('/', '_')}.csv"

# --- MENTOR'S NEW AGGRESSIVE PARAMETER RANGES ---
# The goal is to increase trade frequency and target higher annual returns (15%+)
# and a Sharpe Ratio > 1.2, even if it means accepting a higher drawdown.
ENTRY_THRESHOLDS = [6, 8, 10, 12]
EXIT_THRESHOLDS = [2, 3, 4]
REGIME_FILTER_PERIODS = [1, 2, 3]  # Faster reaction times as per mentor advice.


def run_optimizer():
    """
    Runs the funding rate backtester with multiple parameter combinations
    to find the optimal settings based on the mentor's aggressive targets.
    """
    print("--- Starting MENTOR-DIRECTED AGGRESSIVE Parameter Optimizer ---")
    print(f"Goal: Find params with Sharpe > 1.2 and high trade frequency for {SYMBOL_TO_OPTIMIZE}")

    # Generate all unique combinations of parameters
    param_combinations = list(itertools.product(ENTRY_THRESHOLDS, EXIT_THRESHOLDS, REGIME_FILTER_PERIODS))

    # Filter out invalid combinations where exit threshold is >= entry threshold
    valid_combinations = [p for p in param_combinations if p[1] < p[0]]

    print(f"Generated {len(valid_combinations)} unique parameter combinations to test.")

    all_results = []

    # Use tqdm for a progress bar
    for params in tqdm(valid_combinations, desc=f"Optimizing {SYMBOL_TO_OPTIMIZE}"):
        entry_apr, exit_apr, filter_periods = params

        # Create the parameter dictionary the new backtester expects
        temp_optimal_params = {
            SYMBOL_TO_OPTIMIZE: {
                "entry_apr": entry_apr,
                "exit_apr": exit_apr,
                "filter_periods": filter_periods,
            }
        }

        # Run the backtest with the current set of parameters
        result = run_funding_arb_backtest(
            symbol=SYMBOL_TO_OPTIMIZE,
            start_year=START_YEAR,
            optimal_params=temp_optimal_params,
            show_plot=False,  # We only want the numbers
            verbose=False,
        )

        if "error" in result:
            print(f"Skipping a run due to error: {result['error']}")
            continue

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

    # Calculate Annualized Return for better analysis
    # (Total Return / Number of Years)
    num_years = pd.Timestamp.now().year - START_YEAR + 1
    results_df["Annual Return (%)"] = results_df["Total Return (%)"] / num_years

    # Sort by Sharpe Ratio (descending) as our primary metric
    results_df_sorted = results_df.sort_values(by="Sharpe Ratio", ascending=False)

    # Reorder columns for clarity in the report
    report_columns = [
        "Sharpe Ratio",
        "Annual Return (%)",
        "Max Drawdown (%)",
        "Total Trades",
        "Entry APR",
        "Exit APR",
        "Filter Periods",
        "Net Profit",
        "Total Return (%)",
    ]
    results_df_sorted = results_df_sorted[report_columns]

    # Create the research_results directory if it doesn't exist in the project root
    if not os.path.exists("research_results"):
        os.makedirs("research_results")

    # Save the full report to a CSV file
    results_df_sorted.to_csv(RESULTS_FILE, index=False)
    print(f"\nFull optimization report saved to {RESULTS_FILE}")

    print("\n--- Top 10 Parameter Combinations by Sharpe Ratio ---")
    print(results_df_sorted.head(10).to_string(index=False))


if __name__ == "__main__":
    run_optimizer()
