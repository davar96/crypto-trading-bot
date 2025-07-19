from .logger import logger


class RiskManager:
    def __init__(
        self,
        symbols,
        usdt_per_trade=100.0,
        stop_loss_pct=0.03,
        take_profit_pct=0.06,
        max_open_trades=3,
    ):
        self.usdt_per_trade = usdt_per_trade
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_open_trades = max_open_trades

        self.positions = {symbol: {"size": 0.0, "entry_price": 0.0, "oco_list_id": None} for symbol in symbols}
        logger.info(f"RiskManager: Initialized with a max of {max_open_trades} concurrent trades.")

    def get_open_positions_count(self):
        """Counts how many positions are currently open."""
        return sum(1 for pos in self.positions.values() if pos["size"] > 0)

    def can_open_new_position(self):
        """Checks if the bot is allowed to open a new position."""
        if self.get_open_positions_count() < self.max_open_trades:
            return True
        return False

    def get_position_size(self, symbol):
        return self.positions[symbol]["size"]

    def calculate_trade_size(self, current_price):
        return self.usdt_per_trade / current_price

    def get_stop_loss_price(self, entry_price):
        return entry_price * (1 - self.stop_loss_pct)

    def get_take_profit_price(self, entry_price):
        return entry_price * (1 + self.take_profit_pct)

    def open_position(self, symbol, size, entry_price, oco_list_id):
        self.positions[symbol]["size"] = size
        self.positions[symbol]["entry_price"] = entry_price
        self.positions[symbol]["oco_list_id"] = oco_list_id
        logger.info(f"RiskManager: Opened position for {symbol}. Total open: {self.get_open_positions_count()}.")

    def close_position(self, symbol):
        self.positions[symbol] = {"size": 0.0, "entry_price": 0.0, "oco_list_id": None}
        logger.info(f"RiskManager: Closed position for {symbol}. Total open: {self.get_open_positions_count()}.")

    def get_open_order_id(self, symbol):
        return self.positions[symbol]["oco_list_id"]

    def get_entry_price(self, symbol):
        return self.positions[symbol]["entry_price"]
