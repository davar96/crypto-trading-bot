import ccxt
import os
from dotenv import load_dotenv
import time


def emergency_cleanup():
    """Complete cleanup of testnet account"""
    load_dotenv()

    exchange = ccxt.binance(
        {
            "apiKey": os.getenv("TESTNET_API_KEY"),
            "secret": os.getenv("TESTNET_SECRET_KEY"),
        }
    )
    exchange.set_sandbox_mode(True)

    print("Starting emergency cleanup...")

    # Cancel ALL orders for ALL symbols
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", "LINK/USDT", "AVAX/USDT"]

    for symbol in symbols:
        print(f"\nChecking {symbol}...")
        try:
            # Cancel all open orders
            open_orders = exchange.fetch_open_orders(symbol)
            for order in open_orders:
                try:
                    exchange.cancel_order(order["id"], symbol)
                    print(f"  Cancelled order {order['id']}")
                except:
                    pass

            # Try multiple methods to cancel OCO orders
            market_id = exchange.market_id(symbol)

            # Method 1: Get all order lists
            try:
                result = exchange.privateGetOpenOrderList({"symbol": market_id})
                for oco in result:
                    try:
                        exchange.privateDeleteOrderlist({"symbol": market_id, "orderListId": oco["orderListId"]})
                        print(f"  Cancelled OCO {oco['orderListId']}")
                    except:
                        pass
            except:
                pass

            # Method 2: Get account info and check limits
            try:
                account = exchange.privateGetAccount()
                print(f"  Current algo orders: {account.get('totalAlgoOrderCount', 'unknown')}")
            except:
                pass

        except Exception as e:
            print(f"  Error: {e}")

        time.sleep(0.5)  # Don't hit rate limits

    print("\nCleanup complete!")


if __name__ == "__main__":
    emergency_cleanup()
