# src/research/analyze_pair.py

import pandas as pd
import numpy as np
import sys
import os
from statsmodels.tsa.stattools import coint
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from tqdm import tqdm  # Import the progress bar library

# --- Configuration ---
SYMBOL_A = "ETH/USDT"
SYMBOL_B = "BTC/USDT"
LOOKBACK_PERIOD = 50  # For Z-score calculation
ROLLING_WINDOW = 250 * 24  # Rolling window for cointegration test in hours (approx. 8 months)
P_VALUE_THRESHOLD = 0.05  # Significance level for cointegration


def analyze_pair_relationship(symbol_a, symbol_b):
    print(f"--- Analyzing Cointegration and Relationship for {symbol_a} and {symbol_b} ---")

    # --- 1. Load Data ---
    try:
        df_a = pd.read_csv(f'data/{symbol_a.replace("/", "_")}_1h.csv', index_col="timestamp", parse_dates=True)
        df_b = pd.read_csv(f'data/{symbol_b.replace("/", "_")}_1h.csv', index_col="timestamp", parse_dates=True)
    except FileNotFoundError as e:
        print(f"Error: {e}. Please run collect_data.py for both symbols first.")
        return

    # --- 2. Align Data and Calculate Ratio ---
    df = pd.concat([df_a["close"], df_b["close"]], axis=1, keys=[symbol_a, symbol_b])
    df.dropna(inplace=True)
    df["ratio"] = df[symbol_a] / df[symbol_b]

    # --- 3. ROLLING Cointegration Test ---
    print(f"\n--- Performing Rolling Cointegration Test (Window: {int(ROLLING_WINDOW/24)} days) ---")
    p_values = pd.Series(index=df.index, dtype=float)

    # --- WRAP THE LOOP WITH TQDM FOR A PROGRESS BAR ---
    for i in tqdm(range(ROLLING_WINDOW, len(df)), desc="Running Rolling Cointegration"):
        window = df.iloc[i - ROLLING_WINDOW : i]
        series_a = window[symbol_a]
        series_b = window[symbol_b]

        if len(series_a.unique()) < 2 or len(series_b.unique()) < 2:
            continue

        _, p_value, _ = coint(series_a, series_b)
        p_values.iloc[i] = p_value

    df["p_value"] = p_values
    df["is_cointegrated"] = df["p_value"] < P_VALUE_THRESHOLD

    # Analyze the results
    cointegrated_pct = df["is_cointegrated"].mean() * 100
    print(
        f"Result: The pair was cointegrated approximately {cointegrated_pct:.2f}% of the time during the analysis period."
    )
    if cointegrated_pct < 50:
        print("WARNING: The relationship appears to be unstable for long periods.")
    else:
        print("INFO: The relationship shows periods of stability, which may be tradeable.")

    # --- 4. Calculate Z-Score (for visualization) ---
    df["moving_average"] = df["ratio"].rolling(window=LOOKBACK_PERIOD).mean()
    df["std_dev"] = df["ratio"].rolling(window=LOOKBACK_PERIOD).std()
    df["z_score"] = (df["ratio"] - df["moving_average"]) / df["std_dev"]
    df.dropna(inplace=True)

    # --- 5. Visualization ---
    print("\n--- Generating plots... ---")

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(18, 12), sharex=True, gridspec_kw={"height_ratios": [2, 1, 1]})

    ax1.set_title(f"{symbol_a} / {symbol_b} Price Ratio with Cointegrated Regimes")
    df["ratio"].plot(ax=ax1, label="Price Ratio", color="black", linewidth=0.75)
    ax1.grid(True)

    ax1.fill_between(
        df.index,
        ax1.get_ylim()[0],
        ax1.get_ylim()[1],
        where=df["is_cointegrated"],
        facecolor="green",
        alpha=0.15,
        label="Cointegrated Regime (p < 0.05)",
    )
    ax1.legend()

    ax2.set_title("Z-Score of the Price Ratio")
    df["z_score"].plot(ax=ax2, label="Z-Score")
    ax2.axhline(2.0, color="red", linestyle=":", label="+2.0 Threshold")
    ax2.axhline(-2.0, color="green", linestyle=":", label="-2.0 Threshold")
    ax2.axhline(0.0, color="black", linestyle="--")
    ax2.legend()
    ax2.grid(True)

    ax3.set_title("Rolling Cointegration Test P-Value")
    df["p_value"].plot(ax=ax3, label="P-Value", color="purple")
    ax3.axhline(P_VALUE_THRESHOLD, color="red", linestyle="--", label=f"{P_VALUE_THRESHOLD} Significance Threshold")
    ax3.set_ylim(0, 1)
    ax3.legend()
    ax3.grid(True)

    ax3.xaxis.set_major_locator(mdates.YearLocator())
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    plt.tight_layout()
    plot_filename = f"research_results/{symbol_a.replace('/', '_')}_{symbol_b.replace('/', '_')}_rolling_analysis.png"
    if not os.path.exists("research_results"):
        os.makedirs("research_results")
    plt.savefig(plot_filename)
    print(f"Plots saved to {plot_filename}")
    plt.show()


if __name__ == "__main__":
    sym_a = sys.argv[1] if len(sys.argv) > 1 else SYMBOL_A
    sym_b = sys.argv[2] if len(sys.argv) > 2 else SYMBOL_B
    analyze_pair_relationship(sym_a, sym_b)
