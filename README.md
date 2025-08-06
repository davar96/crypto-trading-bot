# Project Chimera: A Post-Mortem on Retail Algorithmic Trading

### Or: How I Spent 300 Hours Learning That Retail Trading Is Dead

## ⚠️ WARNING TO FUTURE DEVELOPERS

**This repository contains 5 different trading strategies that ALL FAILED. This is not because of bugs or poor implementation. This is because retail algorithmic trading is fundamentally nonviable in 2024. Read this README before wasting your time.**

## Executive Summary

Over 6 months, I built and tested 5 different algorithmic trading strategies with professional-grade backtesting, risk management, and execution systems. Every single strategy failed to produce meaningful returns after accounting for real-world costs.

**Final Verdict: The edge required for profitable algorithmic trading no longer exists at retail scale.**

## The Journey: 5 Strategies, 5 Failures

### 1. Momentum/Mean Reversion Strategy (RSI + SMA)

**The Theory:** Buy oversold, sell overbought, follow the trend
**Implementation:**

- RSI < 30 = Buy, RSI > 70 = Sell
- 50/200 SMA crossovers for trend confirmation
- Tested on 4 years of BTC/ETH data

**Results:**

- Annual Return: 0.75%
- Sharpe Ratio: 0.12
- Max Drawdown: 43%

**Why It Failed:**

- By the time RSI shows oversold, institutional algos have already bought
- Moving averages lag by design - you're always late
- Transaction costs (0.1% per trade) destroyed thin margins
- What worked in 2017 is arbitraged away by 2024

### 2. Statistical Arbitrage / Pairs Trading (ETH/BTC)

**The Theory:** Trade the spread when historically correlated pairs diverge
**Implementation:**

- Cointegration testing (Johansen test)
- Z-score entry/exit signals
- Beta-hedged position sizing

**Results:**

- Annual Return: 5.66%
- Sharpe Ratio: 0.89
- Total Trades: 25 in 4 years
- Max Drawdown: 4.20%

**Why It Failed:**

- Crypto pairs are cointegrated only ~20% of the time
- When they diverge, it's usually for fundamental reasons (not mean reversion)
- Capital efficiency terrible - money tied up waiting for rare signals
- 6 trades per year = not statistically significant

### 3. Funding Rate Arbitrage

**The Theory:** Collect funding payments being delta-neutral (spot vs perpetual)
**Implementation:**

- Enter when funding APR > 15-24%
- Exit when funding APR < 4%
- Delta neutral through spot/perp positions

**Results (Optimistic Backtest):**

- Annual Return: ~20%
- Sharpe Ratio: 4-5
- Trades: 3-6 per year

**Results (Reality with Correct Implementation):**

- Annual Return: 4-6%
- Sharpe Ratio: 0.58-0.84
- Trades: 3-5 per year

**Why It Failed:**

- Extreme funding rates (>15% APR) happen 3-5 times per year
- Institutional traders with better execution capture these instantly
- When accounting for execution slippage, profits evaporate
- Capital sits idle 95% of the time

### 4. Simple Trend Following

**The Theory:** Price above 200 SMA + RSI not overbought = Buy
**Implementation:**

- Entry: Price > 200 SMA, RSI < 65-75
- Exit: Stop loss 7%, Take profit 25%
- Position sizing: 25-33% of capital

**Results:**

- Annual Return: 5.57-7.60%
- Sharpe Ratio: 0.82
- Win Rate: 60%
- Trades: 2-3 per year

**Why It Failed:**

- 2-3 trades per year = lottery tickets, not a strategy
- 7.6% annual returns don't justify the complexity and risk
- Better returns available in index funds with zero effort

### 5. Multi-Timeframe Trend Following (The "Nuclear Option")

**The Theory:** Combine daily, 4H, and 1H signals for more opportunities
**Implementation:**

- Hierarchical signal resolution
- Timeframe-specific parameters
- Complex position management

**Results:**

- Annual Return: 3.6%
- Sharpe Ratio: 0.09
- Win Rate: 28%
- Max Drawdown: 28.79%
- Total Trades: 600+

**Why It Failed:**

- Increased complexity led to more whipsaws
- Transaction costs multiplied with trade frequency
- Lower timeframes = more noise, less signal
- 28% win rate = donation system

## The Brutal Truth About Markets in 2024

### Who's Actually Making Money in Algo Trading:

**Institutional Players:**

- **Citadel/Jump Trading:** Nanosecond execution, unlimited capital, see order flow
- **Market Makers:** Paid by exchanges to provide liquidity, guaranteed profit
- **MEV Bots:** Frontrunning transactions on blockchain, requires $1M+ setup

**What They Have That You Don't:**

- Colocated servers (microsecond latency vs your 100ms)
- Direct exchange connections and special API rates
- Teams of PhDs in mathematics and physics
- Access to order flow information
- Capital to survive 50% drawdowns

### The Efficient Market Reality

Every obvious pattern you can find in TradingView has been arbitraged away:

- Moving average crosses? Priced in milliseconds before you see them
- Support/resistance? Algorithms drawing 1000 different lines
- RSI oversold? Institutions bought 5 minutes ago
- Chart patterns? Pattern recognition algos found it first

## Why This Project Has No Future

### The Math Doesn't Work

```python
# Retail Reality
trades_per_year = 50
win_rate = 0.45  # You lose more than you win
average_win = 0.02  # 2%
average_loss = 0.015  # 1.5%
transaction_cost = 0.002  # 0.2% round trip

gross_return = (trades_per_year * win_rate * average_win) -
               (trades_per_year * (1-win_rate) * average_loss)
# = 0.6375 (6.375% gross)

net_return = gross_return - (trades_per_year * transaction_cost)
# = -0.3625 (-36.25% net)

# You're guaranteed to lose money
```
