import ccxt
import os
from dotenv import load_dotenv

def clean_testnet_account():
    """
    A utility script to clean the Binance Testnet account.
    1. Cancels all open orders.
    2. Sells all assets back to USDT (if their value is > $1).
    """
    print("--- Starting Testnet Account Cleanup ---")

    # --- Load Credentials ---
    load_dotenv()
    api_key = os.getenv("TESTNET_API_KEY")
    secret_key = os.getenv("TESTNET_SECRET_KEY")

    if not api_key or not secret_key:
        print("Error: API keys not found in .env file. Aborting.")
        return

    # --- Connect to Exchange ---
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': secret_key,
    })
    exchange.set_sandbox_mode(True)
    print("Successfully connected to Binance Testnet.")

    # --- Action 1: Cancel All Open Orders ---
    print("\n--- Step 1: Canceling all open orders... ---")
    try:
        # Fetch all open orders across all symbols
        open_orders = exchange.fetch_open_orders()
        if not open_orders:
            print("No open orders found.")
        else:
            for order in open_orders:
                try:
                    symbol = order['symbol']
                    order_id = order['id']
                    print(f"Canceling order {order_id} for {symbol}...")
                    exchange.cancel_order(order_id, symbol)
                    print(f"  > Canceled successfully.")
                except Exception as e:
                    print(f"  > Could not cancel order {order.get('id', 'N/A')}: {e}")
    except Exception as e:
        print(f"Error fetching open orders: {e}")

    # --- Action 2: Sell All Non-USDT Assets ---
    print("\n--- Step 2: Selling all held assets to USDT... ---")
    try:
        balance = exchange.fetch_balance()
        assets_to_keep = ['USDT']
        
        for currency, amount in balance['total'].items():
            if currency not in assets_to_keep and amount > 0:
                symbol = f"{currency}/USDT"
                try:
                    # Check if the market exists
                    markets = exchange.load_markets()
                    if symbol in markets:
                        # Estimate the value to avoid selling dust
                        ticker = exchange.fetch_ticker(symbol)
                        usdt_value = amount * ticker['last']
                        
                        # Only sell if the position is worth more than $1
                        if usdt_value > 1.0:
                            print(f"Selling {amount} of {currency} (Value: ${usdt_value:.2f})...")
                            exchange.create_market_sell_order(symbol, amount)
                            print(f"  > Sold successfully.")
                        else:
                            print(f"Skipping {currency} (dust, value is only ${usdt_value:.2f}).")
                except Exception as e:
                    print(f"  > Could not sell {currency}: {e}")

    except Exception as e:
        print(f"Error fetching balances or selling assets: {e}")
        
    print("\n--- Cleanup Script Finished ---")
    print("Your testnet account should now be clean.")

if __name__ == "__main__":
    clean_testnet_account()