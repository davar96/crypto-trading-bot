# src/live_trader.py (Version 3.0 - Final Paper Trader Assembly)

import ccxt
import time
from dotenv import load_dotenv
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import our production-grade modules
from src.strategy import FundingArbStrategy
from src.position_sizer import select_and_size_position
from src.risk_manager import RiskManager
from src.ledger import PaperTradingLedger
from src.bot.notifier import Notifier

# --- Configuration ---
LOOP_INTERVAL_SECONDS = 60
STARTING_CAPITAL_USD = 100.0


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
    print("--- Initializing Project Chimera: Live Paper Trader (V3.0) ---")

    # Initialize Core Components
    notifier = Notifier()
    exchange = create_exchange(use_testnet=True)
    strategy = FundingArbStrategy(exchange)
    risk_manager = RiskManager(STARTING_CAPITAL_USD, notifier)
    ledger = PaperTradingLedger()

    current_capital = STARTING_CAPITAL_USD
    is_in_position = False
    open_position = {}

    notifier.send_message("🤖 **Project Chimera** Paper Trader INITIALIZED. Starting loop.")

    # The main bot loop
    while True:
        print("\n----------------------------------")
        print(f"Loop start. State: {'IN_POSITION' if is_in_position else 'IDLE'}. Capital: ${current_capital:.2f}")

        try:
            # 1. RISK CHECK (Top Priority)
            if not risk_manager.check(current_capital):
                print("Risk check failed. Shutting down.")
                break

            if not is_in_position:
                # 2. CHECK FOR ENTRY SIGNALS
                signals = strategy.check_entry_signals(current_capital)

                if signals:
                    # 3. SIZE THE POSITION (Opportunistic Single Trade)
                    sized_order = select_and_size_position(signals, current_capital, exchange)

                    if sized_order:
                        # 4. LOG INTENDED ENTRY
                        log_message = (
                            f"📈 PAPER ENTRY:\n"
                            f"Symbol: {sized_order['symbol']}\n"
                            f"Notional: ${sized_order['notional_value_usd']:.2f}"
                        )
                        print(log_message)
                        notifier.send_message(log_message)

                        # Simulate the state transition (we assume perfect execution for paper trading)
                        is_in_position = True
                        open_position = sized_order
                        ledger.log_trade("ENTER", sized_order, current_capital)

            else:
                # 5. MANAGE OPEN POSITION & CHECK EXIT SIGNALS
                print("Managing open position...")
                if strategy.check_exit_signal(open_position):
                    # 6. LOG INTENDED EXIT
                    log_message = f"📉 PAPER EXIT:\nSymbol: {open_position['symbol']}"
                    print(log_message)
                    notifier.send_message(log_message)

                    # Simulate exiting the position
                    # NOTE: In V3.0 we simulate PnL and update capital here
                    # For now, we will simply log the trade
                    ledger.log_trade("EXIT", open_position, current_capital)

                    is_in_position = False
                    open_position = {}

        except Exception as e:
            error_message = f"🚨 CRITICAL ERROR in main loop: {e}"
            print(error_message)
            notifier.send_message(error_message)
            # Implement the mentor's global shutdown logic here if needed.

        print(f"Loop finished. Sleeping for {LOOP_INTERVAL_SECONDS} seconds...")
        time.sleep(LOOP_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
