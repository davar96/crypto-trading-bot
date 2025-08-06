import pandas as pd
import os
import datetime


class PaperTradingLedger:
    def __init__(self, filename="data/paper_trade_log.csv"):
        self.filename = filename
        self.columns = [
            "timestamp",
            "symbol",
            "action",
            "notional_usd",
            "entry_apr",
            "exit_apr",
            "current_apr",
            "trade_pnl",
            "total_equity",
        ]

        if not os.path.exists("data"):
            os.makedirs("data")

        if os.path.exists(self.filename):
            print(f"Loading existing ledger: {self.filename}")
        else:
            print(f"Creating new ledger: {self.filename}")
            df = pd.DataFrame(columns=self.columns)
            df.to_csv(self.filename, index=False)

    def log_trade(self, action, trade_data, current_equity):
        """
        Logs a trade entry (ENTER or EXIT) to the CSV ledger.
        """
        with open(self.filename, "a+", newline="") as f:
            entry = {
                "timestamp": datetime.datetime.now().isoformat(),
                "symbol": trade_data.get("symbol", "N/A"),
                "action": action,
                "notional_usd": trade_data.get("notional_value_usd", 0.0),
                "entry_apr": trade_data.get("entry_apr", 0.0),
                "exit_apr": trade_data.get("exit_apr", 0.0),
                "current_apr": trade_data.get("current_apr", 0.0),
                "trade_pnl": trade_data.get("trade_pnl", 0.0),
                "total_equity": current_equity,
            }
            # Create a DataFrame to ensure the columns are written in the correct order
            df = pd.DataFrame([entry], columns=self.columns)
            df.to_csv(f, header=False, index=False)

        print(f"LEDGER: Logged {action} for {entry['symbol']}. Equity: ${current_equity:.2f}")
