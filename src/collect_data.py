import ccxt
import pandas as pd
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import argparse

# --- Configuration ---
DEFAULT_START_YEAR = 2018


def create_exchange(use_testnet=False):
    """Creates and configures the CCXT exchange instance."""
    load_dotenv()
    config = {"enableRateLimit": True, "options": {"defaultType": "future"}}
    if use_testnet:
        print("--- Using Binance Testnet Environment ---")
        config.update(
            {"apiKey": os.getenv("BINANCE_TESTNET_API_KEY"), "secret": os.getenv("BINANCE_TESTNET_API_SECRET")}
        )
        exchange = ccxt.binance(config)
        exchange.set_sandbox_mode(True)
    else:
        print("--- Using Binance Production Environment ---")
        config.update({"apiKey": os.getenv("BINANCE_API_KEY"), "secret": os.getenv("BINANCE_SECRET_KEY")})
        exchange = ccxt.binance(config)
    return exchange


def fetch_ohlcv_data(exchange, symbol, timeframe, start_dt):
    """Fetches historical OHLCV data from a start date and saves it to a CSV file."""
    print(f"\nFetching {timeframe} OHLCV data for {symbol} from {start_dt.strftime('%Y-%m-%d')}...")

    since = int(start_dt.timestamp() * 1000)
    all_ohlcv = []
    limit = 1000

    while True:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
            if not len(ohlcv):
                break
            since = ohlcv[-1][0] + 1
            all_ohlcv.extend(ohlcv)
            print(f"  Fetched {len(ohlcv)} bars, continuing from {pd.to_datetime(ohlcv[-1][0], unit='ms')}")
        except Exception as e:
            print(f"  An error occurred fetching OHLCV for {symbol}: {e}")
            break

    if not all_ohlcv:
        print(f"No OHLCV data returned for {symbol}.")
        return

    df = pd.DataFrame(all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df.drop_duplicates(subset="timestamp", keep="first", inplace=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

    safe_symbol_name = symbol.replace("/", "_").replace(":", "_")
    filename = f"data/{safe_symbol_name}_{timeframe}_ohlcv.csv"
    df.to_csv(filename, index=False)
    print(f"Successfully saved OHLCV data to: {filename}")


def fetch_funding_rate_history(exchange, symbol, start_dt):
    """Fetches historical funding rate data from a start date and saves it to a CSV file."""
    print(f"\nFetching Funding Rate History for {symbol} from {start_dt.strftime('%Y-%m-%d')}...")
    perp_symbol = f"{symbol.split('/')[0]}/USDT:USDT"
    since = int(start_dt.timestamp() * 1000)
    all_rates = []
    limit = 1000

    while True:
        try:
            rates = exchange.fetch_funding_rate_history(perp_symbol, since=since, limit=limit)
            if not len(rates):
                break
            since = rates[-1]["timestamp"] + 1
            all_rates.extend(rates)
            print(
                f"  Fetched {len(rates)} funding rate entries, continuing from {pd.to_datetime(rates[-1]['timestamp'], unit='ms')}"
            )
        except ccxt.BaseError as e:
            print(f"Could not fetch funding rate history for {perp_symbol}. Reason: {e}")
            return
    if not all_rates:
        print(f"No funding rate data returned for {perp_symbol}.")
        return

    df = pd.DataFrame(all_rates, columns=["timestamp", "symbol", "fundingRate", "markPrice"])
    df.drop_duplicates(subset="timestamp", keep="first", inplace=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df[["timestamp", "fundingRate"]]
    filename = f"data/{symbol.replace('/', '_')}_funding_rates.csv"
    df.to_csv(filename, index=False)
    print(f"Successfully saved Funding Rate data to: {filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crypto Data Collector for Binance")
    parser.add_argument("data_type", choices=["ohlcv", "funding", "perp_ohlcv"], help="The type of data to download.")
    parser.add_argument("symbol", type=str, help="The symbol to fetch data for, e.g., 'BTC/USDT'.")
    parser.add_argument(
        "--start_year", type=int, default=DEFAULT_START_YEAR, help="The year to start data collection from."
    )
    parser.add_argument("--testnet", action="store_true", help="Use the Binance Testnet environment.")

    args = parser.parse_args()
    start_date = datetime(args.start_year, 1, 1)

    print("\n--- Starting Data Collection (V2.3) ---")
    if not os.path.exists("data"):
        os.makedirs("data")

    exchange_instance = create_exchange(use_testnet=args.testnet)

    if args.data_type == "ohlcv":
        fetch_ohlcv_data(exchange_instance, args.symbol, "1d", start_date)
        fetch_ohlcv_data(exchange_instance, args.symbol, "4h", start_date)
        fetch_ohlcv_data(exchange_instance, args.symbol, "1h", start_date)
    elif args.data_type == "funding":
        fetch_funding_rate_history(exchange_instance, args.symbol, start_date)
    elif args.data_type == "perp_ohlcv":
        perp_symbol = f"{args.symbol.split('/')[0]}/USDT:USDT"
        fetch_ohlcv_data(exchange_instance, perp_symbol, "1d", start_date)
        fetch_ohlcv_data(exchange_instance, perp_symbol, "4h", start_date)
        fetch_ohlcv_data(exchange_instance, perp_symbol, "1h", start_date)

    print("\n--- Data Collection Finished ---")
