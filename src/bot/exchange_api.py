import ccxt
from .logger import logger


class ExchangeAPI:
    def __init__(self, api_key, secret_key):
        self.exchange = ccxt.binance(
            {
                "apiKey": api_key,
                "secret": secret_key,
                "options": {"createMarketBuyOrderRequiresPrice": False},
            }
        )
        self.exchange.set_sandbox_mode(True)
        logger.info("ExchangeAPI: Connected to Binance Testnet.")

    def get_balance(self, currency="USDT"):
        try:
            balance = self.exchange.fetch_balance()
            return balance["total"][currency]
        except Exception as e:
            logger.error(f"ExchangeAPI Error: Could not fetch balance. {e}")
            return 0

    def get_market_data(self, symbol, timeframe, limit):
        try:
            return self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        except Exception as e:
            logger.error(f"ExchangeAPI Error: Could not fetch market data for {symbol}. {e}")
            return []

    def get_current_price(self, symbol):
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker["last"]
        except Exception as e:
            logger.error(f"ExchangeAPI Error: Could not fetch current price for {symbol}. {e}")
            return 0

    def place_market_buy_order(self, symbol, amount):
        logger.info(f"ExchangeAPI: Placing market BUY for {amount} of {symbol}")
        return self.exchange.create_market_buy_order(symbol, amount)

    def place_market_sell_order(self, symbol, amount):
        logger.info(f"ExchangeAPI: Placing market SELL for {amount} of {symbol}")
        return self.exchange.create_market_sell_order(symbol, amount)

    def place_oco_order(self, symbol, amount, take_profit_price, stop_loss_price):
        """Places a One-Cancels-the-Other (OCO) order."""
        logger.info(f"ExchangeAPI: Placing OCO for {symbol} | TP: {take_profit_price}, SL: {stop_loss_price}")

        # OCO orders require prices to be formatted to the exchange's precision rules
        tp_price_str = self.exchange.price_to_precision(symbol, take_profit_price)
        sl_price_str = self.exchange.price_to_precision(symbol, stop_loss_price)
        amount_str = self.exchange.amount_to_precision(symbol, amount)

        # Use the private, raw API call for OCO as it's more reliable than the unified method
        return self.exchange.private_post_order_oco(
            {
                "symbol": self.exchange.market_id(symbol),
                "side": "SELL",
                "quantity": amount_str,
                "price": tp_price_str,  # Take-Profit Price (acts as a LIMIT order)
                "stopPrice": sl_price_str,  # Stop-Loss Trigger Price
                "stopLimitPrice": sl_price_str,  # We set this to the same to make it a Stop-Market order
                "stopLimitTimeInForce": "GTC",
            }
        )

    def cancel_order_list(self, symbol, order_list_id):
        """Cancels an entire OCO order list."""
        logger.info(f"ExchangeAPI: Canceling OCO List with ID {order_list_id} for {symbol}")
        return self.exchange.private_delete_orderlist(
            {
                "symbol": self.exchange.market_id(symbol),
                "orderListId": order_list_id,
            }
        )

    def cancel_all_orders_for_symbol(self, symbol):
        """Cancels all open orders for a given symbol."""
        logger.info(f"ExchangeAPI: Cancelling all open orders for {symbol}")
        try:
            # The unified method is great for this
            return self.exchange.cancel_all_orders(symbol)
        except Exception as e:
            logger.error(f"ExchangeAPI Error: Could not cancel all orders for {symbol}. {e}")

    def place_stop_market_sell_order(self, symbol, amount, stop_price):
        """Places a standalone stop-market sell order."""
        logger.info(f"ExchangeAPI: Placing STOP-MARKET SELL for {amount} of {symbol} at trigger price ${stop_price}")

        # Format amount and price to exchange precision
        amount_str = self.exchange.amount_to_precision(symbol, amount)
        price_str = self.exchange.price_to_precision(symbol, stop_price)

        return self.exchange.create_order(
            symbol=symbol,
            type="STOP_MARKET",
            side="sell",
            amount=amount_str,
            price=None,  # Not needed for STOP_MARKET
            params={"stopPrice": price_str},
        )

    def cancel_order(self, symbol, order_id):
        """Cancels a single order by its ID."""
        logger.info(f"ExchangeAPI: Canceling order {order_id} for {symbol}")
        return self.exchange.cancel_order(order_id, symbol)
