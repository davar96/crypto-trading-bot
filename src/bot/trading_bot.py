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
        """Checks for positions closed by SL/TP or trailed stops."""
        for symbol in self.symbols:
            pos = self.risk_manager.get_position_details(symbol)
            if pos["size"] > 0:
                stop_order_id = pos["stop_loss_order_id"]
                if not stop_order_id:
                    logger.warning(f"Position for {symbol} has no stop loss ID. Manual check needed.")
                    continue
                try:
                    stop_order = self.exchange.exchange.fetch_order(stop_order_id, symbol)
                    if stop_order["status"] == "closed" and stop_order["filled"] > 0:
                        exit_price = stop_order.get("average", stop_order.get("price"))
                        reason = "Stop-Loss Hit" if not pos["trailing_stop_activated"] else "Trailing Stop Hit"
                        self._process_closed_position(symbol, reason, exit_price)
                        continue  # Move to next symbol

                    # Also check initial TP if trail not yet active
                    if not pos["trailing_stop_activated"]:
                        tp_order_id = pos["take_profit_order_id"]
                        if tp_order_id:
                            tp_order = self.exchange.exchange.fetch_order(tp_order_id, symbol)
                            if tp_order["status"] == "closed" and tp_order["filled"] > 0:
                                exit_price = tp_order.get("average", tp_order.get("price"))
                                self._process_closed_position(symbol, "Take-Profit Hit", exit_price)
                except ccxt.OrderNotFound:
                    logger.warning(f"Order not found for {symbol}. Closing position as a precaution.")
                    self.risk_manager.close_position(symbol)
                except Exception as e:
                    logger.error(f"TradingBot: Error checking exits for {symbol}. {e}")

    def _process_closed_position(self, symbol, reason, exit_price):
        """Helper function to process PnL and notify on a closed position."""
        pos = self.risk_manager.get_position_details(symbol)
        entry_price = pos["entry_price"]
        position_size = pos["size"]
        pnl = (exit_price - entry_price) * position_size
        pnl_pct = ((exit_price / entry_price) - 1) * 100
        pnl_icon = "💰" if pnl > 0 else "📉"
        message = (
            f"🔵 *Position Closed: {symbol}*\n\n"
            f"*Reason:* {reason}\n"
            f"*Entry Price:* ${entry_price:,.4f}\n"
            f"*Exit Price:* ${exit_price:,.4f}\n\n"
            f"{pnl_icon} *PnL:* ${pnl:,.2f} ({pnl_pct:.2f}%)"
        )
        self.notifier.send_message(message)
        logger.info(message.replace("*", ""))
        self.risk_manager.close_position(symbol)
        self.last_trade_time[symbol] = time.time()

    # --- NEW METHOD FOR TRAILING STOPS ---
    def _manage_trailing_stops(self):
        """Manages trailing stop loss for all open positions."""
        for symbol in self.symbols:
            pos = self.risk_manager.get_position_details(symbol)
            if pos["size"] == 0:
                continue

            current_price = self.exchange.get_current_price(symbol)
            if current_price == 0:
                continue

            # Update the highest price seen for the position
            if current_price > pos["highest_price_seen"]:
                self.risk_manager.update_highest_price(symbol, current_price)
                pos["highest_price_seen"] = current_price  # Update local copy

            try:
                # 1. Activation Logic: Move to Break-Even
                if not pos["trailing_stop_activated"]:
                    activation_price = pos["entry_price"] * (1 + self.risk_manager.trailing_stop_activation_pct)
                    if current_price >= activation_price:
                        logger.info(f"Trailing Stop Activation for {symbol} at ${current_price:.4f}")
                        # Cancel the original OCO order
                        self.exchange.cancel_order_list(symbol, pos["oco_list_id"])
                        # Place new SL at break-even
                        new_stop_order = self.exchange.place_stop_market_sell_order(
                            symbol, pos["size"], pos["entry_price"]
                        )
                        # Update state
                        self.risk_manager.activate_trailing_stop(symbol, pos["entry_price"], new_stop_order["id"])
                        self.notifier.send_message(
                            f"🛡️ *Trailing Stop Activated* for {symbol} at break-even (${pos['entry_price']:.4f})."
                        )

                # 2. Trailing Logic: Move the stop up
                else:
                    new_potential_stop_price = pos["highest_price_seen"] * (
                        1 - self.risk_manager.trailing_stop_callback_pct
                    )
                    if new_potential_stop_price > pos["current_stop_price"]:
                        logger.info(
                            f"Trailing Stop for {symbol} from ${pos['current_stop_price']:.4f} to ${new_potential_stop_price:.4f}"
                        )
                        # Cancel old standalone SL
                        self.exchange.cancel_order(symbol, pos["stop_loss_order_id"])
                        # Place new SL
                        new_stop_order = self.exchange.place_stop_market_sell_order(
                            symbol, pos["size"], new_potential_stop_price
                        )
                        # Update state
                        self.risk_manager.update_trailing_stop(symbol, new_potential_stop_price, new_stop_order["id"])
                        self.notifier.send_message(
                            f"🛡️ Trailing stop for {symbol} moved up to `${new_potential_stop_price:.4f}`."
                        )

            except Exception as e:
                logger.error(f"Failed during trailing stop management for {symbol}: {e}")

    def _process_commands(self):  # Omitted for brevity, no changes
        pass

    def _restore_state(self):  # Omitted for brevity, no changes
        pass

    def _save_state(self):  # Omitted for brevity, no changes
        pass

    # In src/bot/trading_bot.py

    def run(self):
        """The main trading loop with Multi-Timeframe Analysis and Robust Error Handling."""
        self.notifier.send_message(
            f"🤖 *Trading Bot Started*\nVersion: 8.0 (Robust & Expanded)\nScanning {len(self.symbols)} symbols."
        )

        logger.info("--- Performing initial state save on startup... ---")
        self._save_state()
        logger.info("--- Initial state save complete. Starting main loop. ---")

        while True:
            try:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                open_pos = self.risk_manager.get_open_positions_count()
                logger.info(
                    f"--- {now} | Open Positions: {open_pos}/{self.risk_manager.max_open_trades} | Scanning ---"
                )

                self._check_for_exits()
                self._manage_trailing_stops()
                self._process_commands()

                if time.time() - self.last_state_save > 300:
                    self._save_state()
                    self.last_state_save = time.time()

                for symbol in self.symbols:
                    try:  # --- ROBUSTNESS SAFEGUARD ---
                        if self.risk_manager.get_position_size(symbol) == 0:
                            if time.time() - self.last_trade_time.get(symbol, 0) < self.position_cooldown:
                                continue
                            if not self.risk_manager.can_open_new_position():
                                continue

                            current_price = self.exchange.get_current_price(symbol)
                            if current_price == 0:
                                continue

                            ohlcv_5m = self.exchange.get_market_data(symbol, "5m", 100)
                            ohlcv_1h = self.exchange.get_market_data(symbol, "1h", 100)

                            if not ohlcv_5m or not ohlcv_1h:
                                continue

                            analysis = self.strategy.get_signal(ohlcv_5m, ohlcv_1h, current_price)

                            if "h1_trend" in analysis:
                                logger.debug(f"{symbol} | H1 Trend: {analysis['h1_trend']}")

                            if analysis.get("signal") == "BUY":
                                logger.info(f"Action: Attempting to open position for {symbol} based on MTA signal.")

                                atr_value = analysis.get("atr")
                                sl_price = self.risk_manager.get_stop_loss_price(current_price, atr_value)
                                tp_price = self.risk_manager.get_initial_take_profit_price(current_price)
                                trade_size = self.risk_manager.calculate_trade_size(current_price)

                                buy_order = self.exchange.place_market_buy_order(symbol, trade_size)
                                entry_price = float(buy_order.get("price", current_price))
                                filled_size = float(buy_order["filled"])

                                if filled_size == 0:
                                    raise Exception("Market buy order was not filled.")

                                oco_order = self.exchange.place_oco_order(symbol, filled_size, tp_price, sl_price)
                                oco_list_id = oco_order["orderListId"]
                                order_reports = oco_order["orderReports"]
                                sl_order_id = next(
                                    (o["orderId"] for o in order_reports if o["type"] == "STOP_LOSS_LIMIT"), None
                                )
                                tp_order_id = next(
                                    (o["orderId"] for o in order_reports if o["type"] == "LIMIT_MAKER"), None
                                )
                                if not sl_order_id or not tp_order_id:
                                    raise Exception("Could not parse SL/TP order IDs.")

                                self.risk_manager.open_position(
                                    symbol, filled_size, entry_price, oco_list_id, sl_order_id, tp_order_id, sl_price
                                )

                                self.notifier.send_message(
                                    f"✅ *New Position Opened (MTA): {symbol}*\n\n"
                                    f"*Entry:* `${entry_price:,.4f}`\n"
                                    f"*Initial SL:* `${sl_price:,.4f}` | *Initial TP:* `${tp_price:,.4f}`"
                                )
                                time.sleep(5)

                    except ccxt.BadSymbol:
                        logger.warning(f"Symbol {symbol} not found on the exchange. Skipping for this session.")
                        # To avoid spamming logs, we can remove it from the list for this run
                        self.symbols.remove(symbol)
                        continue
                    except Exception as e:
                        logger.error(f"An unexpected error occurred for symbol {symbol}: {e}")
                        continue

                time.sleep(10)

            except KeyboardInterrupt:
                logger.info("TradingBot: Manual stop detected.")
                self.notifier.send_message("🤖 *Trading Bot Stopped Manually*")
                self._save_state()
                break
            except Exception as e:
                logger.critical(f"Trading Bot CRASHED (Main Loop) - {e}", exc_info=True)
                self.notifier.send_message(f"💥 *Trading Bot CRASHED (Main Loop)*\n\n`{e}`")
                time.sleep(60)
