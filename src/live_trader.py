import ccxt
import time
from dotenv import load_dotenv
import os
import sys
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.strategy import FundingArbStrategy
from src.position_sizer import select_and_size_position
from src.risk_manager import RiskManager
from src.ledger import PaperTradingLedger
from src.bot.notifier import Notifier
from src.bot.state_manager import StateManager
from src.bot.logger import logger

# --- Configuration ---
LOOP_INTERVAL_SECONDS = 60
STARTING_CAPITAL_USD = 100.0
ROUND_TRIP_FEES = 0.001 * 4
ROUND_TRIP_SLIPPAGE = 0.0005 * 2
FUNDING_PERIOD_HOURS = 8


def create_exchange(use_testnet=True):
    load_dotenv()
    config = {"enableRateLimit": True, "options": {"defaultType": "future"}}
    if use_testnet:
        config.update(
            {
                "apiKey": os.getenv("BINANCE_TESTNET_API_KEY"),
                "secret": os.getenv("BINANCE_TESTNET_API_SECRET"),
            }
        )
        exchange = ccxt.binance(config)
        exchange.set_sandbox_mode(True)
    else:
        exchange = ccxt.binance(config)
    return exchange


def main():
    load_dotenv()
    logger.info("--- Initializing Project Chimera: Live Paper Trader (V3.6) ---")

    # Initialize Core Components
    notifier = Notifier()
    exchange = create_exchange(use_testnet=True)
    state_manager = StateManager()

    current_capital = state_manager.load_capital(STARTING_CAPITAL_USD)

    risk_manager = RiskManager(exchange, current_capital, notifier)
    strategy = FundingArbStrategy(exchange)
    ledger = PaperTradingLedger()

    is_in_position = False
    open_position = {}

    last_heartbeat_time = time.time()
    last_periodic_check = time.time()

    # --- STATE RECOVERY LOGIC  ---
    recovered_state = state_manager.load_position_state()
    if recovered_state:
        logger.info("!!! RECOVERED POSITION STATE DETECTED !!!")
        open_position = recovered_state
        is_in_position = True
        logger.info(f"  - Capital from file: ${current_capital:.2f}")
        logger.info(f"  - Entry capital from recovered position: ${open_position.get('entry_capital', 0.0):.2f}")
        notifier.send_message(
            f"🤖 **Project Chimera** RESTARTED & RECOVERED open position for {open_position.get('symbol')}."
        )
    else:
        notifier.send_message("🤖 **Project Chimera (V3.6)** Paper Trader INITIALIZED.")

    while True:
        logger.info("\n----------------------------------")
        logger.info(
            f"Loop start. State: {'IN_POSITION' if is_in_position else 'IDLE'}. Capital: ${current_capital:.2f}"
        )

        try:
            # --- Capital and System Checks (Unchanged) ---
            if not risk_manager.check_capital(current_capital):
                logger.critical("Capital risk check failed. Shutting down.")
                break

            if time.time() - last_periodic_check > 900:
                logger.info("Performing periodic checks (Memory, Exchange Status)...")
                risk_manager.check_memory_usage()
                if not risk_manager.check_exchange_status():
                    logger.warning("Exchange status is not OK. Skipping trading logic for this loop.")
                    last_periodic_check = time.time()
                    time.sleep(LOOP_INTERVAL_SECONDS)
                    continue
                last_periodic_check = time.time()

            if time.time() - last_heartbeat_time > 86400:
                heartbeat_msg = (
                    f"❤️ BOT ALIVE.\n"
                    f"Capital: ${current_capital:.2f}\n"
                    f"State: {'IN_POSITION with ' + open_position.get('symbol', '') if is_in_position else 'IDLE'}"
                )
                notifier.send_message(heartbeat_msg)
                last_heartbeat_time = time.time()

            # --- ENTRY LOGIC (Unchanged) ---
            if not is_in_position:
                signals = strategy.check_entry_signals(current_capital)
                if signals:
                    sized_order = select_and_size_position(signals, current_capital, exchange)
                    if sized_order:
                        log_message = (
                            f"📈 PAPER ENTRY:\n"
                            f"Symbol: {sized_order['symbol']}\n"
                            f"Notional: ${sized_order['notional_value_usd']:.2f}"
                        )
                        logger.info(log_message)
                        notifier.send_message(log_message)

                        is_in_position = True
                        open_position = sized_order
                        open_position["entry_time"] = datetime.datetime.now().isoformat()
                        open_position["entry_capital"] = current_capital
                        ledger.log_trade("ENTER", open_position, current_capital)
                        state_manager.save_position_state(open_position)
            else:
                logger.info(f"Managing open position for {open_position['symbol']}. Monitoring for exit signal...")
                # =================================================================

                if strategy.check_exit_signal(open_position):
                    # 1. Get accurate entry and exit details
                    entry_time = datetime.datetime.fromisoformat(open_position["entry_time"])
                    exit_time = datetime.datetime.now()
                    holding_duration = exit_time - entry_time
                    holding_time_str = str(holding_duration).split(".")[0]
                    entry_capital = open_position["entry_capital"]
                    notional_value = open_position["notional_value_usd"]

                    # 2. Determine how many funding payments were received
                    # This is a robust way to count the number of 8-hour periods crossed
                    num_funding_events = holding_duration.total_seconds() // (FUNDING_PERIOD_HOURS * 3600)

                    # 3. Estimate total GROSS funding PnL
                    initial_apr = open_position.get("initial_apr", 0.0)
                    apr_per_period = (initial_apr / 100) / (365 * (24 / FUNDING_PERIOD_HOURS))
                    gross_funding_pnl = notional_value * apr_per_period * num_funding_events

                    # 4. Calculate total round-trip costs
                    trade_costs = notional_value * (ROUND_TRIP_FEES + ROUND_TRIP_SLIPPAGE)

                    # 5. Calculate Final Net PnL and New Capital
                    net_pnl = gross_funding_pnl - trade_costs
                    # THIS is the only place capital should be updated for a trade.
                    current_capital = entry_capital + net_pnl

                    log_message = (
                        f"📉 PAPER EXIT:\n"
                        f"Symbol: {open_position['symbol']}\n"
                        f"Net PnL: ${net_pnl:.4f}\n"
                        f"  (Gross Funding: ${gross_funding_pnl:.4f} | Costs: ${trade_costs:.4f})\n"
                        f"Held for: {holding_time_str} ({int(num_funding_events)} funding payments)"
                    )
                    logger.info(log_message)
                    notifier.send_message(log_message)

                    open_position["trade_pnl"] = net_pnl
                    ledger.log_trade("EXIT", open_position, current_capital)
                    state_manager.clear_position_state()

                    is_in_position = False
                    open_position = {}
                    # =================================================================

        except Exception as e:
            logger.critical(f"CRITICAL ERROR in main loop: {e}", exc_info=True)
            notifier.send_message(f"🚨 CRITICAL ERROR in main loop: {e}")

        # --- Capital Persistence (Unchanged) ---
        state_manager.save_capital(current_capital)

        logger.info(f"Loop finished. Sleeping for {LOOP_INTERVAL_SECONDS} seconds...")
        time.sleep(LOOP_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
