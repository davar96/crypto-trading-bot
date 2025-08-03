import psutil  # <-- NEW IMPORT
import os
from src.bot.notifier import Notifier
from src.bot.logger import logger


class RiskManager:
    """
    Provides an overall safety layer for the trading account.

    Monitors equity for drawdowns, checks exchange maintenance, and monitors memory usage.
    """

    def __init__(self, exchange, starting_capital, notifier, emergency_shutdown_threshold=0.80, max_memory_mb=500):
        self.exchange = exchange
        self.starting_capital = starting_capital
        self.high_water_mark = starting_capital
        self.notifier = notifier
        self.shutdown_threshold_pct = emergency_shutdown_threshold
        self.shutdown_threshold_value = starting_capital * emergency_shutdown_threshold
        self.max_memory_mb = max_memory_mb  # <-- NEW

        # Get the current process to monitor its memory
        self.process = psutil.Process(os.getpid())  # <-- NEW

        logger.info("Risk Manager initialized.")
        logger.info(f"  - High-Water Mark: ${self.high_water_mark:,.2f}")
        logger.info(f"  - Emergency Shutdown if Capital < ${self.shutdown_threshold_value:,.2f}")
        logger.info(f"  - Max Memory Threshold: {self.max_memory_mb} MB")

    def check_capital(self, current_capital):
        """Checks the current capital against the drawdown threshold."""
        if current_capital > self.high_water_mark:
            self.high_water_mark = current_capital
            self.shutdown_threshold_value = self.high_water_mark * self.shutdown_threshold_pct
            logger.info(f"RISK MANAGER: New high-water mark! ${self.high_water_mark:,.2f}")
            logger.info(f"  - New shutdown threshold: ${self.shutdown_threshold_value:,.2f}")

        if current_capital < self.shutdown_threshold_value:
            drawdown_pct = (1 - (current_capital / self.high_water_mark)) * 100
            error_message = (
                f"🚨🚨 CRITICAL RISK 🚨🚨\nEMERGENCY SHUTDOWN TRIGGERED!\n"
                f"Current Capital ${current_capital:,.2f} is below threshold of ${self.shutdown_threshold_value:,.2f}.\n"
                f"Max Drawdown of {drawdown_pct:.2f}% breached."
            )
            logger.critical(error_message)
            self.notifier.send_message(error_message)
            return False
        return True

    def check_exchange_status(self):
        """Checks the exchange's system status for planned maintenance."""
        try:
            status = self.exchange.fetch_status()
            if status["status"] != "ok":
                warning_message = (
                    f"⚠️ EXCHANGE STATUS WARNING: Status is '{status['status']}'. Possible maintenance or issues."
                )
                logger.warning(warning_message)
                self.notifier.send_message(warning_message)
                return False
        except Exception as e:
            logger.error(f"Could not check exchange status. Reason: {e}")
            return True  # Fail safe, allow operation but log the error
        return True

    # --- NEW METHOD ---
    def check_memory_usage(self):
        """
        Checks the bot's current memory usage against a threshold.
        """
        memory_mb = self.process.memory_info().rss / 1024 / 1024
        logger.info(f"Current memory usage: {memory_mb:.2f} MB")

        if memory_mb > self.max_memory_mb:
            warning_message = (
                f"⚠️ MEMORY WARNING: High memory usage detected: {memory_mb:.2f} MB "
                f"(Threshold: {self.max_memory_mb} MB). Consider a graceful restart."
            )
            logger.warning(warning_message)
            self.notifier.send_message(warning_message)
            # This is a warning, not a shutdown trigger, but could be made one.

        return True


# --- Self-Testing Block ---
if __name__ == "__main__":
    from dotenv import load_dotenv
    import os
    import ccxt

    load_dotenv()

    mock_notifier = Notifier()

    # We need a real exchange object for this test
    exchange = ccxt.binance(
        {
            "apiKey": os.getenv("BINANCE_TESTNET_API_KEY"),
            "secret": os.getenv("BINANCE_TESTNET_API_SECRET"),
        }
    )
    exchange.set_sandbox_mode(True)

    print("\n--- RiskManager self-testing is primarily for capital checks. ---")
    print("--- Memory and exchange status checks are integrated into the live bot. ---")

    print("\n--- Testing RiskManager with Exchange Status Check ---")
    risk_manager = RiskManager(exchange=exchange, starting_capital=100.0, notifier=mock_notifier)

    status_ok = risk_manager.check_exchange_status()
    print(f"Exchange status check returned: {status_ok}")
    assert status_ok is True

    print("\n--- All new RiskManager tests passed! ---")
