# src/backtest.py

import pandas as pd
import sys
import numpy as np
from bot.strategy import Strategy
from bot.risk_manager import RiskManager
from bot.logger import logger

# --- Backtest Configuration ---
INITIAL_CASH = 10000.0
SYMBOL = "BTC/USDT"
TRANSACTION_FEE_PERCENT = 0.001  # 0.1% fee for Binance spot trading
SLIPPAGE_PERCENT = 0.0005  # 0.05% slippage estimate per trade side


def run_backtest(symbol):
    print(f"--- Starting Backtest for {symbol} ---")

    # --- 1. Load Data ---
    try:
        df_5m = pd.read_csv(f'data/{symbol.replace("/", "_")}_5m.csv', parse_dates=["timestamp"])
        df_1h = pd.read_csv(f'data/{symbol.replace("/", "_")}_1h.csv', parse_dates=["timestamp"])
    except FileNotFoundError as e:
        logger.error(f"Error loading data: {e}. Run collect_data.py for {symbol} first.")
        return

    # --- 2. Initialize Components ---
    strategy = Strategy()
    risk_manager = RiskManager(
        symbols=[symbol],
        usdt_per_trade=200.0,
        max_open_trades=1,
        atr_multiplier=3.0,
        trailing_stop_activation_pct=0.02,
        trailing_stop_callback_pct=0.01,
    )

    # --- 3. Simulation Setup ---
    cash = INITIAL_CASH
    position = None
    trades = []
    equity_curve = []

    # --- 4. Main Simulation Loop ---
    for i in range(100, len(df_5m)):
        current_candle = df_5m.iloc[i]
        current_price = current_candle["close"]
        current_time = current_candle["timestamp"]

        historical_5m = df_5m.iloc[: i + 1]
        historical_1h = df_1h[df_1h["timestamp"] <= current_time]
        if len(historical_1h) < 100:
            continue

        # --- Position Management ---
        if position:
            if current_price > position["highest_price_seen"]:
                position["highest_price_seen"] = current_price

            if current_price <= position["current_stop_price"]:
                # Slippage: we assume the exit price is slightly worse than the stop price
                exit_price = position["current_stop_price"] * (1 - SLIPPAGE_PERCENT)
                reason = "Stop-Loss Hit" if not position["trailing_stop_activated"] else "Trailing Stop Hit"

                trade_value = position["size"] * exit_price
                fee = trade_value * TRANSACTION_FEE_PERCENT
                cash += trade_value - fee

                pnl = (trade_value - fee) - position["entry_value"]
                trades.append(
                    {
                        "entry_time": position["entry_time"],
                        "exit_time": current_time,
                        "entry_price": position["entry_price"],
                        "exit_price": exit_price,
                        "pnl": pnl,
                        "reason": reason,
                    }
                )
                print(f"{current_time}: {reason.upper()} @ ${exit_price:.2f}. PnL: ${pnl:.2f}. Cash: ${cash:.2f}")
                position = None

            elif not position["trailing_stop_activated"]:
                activation_price = position["entry_price"] * (1 + risk_manager.trailing_stop_activation_pct)
                if current_price >= activation_price:
                    position["trailing_stop_activated"] = True
                    position["current_stop_price"] = position["entry_price"]
                    print(
                        f"{current_time}: Trailing Stop Activated for {symbol} at Break-Even ${position['current_stop_price']:.2f}"
                    )

            if position and position["trailing_stop_activated"]:
                new_potential_stop = position["highest_price_seen"] * (1 - risk_manager.trailing_stop_callback_pct)
                if new_potential_stop > position["current_stop_price"]:
                    position["current_stop_price"] = new_potential_stop

        # --- Entry Logic ---
        if not position:
            ohlcv_5m = historical_5m[["timestamp", "open", "high", "low", "close", "volume"]].values.tolist()
            ohlcv_1h = historical_1h[["timestamp", "open", "high", "low", "close", "volume"]].values.tolist()
            analysis = strategy.get_signal(ohlcv_5m, ohlcv_1h, current_price)

            if analysis.get("signal") == "BUY":
                # Slippage: we assume we buy at a slightly worse price
                entry_price = current_price * (1 + SLIPPAGE_PERCENT)
                trade_size = risk_manager.usdt_per_trade / entry_price
                sl_price = risk_manager.get_stop_loss_price(entry_price, analysis.get("atr"))

                trade_value = trade_size * entry_price
                fee = trade_value * TRANSACTION_FEE_PERCENT

                if cash < (trade_value + fee):
                    print("INSUFFICIENT FUNDS TO PLACE TRADE")
                    continue

                cash -= trade_value + fee

                position = {
                    "size": trade_size,
                    "entry_price": entry_price,
                    "entry_time": current_time,
                    "entry_value": trade_value,
                    "current_stop_price": sl_price,
                    "trailing_stop_activated": False,
                    "highest_price_seen": entry_price,
                }
                print(f"{current_time}: BUY SIGNAL @ ${entry_price:.2f}. Initial SL: ${sl_price:.2f}")

        portfolio_value = cash + (position["size"] * current_price if position else 0)
        equity_curve.append({"timestamp": current_time, "equity": portfolio_value})

    # --- 5. Performance Analysis ---
    print("\n--- Backtest Finished ---")
    if not trades:
        print("No trades were executed.")
        return

    trades_df = pd.DataFrame(trades)
    equity_df = pd.DataFrame(equity_curve)
    equity_df.set_index("timestamp", inplace=True)

    # --- Calculate Metrics ---
    total_trades = len(trades_df)
    wins = trades_df[trades_df["pnl"] > 0]
    losses = trades_df[trades_df["pnl"] <= 0]
    win_rate = (len(wins) / total_trades) * 100 if total_trades > 0 else 0

    net_profit = trades_df["pnl"].sum()
    net_return_pct = (net_profit / INITIAL_CASH) * 100

    gross_profit = wins["pnl"].sum()
    gross_loss = abs(losses["pnl"].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

    avg_win = wins["pnl"].mean() if len(wins) > 0 else 0
    avg_loss = abs(losses["pnl"].mean()) if len(losses) > 0 else 0
    risk_reward_ratio = avg_win / avg_loss if avg_loss > 0 else np.inf

    # Calculate Sharpe Ratio (assuming risk-free rate is 0)
    daily_returns = equity_df["equity"].pct_change().dropna()
    sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(365 * 24 * 12)  # Annualized for 5m data

    # Calculate Maximum Drawdown
    running_max = equity_df["equity"].cummax()
    drawdown = (equity_df["equity"] - running_max) / running_max
    max_drawdown_pct = abs(drawdown.min()) * 100

    # --- Print Report ---
    print("\n--- Performance Report (incl. Fees & Slippage) ---")
    print(f"Period: {df_5m['timestamp'].iloc[0].date()} to {df_5m['timestamp'].iloc[-1].date()}")
    print(f"Initial Portfolio: ${INITIAL_CASH:,.2f}")
    print(f"Final Portfolio:   ${equity_df['equity'].iloc[-1]:,.2f}")

    print("\n--- Profitability ---")
    print(f"Total Net Profit:  ${net_profit:,.2f} ({net_return_pct:.2f}%)")
    print(f"Profit Factor:     {profit_factor:.2f}")
    print(f"Sharpe Ratio:      {sharpe_ratio:.2f}")

    print("\n--- Trade Statistics ---")
    print(f"Total Trades:      {total_trades}")
    print(f"Win Rate:          {win_rate:.2f}%")
    print(f"Average Win:       ${avg_win:,.2f}")
    print(f"Average Loss:      ${avg_loss:,.2f}")
    print(f"Risk/Reward Ratio: {risk_reward_ratio:.2f}:1")

    print("\n--- Risk Metrics ---")
    print(f"Maximum Drawdown:  {max_drawdown_pct:.2f}%")


if __name__ == "__main__":
    target_symbol = sys.argv[1] if len(sys.argv) > 1 else SYMBOL
    run_backtest(target_symbol)
