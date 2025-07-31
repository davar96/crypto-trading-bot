# src/research/pair_screener.py (Version 1.3 - With Inner Progress Bar)

import pandas as pd
import numpy as np
import sys
import os
import itertools
from statsmodels.tsa.stattools import coint
from tqdm import tqdm
import warnings

# --- Configuration ---
SYMBOL_UNIVERSE = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "AVAX/USDT",
    "MATIC/USDT",
    "LINK/USDT",
    "BNB/USDT",
    "ADA/USDT",
]

START_YEAR = 2021
COINT_WINDOW = 250 * 24
P_VALUE_THRESHOLD = 0.05
RESULTS_FILE = "research_results/screener_report.csv"

# Ignore warnings from statsmodels
warnings.filterwarnings("ignore")


def load_data_for_symbol(symbol, start_year):
    """Loads historical price data for a single symbol."""
    file_path = f'data/{symbol.replace("/", "_")}_1h.csv'
    try:
        df = pd.read_csv(file_path, index_col="timestamp", parse_dates=True)
        df = df[df.index.year >= start_year]
        return df["close"]
    except FileNotFoundError:
        print(f"Warning: Data file not found for {symbol}. Skipping.")
        return None


def run_screener():
    print("--- Starting Cointegration Pair Screener (V1.3 - With Inner Progress Bar) ---")
    print(f"Analyzing {len(SYMBOL_UNIVERSE)} symbols...")

    processed_pairs = set()
    if os.path.exists(RESULTS_FILE):
        print(f"--- Found existing report at {RESULTS_FILE}. Resuming... ---")
        results_df = pd.read_csv(RESULTS_FILE)
        for pair_str in results_df["Pair"]:
            processed_pairs.add(tuple(sorted(pair_str.split(" / "))))
    else:
        results_df = pd.DataFrame(columns=["Pair", "Cointegration %"])

    all_data = {symbol: load_data_for_symbol(symbol, START_YEAR) for symbol in SYMBOL_UNIVERSE}
    all_data = {k: v for k, v in all_data.items() if v is not None}

    all_pairs = list(itertools.combinations(all_data.keys(), 2))

    pairs_to_test = [p for p in all_pairs if tuple(sorted(p)) not in processed_pairs]
    if not pairs_to_test:
        print("--- All pairs have already been processed. Displaying final report. ---")
    else:
        print(f"Generated {len(all_pairs)} unique pairs. {len(pairs_to_test)} pairs remaining to test.")

    for symbol_a, symbol_b in tqdm(pairs_to_test, desc="Overall Progress"):
        pair_data = pd.concat([all_data[symbol_a], all_data[symbol_b]], axis=1).dropna()

        if len(pair_data) < COINT_WINDOW:
            print(f"Skipping {symbol_a}/{symbol_b} due to insufficient common data.")
            continue

        p_values = pd.Series(index=pair_data.index, dtype=float)

        # --- UX IMPROVEMENT: Add a nested progress bar for the slow inner loop ---
        # The `leave=False` argument makes the bar disappear after it's done, keeping the output clean.
        inner_loop_desc = f"Processing {symbol_a}/{symbol_b}"
        inner_loop = tqdm(range(COINT_WINDOW, len(pair_data)), desc=inner_loop_desc, leave=False)

        for i in inner_loop:
            window = pair_data.iloc[i - COINT_WINDOW : i]

            if window.iloc[:, 0].nunique() < 2 or window.iloc[:, 1].nunique() < 2:
                continue

            _, p_value, _ = coint(window.iloc[:, 0], window.iloc[:, 1])
            p_values.iloc[i] = p_value

        is_cointegrated = p_values < P_VALUE_THRESHOLD
        cointegrated_pct = is_cointegrated.mean() * 100

        new_row = pd.DataFrame([{"Pair": f"{symbol_a} / {symbol_b}", "Cointegration %": cointegrated_pct}])
        results_df = pd.concat([results_df, new_row], ignore_index=True)
        results_df.to_csv(RESULTS_FILE, index=False)

    results_df = results_df.sort_values(by="Cointegration %", ascending=False).reset_index(drop=True)

    print("\n\n--- Cointegration Screening Report ---")
    print(
        f"Analysis Period: {START_YEAR}-Present | Cointegration Window: {int(COINT_WINDOW/24)} days | P-Value < {P_VALUE_THRESHOLD}"
    )
    print(results_df.to_string())
    print(f"\nReport saved to {RESULTS_FILE}")


if __name__ == "__main__":
    if not os.path.exists("research_results"):
        os.makedirs("research_results")
    run_screener()
