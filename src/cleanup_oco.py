import ccxt
import os
from dotenv import load_dotenv
from bot.logger import logger


def cleanup_all_oco_orders():
    """Cancel all OCO orders specifically"""
    load_dotenv()

    # Initialize exchange
    exchange = ccxt.binance(
        {
            "apiKey": os.getenv("TESTNET_API_KEY"),
            "secret": os.getenv("TESTNET_SECRET_KEY"),
        }
    )
    exchange.set_sandbox_mode(True)

    logger.info("Starting OCO cleanup...")

    # List of all symbols to check
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", "LINK/USDT", "AVAX/USDT"]

    total_cancelled = 0

    # For each symbol, check for OCO orders
    for symbol in symbols:
        try:
            # Get the market ID that Binance uses
            market_id = exchange.market_id(symbol)

            # Use the private API to get OCO order lists
            try:
                oco_lists = exchange.private_get_openorderlist({"symbol": market_id})

                if oco_lists:
                    logger.info(f"Found {len(oco_lists)} OCO order(s) for {symbol}")

                    for oco in oco_lists:
                        try:
                            # Cancel the OCO order list
                            result = exchange.private_delete_orderlist(
                                {"symbol": market_id, "orderListId": oco["orderListId"]}
                            )
                            logger.info(f"✅ Cancelled OCO order {oco['orderListId']} for {symbol}")
                            total_cancelled += 1
                        except Exception as e:
                            logger.error(f"Failed to cancel OCO {oco['orderListId']}: {e}")

            except Exception as e:
                # This is normal if there are no OCO orders
                if "Order list does not exist" not in str(e):
                    logger.debug(f"No OCO orders for {symbol}")

        except Exception as e:
            logger.error(f"Error checking {symbol}: {e}")

    # Also get ALL open OCO orders across all symbols
    try:
        all_oco = exchange.private_get_openorderlist()
        if all_oco:
            logger.info(f"Found {len(all_oco)} additional OCO orders")
            for oco in all_oco:
                try:
                    result = exchange.private_delete_orderlist(
                        {"symbol": oco["symbol"], "orderListId": oco["orderListId"]}
                    )
                    logger.info(f"✅ Cancelled OCO order {oco['orderListId']}")
                    total_cancelled += 1
                except Exception as e:
                    logger.error(f"Failed to cancel OCO: {e}")
    except:
        pass

    logger.info(f"🧹 Cleanup complete! Cancelled {total_cancelled} OCO orders")

    # Final check - show current algo order count
    try:
        account_info = exchange.private_get_account()
        if "rateLimits" in account_info:
            for limit in account_info["rateLimits"]:
                if limit.get("rateLimitType") == "ORDERS":
                    logger.info(f"Current order limits: {limit}")
    except:
        pass


if __name__ == "__main__":
    cleanup_all_oco_orders()
