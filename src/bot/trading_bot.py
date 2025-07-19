from .exchange_api import ExchangeAPI
from .strategy import Strategy
from .risk_manager import RiskManager
from .notifier import Notifier
from .logger import logger
from datetime import datetime
from .state_manager import StateManager
import time
from collections import defaultdict
import ccxt


class TradingBot:
    def __init__(self, api_key, secret_key, symbols):
        self.exchange = ExchangeAPI(api_key, secret_key)
        self.strategy = Strategy()
        self.risk_manager = RiskManager(symbols)
        self.notifier = Notifier()
        self.state_manager = StateManager()
        self.symbols = symbols
        self.last_state_save = time.time()
        self.last_trade_time = defaultdict(float)
        self.position_cooldown = 300
        self._restore_state()
        logger.info("TradingBot: Initialized.")

    def _check_for_exits(self):
        """Checks for and handles positions closed by SL/TP hits."""
        for symbol in self.symbols:
            if self.risk_manager.get_position_size(symbol) > 0:
                try:
                    oco_list_id = self.risk_manager.get_open_order_id(symbol)
                    # Use CCXT's fetchOrders to check the status of orders in the list
                    # This is a simplified check. A more robust way is to query the specific orderList if available.
                    open_orders = self.exchange.exchange.fetch_open_orders(symbol)

                    # If our OCO order is no longer in the list of open orders, it was filled or canceled.
                    if not any(
                        order["id"] in str(oco_list_id) for order in open_orders
                    ):
                        # Note: This check is basic. Binance doesn't provide a simple way to check OCO list status via unified API.
                        # We assume if the orders are gone, the position is closed.
                        logger.info(
                            f"TradingBot: OCO for {symbol} no longer open. Assuming SL/TP hit."
                        )

                        entry_price = self.risk_manager.get_entry_price(symbol)
                        current_price = self.exchange.get_current_price(
                            symbol
                        )  # Approximate exit price
                        position_size = self.risk_manager.get_position_size(symbol)

                        pnl = (current_price - entry_price) * position_size
                        pnl_pct = ((current_price / entry_price) - 1) * 100
                        pnl_icon = "💰" if pnl > 0 else "📉"

                        message = (
                            f"🔵 *Position Closed (SL/TP): {symbol}*\n\n"
                            f"*Reason:* Stop-Loss or Take-Profit Hit\n"
                            f"*Approx Exit Price:* ${current_price:,.2f}\n\n"
                            f"{pnl_icon} *PnL:* ${pnl:,.2f} ({pnl_pct:.2f}%)"
                        )
                        self.notifier.send_message(message)
                        self.risk_manager.close_position(symbol)
                        self.last_trade_time[symbol] = time.time()

                except Exception as e:
                    logger.error(f"TradingBot: Error checking exits for {symbol}. {e}")

    def _process_commands(self):
        """Checks for and processes incoming commands from Telegram."""
        commands = self.notifier.get_commands()
        for command in commands:
            if command == "/status":
                logger.info("TradingBot: Received /status command. Generating report.")

                usdt_balance = self.exchange.get_balance()
                open_positions_summary = []
                total_unrealized_pnl = 0

                for symbol in self.symbols:
                    size = self.risk_manager.get_position_size(symbol)
                    if size > 0:
                        entry_price = self.risk_manager.get_entry_price(symbol)
                        current_price = self.exchange.get_current_price(symbol)
                        pnl = (current_price - entry_price) * size
                        pnl_pct = ((current_price / entry_price) - 1) * 100
                        total_unrealized_pnl += pnl
                        pnl_icon = "🟢" if pnl > 0 else "🔴"

                        summary = (
                            f"*{symbol}*\n"
                            f"  Size: `{size}`\n"
                            f"  Entry: `${entry_price:,.2f}`\n"
                            f"  Current: `${current_price:,.2f}`\n"
                            f"  PnL: {pnl_icon} `${pnl:,.2f}` `({pnl_pct:.2f}%)`"
                        )
                        open_positions_summary.append(summary)

                positions_text = (
                    "\n\n".join(open_positions_summary)
                    if open_positions_summary
                    else "No open positions."
                )

                message = (
                    f"🤖 *Bot Status Report*\n\n"
                    f"*{'RUNNING'}*\n\n"
                    f"💰 *Portfolio*\n"
                    f"  USDT Balance: `${usdt_balance:,.2f}`\n"
                    f"  Unrealized PnL: `${total_unrealized_pnl:,.2f}`\n\n"
                    f"📈 *Open Positions ({len(open_positions_summary)})*\n"
                    f"---------------------\n"
                    f"{positions_text}"
                )
                self.notifier.send_message(message)

    def _restore_state(self):
        """Restore bot state from file if it exists"""
        state = self.state_manager.load_state()
        if state and "positions" in state:
            # Ask user if they want to restore
            logger.warning("Found previous bot state. Positions will be restored.")
            self.notifier.send_message(
                "🔄 *Bot Restarted*\n\n" "Found previous state. Restoring positions..."
            )

            # Restore positions
            self.risk_manager.positions = state["positions"]

            # Log restored positions
            open_count = self.risk_manager.get_open_positions_count()
            if open_count > 0:
                logger.info(f"Restored {open_count} open positions")
                self.notifier.send_message(f"✅ Restored {open_count} open positions")

    def _save_state(self):
        """Save current state to file"""
        self.state_manager.save_state(self.risk_manager)

    def run(self):
        """The main trading loop with atomic, resilient logic."""
        self.notifier.send_message(
            f"🤖 *Trading Bot Started*\nVersion: 3.2 (Hardened & Resilient)\nScanning: `{', '.join(self.symbols)}`"
        )

        while True:
            try:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.info(f"--- {now} | Scanning {len(self.symbols)} symbols ---")

                self._process_commands()
                self._check_for_exits()

                # Save state every 5 minutes
                if time.time() - self.last_state_save > 300:  # 300 seconds = 5 minutes
                    self._save_state()
                    self.last_state_save = time.time()

                for symbol in self.symbols:
                    position_size = self.risk_manager.get_position_size(symbol)
                    current_price = self.exchange.get_current_price(symbol)
                    if current_price == 0:
                        continue

                    ohlcv = self.exchange.get_market_data(symbol, "1m", 50)
                    if not ohlcv:
                        continue

                    analysis = self.strategy.get_signal(ohlcv, current_price)
                    signal = analysis["signal"]
                    logger.debug(
                        f"{symbol} | Price: ${current_price:,.2f} | Signal: {signal} | Position: {'long' if position_size > 0 else 'none'}"
                    )

                    # --- ATOMIC BUY LOGIC ---
                    if signal == "BUY" and position_size == 0:

                        if (
                            time.time() - self.last_trade_time.get(symbol, 0)
                            < self.position_cooldown
                        ):
                            logger.debug(f"Skipping {symbol} - In cooldown period")
                            continue

                        if not self.risk_manager.can_open_new_position():
                            logger.debug(
                                f"Skipping {symbol} - Max open trades reached ({self.risk_manager.max_open_trades})"
                            )
                            continue

                        if (
                            self.exchange.get_balance()
                            >= self.risk_manager.usdt_per_trade
                        ):
                            logger.info(
                                f"Action: Attempting to open position for {symbol}."
                            )
                            try:
                                trade_size = self.risk_manager.calculate_trade_size(
                                    current_price
                                )
                                buy_order = self.exchange.place_market_buy_order(
                                    symbol, trade_size
                                )
                                entry_price = float(
                                    buy_order.get("price", current_price)
                                )
                                filled_size = float(buy_order["filled"])
                                sl_price = self.risk_manager.get_stop_loss_price(
                                    entry_price
                                )
                                tp_price = self.risk_manager.get_take_profit_price(
                                    entry_price
                                )
                                oco_order = self.exchange.place_oco_order(
                                    symbol, filled_size, tp_price, sl_price
                                )
                                self.risk_manager.open_position(
                                    symbol,
                                    filled_size,
                                    entry_price,
                                    oco_order["orderListId"],
                                )

                                message = (
                                    f"✅ *New Position Opened: {symbol}*\n\n"
                                    f"*Side:* `BUY`\n"
                                    f"*Size:* `{filled_size:.6f}`\n"
                                    f"*Value:* `${self.risk_manager.usdt_per_trade:,.2f}`\n"
                                    f"*Entry Price:* `${entry_price:,.2f}`\n\n"
                                    f"🛡️ *OCO Set*\nSL: `${sl_price:,.2f}` | TP: `${tp_price:,.2f}`"
                                )
                                self.notifier.send_message(message)

                                # --- COOL-DOWN PERIOD ---
                                logger.info(
                                    "Cooling down for 5 seconds after successful trade."
                                )
                                time.sleep(5)

                            except Exception as e:
                                error_message = f"Failed to open position for {symbol}. Error: `{e}`"
                                logger.error(error_message)
                                self.notifier.send_message(
                                    f"⚠️ *Trade Execution Warning*\n\n{error_message}"
                                )

                    # --- ATOMIC SELL LOGIC ---
                    elif signal == "SELL" and position_size > 0:
                        logger.info(
                            f"Action: Attempting to close position for {symbol}."
                        )
                        try:
                            oco_list_id = self.risk_manager.get_open_order_id(symbol)
                            if oco_list_id:
                                self.exchange.cancel_order_list(symbol, oco_list_id)

                            entry_price = self.risk_manager.get_entry_price(symbol)
                            sell_order = self.exchange.place_market_sell_order(
                                symbol, position_size
                            )
                            exit_price = float(sell_order.get("price", current_price))
                            pnl = (exit_price - entry_price) * position_size
                            pnl_pct = ((exit_price / entry_price) - 1) * 100
                            pnl_icon = "💰" if pnl > 0 else "📉"

                            message = (
                                f"❌ *Position Closed (Strategy): {symbol}*\n\n"
                                f"*PnL:* `{pnl_icon} ${pnl:,.2f} ({pnl_pct:.2f} %)`"
                            )
                            self.notifier.send_message(message)
                            self.risk_manager.close_position(symbol)

                        except Exception as e:
                            error_message = (
                                f"Failed to close position for {symbol}. Error: `{e}`"
                            )
                            logger.error(error_message)
                            self.notifier.send_message(
                                f"⚠️ *Trade Execution Warning*\n\n{error_message}"
                            )

                time.sleep(15)

            except KeyboardInterrupt:
                self.notifier.send_message("🤖 *Trading Bot Stopped Manually*")
                break
            except Exception as e:
                error_message = f"💥 *Trading Bot CRASHED (Main Loop)*\n\n`{e}`"
                self.notifier.send_message(error_message)
                logger.critical(error_message)
                time.sleep(60)
