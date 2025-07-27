# src/collect_data.py

import ccxt
import pandas as pd
import os
import sys
from datetime import datetime

# Default configuration
DEFAULT_SYMBOL = "BTC/USDT"
DEFAULT_START_YEAR = 2021


def fetch_and_save_data(symbol, timeframe, start_dt):
    """Fetches historical OHLCV data from a start date and saves it to a CSV file."""
    exchange = ccxt.binance({"enableRateLimit": True})

    # Convert the start datetime object to milliseconds for the API
    since = int(start_dt.timestamp() * 1000)

    print(f"Fetching {symbol} {timeframe} data from {start_dt.strftime('%Y-%m-%d')}...")

    try:
        # Fetch data in chunks using a loop
        all_ohlcv = []
        limit = 1000  # Max number of candles per API request
        while True:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
            if len(ohlcv):
                # The 'since' for the next request is the timestamp of the last candle + 1 ms
                since = ohlcv[-1][0] + 1
                all_ohlcv.extend(ohlcv)
                print(f"  Fetched {len(ohlcv)} bars, continuing from {pd.to_datetime(ohlcv[-1][0], unit='ms')}")
            else:
                break  # Exit loop when no more data is returned

        if not all_ohlcv:
            print(f"No data returned for {symbol}. Please check the symbol and timeframe.")
            return

        # Create DataFrame and process the data
        df = pd.DataFrame(all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df.drop_duplicates(subset="timestamp", keep="first", inplace=True)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

        # Create data directory if it doesn't exist
        if not os.path.exists("data"):
            os.makedirs("data")

        # Define filename and save to CSV
        filename = f"data/{symbol.replace('/', '_')}_{timeframe}.csv"
        df.to_csv(filename, index=False)
        print(f"Data for {symbol} ({timeframe}) saved to: {filename}")

    except ccxt.BadSymbol as e:
        print(f"Error: {e}. The symbol '{symbol}' is not supported by the exchange.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    # --- Parse Command-Line Arguments ---
    # Usage: python src/collect_data.py [SYMBOL] [START_YEAR]
    # Example: python src/collect_data.py ETH/USDT 2022

    target_symbol = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SYMBOL
    start_year = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_START_YEAR

    start_date = datetime(start_year, 1, 1)

    print("\n--- Starting Data Collection ---")
    print(f"Symbol: {target_symbol}")
    print(f"Start Date: {start_date.strftime('%Y-%m-%d')}")

    # Fetch data for both timeframes required by the backtester
    fetch_and_save_data(target_symbol, "1h", start_date)
    fetch_and_save_data(target_symbol, "5m", start_date)

    print("\n--- Data Collection Finished ---")
    print(f"You can now run a backtest for {target_symbol} with data since {start_year}.")
