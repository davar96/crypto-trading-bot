# src/live_trader.py (Version 3.1 - With PnL Simulation & Heartbeat)

import ccxt
import time
from dotenv import load_dotenv
import os
import sys
import datetime

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
# Costs are now defined in the main script to be passed to the PnL calculation
ROUND_TRIP_FEES = 0.001 * 4
ROUND_TRIP_SLIPPAGE = 0.0005 * 2


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
    print("--- Initializing Project Chimera: Live Paper Trader (V3.1) ---")

    # Initialize Core Components
    notifier = Notifier()
    exchange = create_exchange(use_testnet=True)
    strategy = FundingArbStrategy(exchange)
    risk_manager = RiskManager(STARTING_CAPITAL_USD, notifier)
    ledger = PaperTradingLedger()

    current_capital = STARTING_CAPITAL_USD
    is_in_position = False
    open_position = {}

    # Variables for heartbeat and PnL simulation
    last_heartbeat_time = time.time()

    notifier.send_message("🤖 **Project Chimera (V3.1)** Paper Trader INITIALIZED. Starting loop.")

    # The main bot loop
    while True:
        print("\n----------------------------------")
        print(f"Loop start. State: {'IN_POSITION' if is_in_position else 'IDLE'}. Capital: ${current_capital:.2f}")

        try:
            # 1. RISK CHECK
            if not risk_manager.check(current_capital):
                print("Risk check failed. Shutting down.")
                break

            # --- HEARTBEAT LOGIC ---
            if time.time() - last_heartbeat_time > 86400:  # 86400 seconds = 24 hours
                heartbeat_msg = (
                    f"❤️ BOT ALIVE.\n"
                    f"Capital: ${current_capital:.2f}\n"
                    f"State: {'IN_POSITION with ' + open_position.get('symbol', '') if is_in_position else 'IDLE'}"
                )
                notifier.send_message(heartbeat_msg)
                last_heartbeat_time = time.time()

            # --- MAIN TRADING LOGIC ---
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
                        print(log_message)
                        notifier.send_message(log_message)

                        is_in_position = True
                        open_position = sized_order
                        open_position["entry_time"] = datetime.datetime.now()
                        open_position["entry_capital"] = current_capital
                        ledger.log_trade("ENTER", open_position, current_capital)
            else:
                # Get the current funding rate to simulate PnL
                perp_symbol = f"{open_position['symbol'].split('/')[0]}/USDT:USDT"
                rate_data = exchange.fetch_funding_rate(perp_symbol)
                current_funding_rate = rate_data.get("fundingRate", 0.0)

                # Simulate the profit from this funding period
                funding_pnl = open_position["notional_value_usd"] * current_funding_rate
                current_capital += funding_pnl

                print(f"Managing open position... Funding PnL for this period: ${funding_pnl:.4f}")

                if strategy.check_exit_signal(open_position):
                    # --- PNL SIMULATION & EXIT LOGIC ---
                    entry_capital = open_position["entry_capital"]
                    trade_pnl = current_capital - entry_capital

                    # Subtract estimated costs for the round trip
                    trade_costs = open_position["notional_value_usd"] * (ROUND_TRIP_FEES + ROUND_TRIP_SLIPPAGE)
                    net_pnl = trade_pnl - trade_costs

                    # Final capital update
                    current_capital = entry_capital + net_pnl

                    holding_time = datetime.datetime.now() - open_position["entry_time"]

                    log_message = (
                        f"📉 PAPER EXIT:\n"
                        f"Symbol: {open_position['symbol']}\n"
                        f"Net PnL: ${net_pnl:.2f} (Costs: ~${trade_costs:.2f})\n"
                        f"Held for: {str(holding_time).split('.')[0]}"
                    )
                    print(log_message)
                    notifier.send_message(log_message)

                    open_position["trade_pnl"] = net_pnl
                    ledger.log_trade("EXIT", open_position, current_capital)

                    is_in_position = False
                    open_position = {}

        except Exception as e:
            error_message = f"🚨 CRITICAL ERROR in main loop: {e}"
            print(error_message)
            notifier.send_message(error_message)

        print(f"Loop finished. Sleeping for {LOOP_INTERVAL_SECONDS} seconds...")
        time.sleep(LOOP_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
