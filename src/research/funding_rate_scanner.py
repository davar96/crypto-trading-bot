# src/research/funding_rate_scanner.py

import ccxt
import pandas as pd

# --- Configuration ---
# The base assets we want to scan for funding rate opportunities.
# (e.g., 'BTC' will scan the 'BTC/USDT:USDT' perpetual contract)
SYMBOL_UNIVERSE = [
    "BTC",
    "ETH",
    "BNB",
    "SOL",
    "XRP",
    "DOGE",
    "AVAX",
    "LINK",
    "MATIC",
    "LTC",
    "BCH",
    "SHIB",
    "PEPE",
    "ADA",
    "DOT",
]


def scan_funding_rates():
    """
    Scans for funding rate arbitrage opportunities on Binance perpetual futures.
    Fetches the current funding rate for a universe of symbols, calculates the
    annualized return, and prints a sorted table of the best opportunities.
    """
    print("--- Starting Funding Rate Scanner ---")
    print(f"Scanning {len(SYMBOL_UNIVERSE)} symbols on Binance...\n")

    exchange = ccxt.binance(
        {
            "enableRateLimit": True,
            "options": {
                "defaultType": "future",  # Specify we are working with futures
            },
        }
    )

    opportunities = []

    for symbol in SYMBOL_UNIVERSE:
        try:
            # Construct the perpetual contract symbol in the format CCXT expects
            # for USD-M futures. e.g., 'BTC/USDT:USDT'
            perp_symbol = f"{symbol}/USDT:USDT"

            # Fetch the funding rate data
            rate_data = exchange.fetch_funding_rate(perp_symbol)

            funding_rate = rate_data.get("fundingRate")
            mark_price = rate_data.get("markPrice")

            if funding_rate is None or mark_price is None:
                print(f"Warning: Incomplete data for {symbol}. Skipping.")
                continue

            # Funding is typically paid 3 times a day (every 8 hours)
            # Calculate projected APR
            daily_rate = funding_rate * 3
            apr = daily_rate * 365 * 100  # As a percentage

            opportunities.append(
                {
                    "Symbol": symbol,
                    "Mark Price": f"${mark_price:,.2f}",
                    "Funding Rate (%)": f"{funding_rate * 100:.4f}%",
                    "Projected APR (%)": f"{apr:.2f}%",
                }
            )

        except ccxt.DDoSProtection as e:
            print(f"API Rate Limit Error: {e}. Aborting.")
            break
        except ccxt.BaseError as e:
            # Catch other potential CCXT errors (e.g., symbol not found)
            print(f"Notice: Could not fetch data for {symbol}. Reason: {e}")
            continue

    if not opportunities:
        print("\n--- No opportunities found or an error occurred. ---")
        return

    # Create a pandas DataFrame for clean output
    df = pd.DataFrame(opportunities)
    df_sorted = df.sort_values(by="Projected APR (%)", ascending=False).reset_index(drop=True)

    print("\n--- Funding Rate Opportunities Report ---")
    print("(Sorted by highest APR. Positive APR means longs pay shorts.)")
    print(df_sorted.to_string())


if __name__ == "__main__":
    scan_funding_rates()
