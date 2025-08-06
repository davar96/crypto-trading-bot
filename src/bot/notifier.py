import requests
import os
from src.bot.logger import logger


class Notifier:
    def __init__(self):
        """Initializes the Notifier and clears any old pending commands."""
        self.token = os.getenv("TELEGRAM_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.last_update_id = 0

        if not self.token or not self.chat_id:
            logger.warning("Notifier: Telegram credentials not found. Notifications will be local log only.")
            self.enabled = False
        else:
            logger.info("Notifier: Initialized with Telegram credentials.")
            self.enabled = True
            self.get_commands()

    def send_message(self, message):
        """
        Sends a message locally to the log file and to Telegram.
        """
        clean_message = (
            message.replace("`", "")
            .replace("*", "")
            .replace("~", "")
            .replace("📈", "")
            .replace("📉", "")
            .replace("❤️", "")
            .replace("🤖", "")
            .replace("🚨", "")
        )
        clean_message = clean_message.strip()
        logger.info(f"NOTIFICATION: {clean_message}")

        if not self.enabled:
            return

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "Markdown"}
        try:
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code != 200:
                logger.error(f"Notifier Error: Failed to send Telegram message. Response: {response.text}")
        except Exception as e:
            logger.error(f"Notifier Error: Could not send Telegram message. {e}")

    def get_commands(self):
        """Polls Telegram for new messages and returns them as commands."""
        if not self.enabled:
            return []
        url = f"https://api.telegram.org/bot{self.token}/getUpdates"

        params = {
            "timeout": 1,
            "offset": self.last_update_id + 1,
            "allowed_updates": ["message"],
        }

        try:
            # Added a 5-second timeout for robustness
            response = requests.get(url, params=params, timeout=5)
            updates = response.json().get("result", [])
            if updates:
                self.last_update_id = updates[-1]["update_id"]
                return [
                    update["message"]["text"]
                    for update in updates
                    if "message" in update and "text" in update["message"]
                ]
        except Exception as e:
            logger.error(f"Notifier Error: Could not get Telegram updates. {e}")
        return []
