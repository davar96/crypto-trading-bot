# 🚀 Algorithmic Cryptocurrency Trading Bot

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Binance](https://img.shields.io/badge/Exchange-Binance-yellow.svg)](https://www.binance.com/)
[![Status](https://img.shields.io/badge/Status-Development-orange.svg)]()
[![Version](https://img.shields.io/badge/Version-5.0-green.svg)]()

> A systematic, disciplined, and risk-managed cryptocurrency trading bot built with Python for the Binance exchange.

This repository contains a modular algorithmic trading bot designed to execute cryptocurrency trades on Binance. Built with extensibility in mind, it allows for easy implementation of new strategies, risk management rules, and exchange integrations. Currently configured for **Binance Testnet** for safe paper-trading.

---

## 📊 Current Status: `Version 5.0 (Trailing Stops)`

The bot implements a "Buy the Dip" trend-following strategy with dynamic volatility-based stop-losses and trailing-stop mechanisms to maximize profits while protecting capital.

---

## ✨ Core Features

### 📈 Trading Capabilities

- **🔄 Multi-Asset Trading**: Simultaneously monitors multiple cryptocurrency pairs (BTC/USDT, ETH/USDT, etc.)
- **🧩 Modular Strategy Engine**: Easily swap and test different trading strategies
- **📱 Real-time Notifications**: Telegram integration for instant trade alerts

### 🎯 Current Strategy: "Buy the Dip"

- **Trend Filter**: Price above 20-period SMA with upward slope (5min chart)
- **Entry Signal**: RSI crosses back above 40 after dipping below
- **Exit Logic**: Dynamic ATR-based stops with trailing functionality

### 🛡️ Risk Management

- **Position Sizing**: Fixed USDT amount per trade (default: $20)
- **Dynamic Stop-Loss**: ATR-based stops that adapt to market volatility
- **Trailing Stops**: Automatically adjusts stops to lock in profits
- **Portfolio Limits**: Maximum concurrent positions to control exposure

### 🔧 Technical Features

- **OCO Orders**: One-Cancels-Other orders for simultaneous SL/TP
- **State Persistence**: Saves positions to `bot_state.json` for restart safety
- **Testnet Integration**: Safe development on Binance's paper-trading environment

---

## 📁 Project Structure

```
crypto-trading-bot/
├── 📂 src/
│   ├── 📂 bot/
│   │   ├── __init__.py
│   │   ├── trading_bot.py        # Main bot orchestrator
│   │   ├── exchange_api.py       # Binance API wrapper
│   │   ├── strategy.py           # Trading strategy logic
│   │   ├── risk_manager.py       # Risk and position management
│   │   ├── notifier.py           # Telegram notifications
│   │   ├── logger.py             # Logging configuration
│   │   └── state_manager.py      # State persistence
│   ├── main.py                   # Entry point
│   ├── cleanup_oco.py            # Legacy cleanup script
│   ├── emergency_cleanup.py      # Full testnet cleanup
│   └── clean_testnet.py          # Original cleanup script
├── 📂 data/                      # CSV data & bot_state.json
├── 📂 logs/                      # Log files
├── .env                          # API keys (⚠️ add to .gitignore!)
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

---

## 🚀 Getting Started

### 1️⃣ Installation

```bash
# Clone the repository
git clone <https://github.com/davar96/crypto-trading-bot>
cd crypto-trading-bot

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2️⃣ Configuration

Create a `.env` file in the root directory:

```env
# Binance Testnet API Keys
# Get from: https://testnet.binance.vision/
TESTNET_API_KEY="your_binance_testnet_api_key"
TESTNET_SECRET_KEY="your_binance_testnet_secret_key"

# Telegram Bot Credentials
# Get from BotFather on Telegram
TELEGRAM_TOKEN="your_telegram_bot_token"
TELEGRAM_CHAT_ID="your_telegram_chat_id"
```

⚠️ **IMPORTANT**: Add `.env` to your `.gitignore` file!

### 3️⃣ Running the Bot

```bash
# Start the trading bot
python src/main.py
```

The bot will initialize, connect to Binance Testnet, and begin scanning for opportunities. You'll receive a startup notification on Telegram.

### 4️⃣ Maintenance & Cleanup

Before starting a new session, clean up any lingering orders:

```bash
# Recommended: Full cleanup
python src/emergency_cleanup.py
```

---

## 🗺️ Development Roadmap

### 🎯 Tier 1 - High Priority

- [ ] **Multi-Timeframe Analysis**: Add higher timeframe confirmation (1H) to reduce false signals
- [ ] **Enhanced Debug Logging**: Detailed logs showing which conditions are met/missed
- [ ] **Parameter Optimization**: Systematic testing of RSI, SMA, and ATR values

### 🚀 Tier 2 - Major Upgrades

- [ ] **Multi-Strategy Framework**: Master controller to switch strategies based on market conditions
- [ ] **Backtesting Engine**: Test strategies on historical data for rapid development
- [ ] **Expanded Universe**: Increase tradable assets to top 20-30 coins

### 🌟 Tier 3 - Long-term Vision

- [ ] **Live Trading Mode**: Production-ready configuration with enhanced security
- [ ] **Analytics Dashboard**: Track KPIs (win rate, Sharpe ratio, max drawdown)
- [ ] **ML Integration**: Dynamic parameter tuning using machine learning

---

## 📞 Telegram Commands

| Command   | Description                                      |
| --------- | ------------------------------------------------ |
| `/status` | Get current portfolio balance and open positions |

---

## ⚡ Quick Tips

- 💡 Always run cleanup scripts before starting a new session
- 📊 Monitor logs in the `logs/` folder for detailed execution info
- 🔄 The bot saves state automatically - safe to restart anytime
- 📱 Keep Telegram notifications on for real-time trade updates

---

## 📝 License

This project is for educational purposes. Trade at your own risk.

---

<p align="center">
  <i>Built with ❤️ for systematic crypto trading</i>
</p>
