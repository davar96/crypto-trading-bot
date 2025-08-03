# src/risk_manager.py (Version 1.0)

from src.bot.notifier import Notifier  # Using absolute import path


class RiskManager:
    """
    Provides an overall safety layer for the trading account.

    Monitors total equity and triggers a global shutdown if a critical
    drawdown threshold is breached.
    """

    def __init__(self, starting_capital, notifier, emergency_shutdown_threshold=0.80):
        """
        Initializes the RiskManager.

        Args:
            starting_capital (float): The initial capital of the account.
            notifier (Notifier): An initialized Notifier object.
            emergency_shutdown_threshold (float): The capital percentage below which to shut down.
                                                  0.80 means a 20% drawdown.
        """
        self.starting_capital = starting_capital
        self.high_water_mark = starting_capital
        self.notifier = notifier
        self.shutdown_threshold_pct = emergency_shutdown_threshold
        self.shutdown_threshold_value = starting_capital * emergency_shutdown_threshold

        print("Risk Manager initialized.")
        print(f"  - High-Water Mark: ${self.high_water_mark:,.2f}")
        print(f"  - Emergency Shutdown if Capital < ${self.shutdown_threshold_value:,.2f}")

    def check(self, current_capital):
        """
        Checks the current capital against risk thresholds.

        Args:
            current_capital (float): The current total equity of the account.

        Returns:
            bool: True if everything is OK, False if a shutdown is triggered.
        """
        # Update the high-water mark if we've reached a new equity peak
        if current_capital > self.high_water_mark:
            self.high_water_mark = current_capital
            # Adjust the shutdown value based on the new peak
            self.shutdown_threshold_value = self.high_water_mark * self.shutdown_threshold_pct
            print(f"RISK MANAGER: New high-water mark! ${self.high_water_mark:,.2f}")
            print(f"  - New shutdown threshold: ${self.shutdown_threshold_value:,.2f}")

        # The critical check
        if current_capital < self.shutdown_threshold_value:
            drawdown_pct = (1 - (current_capital / self.high_water_mark)) * 100

            error_message = (
                f"🚨🚨 CRITICAL RISK 🚨🚨\n"
                f"EMERGENCY SHUTDOWN TRIGGERED!\n"
                f"Current Capital ${current_capital:,.2f} is below threshold of ${self.shutdown_threshold_value:,.2f}.\n"
                f"Max Drawdown of {drawdown_pct:.2f}% breached."
            )
            print(error_message)
            self.notifier.send_message(error_message)
            return False  # Signal to shut down

        # If we reach here, all checks have passed.
        return True  # Signal that everything is OK.


# --- Self-Testing Block ---
if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    mock_notifier = Notifier()

    print("\n--- Test Case 1: Initial State ---")
    risk_manager = RiskManager(starting_capital=100.0, notifier=mock_notifier)
    assert risk_manager.high_water_mark == 100.0
    assert risk_manager.shutdown_threshold_value == 80.0

    print("\n--- Test Case 2: Capital Growth (No Shutdown) ---")
    # Simulate a profitable trade
    ok = risk_manager.check(current_capital=110.0)
    assert ok is True
    assert risk_manager.high_water_mark == 110.0
    assert risk_manager.shutdown_threshold_value == 88.0  # 80% of 110

    print("\n--- Test Case 3: Minor Drawdown (No Shutdown) ---")
    # Simulate a small loss
    ok = risk_manager.check(current_capital=105.0)
    assert ok is True
    assert risk_manager.high_water_mark == 110.0  # HWM does not decrease

    print("\n--- Test Case 4: Critical Drawdown (SHUTDOWN) ---")
    # Simulate a major loss that breaches the threshold
    print("Testing a critical breach...")
    ok = risk_manager.check(current_capital=85.0)
    assert ok is False  # Should return False to signal a shutdown

    print("\n--- All RiskManager tests passed! ---")
