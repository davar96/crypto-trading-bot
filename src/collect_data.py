import ccxt
import pandas as pd
import os

# This is the function definition. It tells Python what to do when called.
def fetch_historical_data(symbol, timeframe, limit):
    """
    Fetches historical OHLCV data from Binance and saves it to a CSV file.
    """
    
    # Initialize exchange
    exchange = ccxt.binance({'enableRateLimit': True})
    
    print(f"Fetching {limit} bars of {symbol} data with a {timeframe} timeframe...")
    
    try:
        # 1. Fetch the data
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        if not ohlcv:
            print(f"No data returned for {symbol}. Please check the symbol and timeframe.")
            return

        # 2. Convert to a pandas DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # 3. Convert timestamp to a human-readable format
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        print("Data fetched successfully.")
        print("Sample of the last 5 rows:")
        print(df.tail().to_string())

        # 4. Save to CSV
        if not os.path.exists('data'):
            os.makedirs('data')
            
        filename = f"data/{symbol.replace('/', '_')}_{timeframe}_{limit}_bars.csv"
        df.to_csv(filename, index=False)
        print(f"\nData saved to: {filename}")
        print(f"You can now run the backtest with this command:")
        print(f"python src/backtest.py {filename}")

    except ccxt.BadSymbol as e:
        print(f"Error: {e}. The symbol '{symbol}' is not supported by the exchange.")
    except Exception as e:
        print(f"An error occurred: {e}")


# ==============================================================================
# This is the crucial part that ACTUALLY RUNS the script.
# It acts as the entry point, or the "start button".
# ==============================================================================
if __name__ == "__main__":
    # --- Configuration ---
    target_symbol = 'BTC/USDT'
    target_timeframe = '1h'
    bar_limit = 500
    
    # This line CALLS the function defined above.
    fetch_historical_data(target_symbol, target_timeframe, bar_limit)