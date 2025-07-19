import pandas as pd
import sys

# --- Parameters ---
sma_period = 20
initial_cash = 10000.0

def run_backtest(file_path):
    print("--- Starting Backtest ---")
    
    # 1. Load Data
    try:
        df = pd.read_csv(file_path)
        if 'close' not in df.columns:
            print("Error: CSV file must contain a 'close' column.")
            return
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return

    print(f"Loaded {len(df)} data points.")

    # 2. Calculate Indicators
    df['sma'] = df['close'].rolling(window=sma_period).mean()
    df = df.dropna()

    # 3. Simulate Trading
    cash = initial_cash
    btc_holdings = 0.0
    position = 'none'

    for index, row in df.iterrows():
        current_price = row['close']
        current_sma = row['sma']

        # Buy condition: Price crosses above SMA and we are not in a position
        if current_price > current_sma and position == 'none':
            btc_holdings = cash / current_price
            cash = 0.0
            position = 'long'
            print(f"{pd.to_datetime(row['timestamp'])}: BUY signal @ ${current_price:.2f}. Holdings: {btc_holdings:.6f} BTC")

        # Sell condition: Price crosses below SMA and we are in a position
        elif current_price < current_sma and position == 'long':
            cash = btc_holdings * current_price
            btc_holdings = 0.0
            # THE FIX: We are now 'none' because we just sold.
            position = 'none' 
            print(f"{pd.to_datetime(row['timestamp'])}: SELL signal @ ${current_price:.2f}. Cash: ${cash:.2f}")

    # 4. Calculate Final Performance
    print("\n--- Backtest Finished ---")
    
    final_portfolio_value = cash
    if btc_holdings > 0:
        final_portfolio_value = btc_holdings * df['close'].iloc[-1]

    profit_loss = final_portfolio_value - initial_cash
    profit_percent = (profit_loss / initial_cash) * 100

    print(f"\nInitial Portfolio Value: ${initial_cash:.2f}")
    print(f"Final Portfolio Value:   ${final_portfolio_value:.2f}")
    print(f"Profit/Loss:             ${profit_loss:.2f} ({profit_percent:.2f}%)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python src/backtest.py <path_to_csv_file>")
    else:
        csv_file_path = sys.argv[1]
        run_backtest(csv_file_path)