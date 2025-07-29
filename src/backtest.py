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
    print(f"--- Starting High-Performance Backtest for {symbol} ---")

    # --- 1. Load Data ---
    try:
        df_5m = pd.read_csv(f'data/{symbol.replace("/", "_")}_5m.csv', parse_dates=["timestamp"])
        df_1h = pd.read_csv(f'data/{symbol.replace("/", "_")}_1h.csv', parse_dates=["timestamp"])
    except FileNotFoundError as e:
        logger.error(f"Error: {e}. Run collect_data.py for {symbol} first.")
        return

    # --- 2. Vectorized Pre-calculation of Indicators and Signals ---
    print("--- Pre-calculating indicators and signals... ---")
    strategy = Strategy()

    # H1 Trend
    df_1h["sma"] = df_1h["close"].rolling(window=strategy.sma_period).mean()
    df_1h["h1_uptrend"] = df_1h["close"] > df_1h["sma"]
    df_1h.set_index("timestamp", inplace=True)
    h1_trend_resampled = df_1h["h1_uptrend"].resample("5min").ffill()
    df_5m = pd.merge(df_5m, h1_trend_resampled, on="timestamp", how="left")
    df_5m["h1_uptrend"] = df_5m["h1_uptrend"].ffill()

    # 5M Indicators
    df_5m["rsi"] = strategy._calculate_rsi(df_5m, strategy.rsi_period)
    df_5m["atr"] = strategy._calculate_atr(df_5m, strategy.atr_period)

    # --- NEW: Vectorized Volume Calculation ---
    df_5m["avg_volume"] = df_5m["volume"].rolling(window=20).mean()

    # --- Generate Entry Signals with Volume Confirmation ---
    rsi_crossed_up = (df_5m["rsi"] > strategy.rsi_oversold) & (df_5m["rsi"].shift(1) <= strategy.rsi_oversold)
    is_confirmation_candle = df_5m["close"].shift(1) > df_5m["open"].shift(1)

    # --- THE NEW RULE ---
    volume_confirmed = df_5m["volume"].shift(1) > df_5m["avg_volume"].shift(1) * 1.5

    df_5m["signal"] = np.where(
        (df_5m["h1_uptrend"].shift(1) == True) & rsi_crossed_up & is_confirmation_candle & volume_confirmed,
        "BUY",
        "HOLD",
    )
    print("--- Pre-calculation complete. Starting simulation. ---")

    # --- 3. Initialize Simulation Components ---
    risk_manager = RiskManager(
        symbols=[symbol],
        usdt_per_trade=200.0,
        max_open_trades=1,
        atr_multiplier=3.0,
        trailing_stop_activation_pct=0.02,
        trailing_stop_callback_pct=0.01,
    )
    cash = INITIAL_CASH
    position = None
    trades = []
    equity_curve = []

    # --- 4. High-Speed Simulation Loop ---
    # The loop is now simple and fast because all complex calculations are done.
    for i, row in df_5m.iterrows():
        if i < 100:  # Skip warm-up period
            equity_curve.append({"timestamp": row["timestamp"], "equity": cash})
            continue

        current_price = row["close"]

        # --- Position Management ---
        if position:
            if current_price > position["highest_price_seen"]:
                position["highest_price_seen"] = current_price

            if current_price <= position["current_stop_price"]:
                exit_price = position["current_stop_price"] * (1 - SLIPPAGE_PERCENT)
                reason = "Stop-Loss Hit" if not position["trailing_stop_activated"] else "Trailing Stop Hit"

                trade_value = position["size"] * exit_price
                fee = trade_value * TRANSACTION_FEE_PERCENT
                cash += trade_value - fee
                pnl = (trade_value - fee) - position["entry_value"]
                trades.append({"pnl": pnl, "reason": reason})
                print(f"{row['timestamp']}: {reason.upper()} @ ${exit_price:.2f}. PnL: ${pnl:.2f}. Cash: ${cash:.2f}")
                position = None

            elif not position["trailing_stop_activated"]:
                activation_price = position["entry_price"] * (1 + risk_manager.trailing_stop_activation_pct)
                if current_price >= activation_price:
                    position["trailing_stop_activated"] = True
                    position["current_stop_price"] = position["entry_price"]
                    print(
                        f"{row['timestamp']}: Trailing Stop Activated at Break-Even ${position['current_stop_price']:.2f}"
                    )

            if position and position["trailing_stop_activated"]:
                new_potential_stop = position["highest_price_seen"] * (1 - risk_manager.trailing_stop_callback_pct)
                if new_potential_stop > position["current_stop_price"]:
                    position["current_stop_price"] = new_potential_stop

        # --- Entry Logic ---
        if not position and row["signal"] == "BUY" and row["atr"] > 0:
            entry_price = current_price * (1 + SLIPPAGE_PERCENT)
            trade_size = risk_manager.usdt_per_trade / entry_price
            sl_price = risk_manager.get_stop_loss_price(entry_price, row["atr"])

            trade_value = trade_size * entry_price
            fee = trade_value * TRANSACTION_FEE_PERCENT
            if cash < (trade_value + fee):
                continue

            cash -= trade_value + fee
            position = {
                "size": trade_size,
                "entry_price": entry_price,
                "entry_value": trade_value,
                "current_stop_price": sl_price,
                "trailing_stop_activated": False,
                "highest_price_seen": entry_price,
            }
            print(f"{row['timestamp']}: BUY SIGNAL @ ${entry_price:.2f}. Initial SL: ${sl_price:.2f}")

        portfolio_value = cash + (position["size"] * current_price if position else 0)
        equity_curve.append({"timestamp": row["timestamp"], "equity": portfolio_value})

    # --- 5. Performance Analysis ---
    print("\n--- Backtest Finished ---")
    if not trades:
        print("No trades were executed.")
        return

    trades_df = pd.DataFrame(trades)
    equity_df = pd.DataFrame(equity_curve)
    equity_df.set_index("timestamp", inplace=True)

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

    daily_returns = equity_df["equity"].resample("D").last().pct_change().dropna()
    sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(365) if daily_returns.std() > 0 else 0

    running_max = equity_df["equity"].cummax()
    drawdown = (equity_df["equity"] - running_max) / running_max
    max_drawdown_pct = abs(drawdown.min()) * 100

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
