from .logger import logger


class RiskManager:
    def __init__(
        self,
        symbols,
        usdt_per_trade=20.0,
        max_open_trades=3,
        atr_multiplier=1.5,
        # --- NEW TRAILING STOP PARAMETERS ---
        trailing_stop_activation_pct=0.02,  # Activate trail after 2% profit
        trailing_stop_callback_pct=0.01,  # Keep SL 1% behind the highest price
    ):
        self.usdt_per_trade = usdt_per_trade
        self.max_open_trades = max_open_trades
        self.atr_multiplier = atr_multiplier
        self.trailing_stop_activation_pct = trailing_stop_activation_pct
        self.trailing_stop_callback_pct = trailing_stop_callback_pct

        # --- MODIFIED: Add trailing stop fields to the position state ---
        self.positions = {
            symbol: {
                "size": 0.0,
                "entry_price": 0.0,
                "oco_list_id": None,
                "stop_loss_order_id": None,  # This will now be the ID of the ACTIVE stop
                "take_profit_order_id": None,  # This will be None after trail activates
                "trailing_stop_activated": False,
                "current_stop_price": 0.0,
                "highest_price_seen": 0.0,
            }
            for symbol in symbols
        }
        logger.info(f"RiskManager: Initialized with a max of {max_open_trades} concurrent trades.")
        logger.info(f"RiskManager: Trade size set to ${usdt_per_trade:.2f}.")
        logger.info(f"RiskManager: Using ATR x {self.atr_multiplier} for initial Stop Loss.")
        logger.info(
            f"RiskManager: Trailing stop will activate at +{self.trailing_stop_activation_pct:.1%} and trail at {self.trailing_stop_callback_pct:.1%}."
        )

    def get_open_positions_count(self):
        return sum(1 for pos in self.positions.values() if pos["size"] > 0)

    def can_open_new_position(self):
        return self.get_open_positions_count() < self.max_open_trades

    def get_position_size(self, symbol):
        return self.positions[symbol]["size"]

    def calculate_trade_size(self, current_price):
        return self.usdt_per_trade / current_price

    def get_stop_loss_price(self, entry_price, atr):
        if atr is None or atr <= 0:
            logger.warning("ATR is zero or None, falling back to fixed 3% Stop-Loss.")
            return entry_price * (1 - 0.03)
        stop_loss_amount = atr * self.atr_multiplier
        return entry_price - stop_loss_amount

    # --- TAKE PROFIT IS NOW HANDLED BY THE TRAILING STOP, BUT WE NEED AN INITIAL TP ---
    def get_initial_take_profit_price(self, entry_price):
        # We can set an initial TP, which will be cancelled when the trail starts
        return entry_price * (1 + 0.06)  # 6% initial TP

    def open_position(self, symbol, size, entry_price, oco_list_id, sl_order_id, tp_order_id, sl_price):
        self.positions[symbol]["size"] = size
        self.positions[symbol]["entry_price"] = entry_price
        self.positions[symbol]["oco_list_id"] = oco_list_id
        self.positions[symbol]["stop_loss_order_id"] = sl_order_id
        self.positions[symbol]["take_profit_order_id"] = tp_order_id
        self.positions[symbol]["current_stop_price"] = sl_price  # IMPORTANT: Store initial SL price
        self.positions[symbol]["highest_price_seen"] = entry_price  # Start with entry price
        self.positions[symbol]["trailing_stop_activated"] = False  # Ensure it's false on open
        logger.info(f"RiskManager: Opened position for {symbol}. Initial SL: ${sl_price:.4f}")

    def close_position(self, symbol):
        # Reset all fields, including new ones
        self.positions[symbol] = {
            "size": 0.0,
            "entry_price": 0.0,
            "oco_list_id": None,
            "stop_loss_order_id": None,
            "take_profit_order_id": None,
            "trailing_stop_activated": False,
            "current_stop_price": 0.0,
            "highest_price_seen": 0.0,
        }
        logger.info(f"RiskManager: Closed position for {symbol}. Total open: {self.get_open_positions_count()}.")

    # --- NEW METHODS to manage trailing stop state ---
    def get_position_details(self, symbol):
        return self.positions[symbol]

    def update_trailing_stop(self, symbol, new_stop_price, new_stop_order_id):
        self.positions[symbol]["current_stop_price"] = new_stop_price
        self.positions[symbol]["stop_loss_order_id"] = new_stop_order_id
        logger.info(f"RiskManager: Updated trailing stop for {symbol} to ${new_stop_price:.4f}")

    def activate_trailing_stop(self, symbol, breakeven_stop_price, new_stop_order_id):
        self.positions[symbol]["trailing_stop_activated"] = True
        self.positions[symbol]["current_stop_price"] = breakeven_stop_price
        self.positions[symbol]["stop_loss_order_id"] = new_stop_order_id
        self.positions[symbol]["oco_list_id"] = None  # OCO is no longer active
        self.positions[symbol]["take_profit_order_id"] = None  # TP is no longer active
        logger.info(f"RiskManager: Activated trailing stop for {symbol} at break-even: ${breakeven_stop_price:.4f}")

    def update_highest_price(self, symbol, price):
        self.positions[symbol]["highest_price_seen"] = price
