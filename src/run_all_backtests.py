# src/run_all_backtests.py

import os
import subprocess
import sys  # Import sys to get the current python executable
import time

# This is the list of symbols you want to backtest
SYMBOLS_TO_TEST = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "BNB/USDT",
    "BCH/USDT",
    "DOT/USDT",
    "ADA/USDT",
    "NEAR/USDT",
    "AVAX/USDT",
    "LINK/USDT",
    "XRP/USDT",
    "DOGE/USDT",
    "LTC/USDT",
    "ATOM/USDT",
    "FTM/USDT",
    "RUNE/USDT",
    "UNI/USDT",
    "AAVE/USDT",
]

if __name__ == "__main__":
    start_time = time.time()
    print("--- Starting Batch Backtest Process ---")
    print(f"Will test {len(SYMBOLS_TO_TEST)} symbols...")

    # --- THE FIX: Get the path to the python executable in the current venv ---
    python_executable = sys.executable
    print(f"Using Python executable: {python_executable}")
    # --- END OF FIX ---

    # First, collect data for all symbols
    print("\n--- Phase 1: Collecting all historical data ---")
    for symbol in SYMBOLS_TO_TEST:
        print(f"\n--- Collecting data for {symbol} ---")
        # Use the specific python executable from our venv
        subprocess.run([python_executable, "src/collect_data.py", symbol, "2021"])

    # Then, run a backtest for each symbol
    print("\n--- Phase 2: Running backtests for all symbols ---")
    for symbol in SYMBOLS_TO_TEST:
        print(f"\n--- Running backtest for {symbol} ---")
        # Use the specific python executable from our venv
        subprocess.run([python_executable, "src/backtest.py", symbol])

    end_time = time.time()
    total_time = end_time - start_time
    print("\n--- Batch Backtest Process Finished ---")
    print(f"Total time taken: {total_time / 60:.2f} minutes")
