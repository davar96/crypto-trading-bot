# src/research/sanity_checker.py (Version 2.0 - Multi-Scenario Analysis)

import pandas as pd
import os


def run_sanity_check(symbol, year, basis_threshold_bps=50):
    """
    Performs the mentor's quick sanity check with a variable basis threshold.
    """
    print(f"\n--- Running Sanity Check ---")
    print(f"  - Asset: {symbol}")
    print(f"  - Year: {year}")
    print(f"  - Basis Threshold: > {basis_threshold_bps} bps")
    print("----------------------------")

    # --- 1. Define file paths ---
    spot_file = f"data/{symbol.replace('/', '_')}_1h_ohlcv.csv"
    # This handles the filename change from the data collector script
    perp_symbol_for_file = f"{symbol.split('/')[0]}_USDT_USDT"
    perp_file = f"data/{perp_symbol_for_file}_1h_ohlcv.csv"
    funding_file = f"data/{symbol.replace('/', '_')}_funding_rates.csv"

    # --- 2. Load data and handle potential errors ---
    try:
        df_spot = pd.read_csv(spot_file, index_col="timestamp", parse_dates=True)
        df_perp = pd.read_csv(perp_file, index_col="timestamp", parse_dates=True)
        df_funding = pd.read_csv(funding_file, index_col="timestamp", parse_dates=True)
    except FileNotFoundError as e:
        print(f"ERROR: A required data file was not found: {e}")
        return

    # --- 3. Prepare and merge data ---
    df = pd.concat(
        [df_spot["close"].rename("spot_close"), df_perp["close"].rename("perp_close"), df_funding["fundingRate"]],
        axis=1,
    )

    df = df.resample("h").last().ffill().dropna()
    df = df[df.index.year == year]

    if df.empty:
        print(f"No aligned data found for {year}. Cannot perform check.")
        return

    # --- 4. Perform the analysis ---
    df["basis_bps"] = ((df["perp_close"] - df["spot_close"]) / df["spot_close"]) * 10000

    opportunity_hours = df[(df["basis_bps"] > basis_threshold_bps) & (df["fundingRate"] > 0)]

    total_hours_in_year = len(df)
    profitable_hours = len(opportunity_hours)

    # --- 5. Report the findings ---
    print(f"Analysis Complete:")
    print(f"Total Hours Analyzed: {total_hours_in_year}")
    print(f"Profitable Opportunity Hours: {profitable_hours}")

    if total_hours_in_year > 0:
        opportunity_pct = (profitable_hours / total_hours_in_year) * 100
        print(f"Opportunity existed for ~{opportunity_pct:.2f}% of the time.")

    if profitable_hours > 10:
        print("VERDICT: ✅ Viable. The number of opportunity hours is significant.")
    else:
        print("VERDICT: ❌ Caution. Very few opportunity hours found under these specific parameters.")


if __name__ == "__main__":
    # Ensure all required data files for BTC and DOGE since 2022 are present first!
    print("===== Starting Market-Wide Reconnaissance =====")

    # Scenario 1: The original test. Confirms our baseline.
    run_sanity_check(symbol="BTC/USDT", year=2023, basis_threshold_bps=50)

    # Scenario 2: The "Bear Market" check. Was 2023 an anomaly for BTC?
    run_sanity_check(symbol="BTC/USDT", year=2022, basis_threshold_bps=50)

    # Scenario 3: The "Asset Personality" check. Does a less efficient asset show opportunity?
    run_sanity_check(symbol="DOGE/USDT", year=2023, basis_threshold_bps=50)

    # Scenario 4: The "Lowered Bar" check. Is the 50bps threshold too high for BTC?
    run_sanity_check(symbol="BTC/USDT", year=2023, basis_threshold_bps=20)

    print("\n===== Reconnaissance Complete =====")
