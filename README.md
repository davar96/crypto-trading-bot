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

````python
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
Survivorship Bias in Trading Content
For every YouTuber showing profitable strategies:

100 failed traders stayed silent
Cherry-picked timeframes
Doesn't include fees/slippage
Often paper trading or falsified results

What Actually Works (For Developers)
Instead of Trading, Build Trading Infrastructure:

Trading Tools/Indicators: Sell shovels during gold rush ($50-500/month per customer)
Backtesting Services: Charge dreamers to test their strategies ($100-1000/project)
Trading Education: Sell courses to hopefuls ($500-5000 per course)
Exchange APIs/Wrappers: Developers need these ($30-200/month)

Real Opportunities in Crypto (Without Trading):

MEV Research: Requires deep blockchain knowledge, not TA
DeFi Development: Build protocols, earn fees
Smart Contract Auditing: $50-200k per audit
Blockchain Infrastructure: Nodes, indexers, oracles

For Passive Income:

Buy and Hold BTC/ETH: 50-100% returns over 3-5 years
Index Funds: 10-12% annual average
Build SaaS: Recurring revenue that actually scales

Repository Contents (For Archaeological Purposes)
/src
  /strategies      # 5 failed attempts at finding edge
  /backtesting     # Actually well-built, just proved nothing works
  /execution       # Production-ready code for a non-viable strategy
  /risk_management # Properly built risk system for losing money safely
  /data_collection # Professional-grade data pipeline for useless data
Lessons Learned (Worth the 300 Hours)

Technical Analysis is astrology for men with spreadsheets
If a strategy worked, it wouldn't be on YouTube
Backtests lie, even when done correctly
The house always wins (be the exchange, not the trader)
Time in market > Timing the market

For My Friends Reading This
Don't try to "fix" this project. It's not broken - the entire concept is flawed.
If you want to make money in crypto/finance:

Build tools for traders (they'll pay for hope)
Get a job at a trading firm (use their capital)
Buy and hold (boring but works)
Build literally anything else (SaaS, consulting, whatever)

Performance Metrics Across All Strategies
StrategyAnnual ReturnSharpeMax DDVerdictMomentum0.75%0.1243%Complete FailurePairs Trading5.66%0.894.2%Too RareFunding Arb4-6%0.6-0.8<1%No OpportunitySimple Trend7.6%0.824.78%Not Worth ItMulti-Frame3.6%0.0928.79%DisasterS&P 50012%1.020%Just Buy This
Final Words
This repository stands as a monument to the death of retail algorithmic trading. It's not a failure of implementation - it's proof that the game is rigged.
300 hours of work. 5 strategies. 0 profits.
The edge doesn't exist anymore. It's been arbitraged away by institutions with better resources than you'll ever have.
Do yourself a favor: Delete this repo, buy some Bitcoin, and build something people actually want.

Repository Status: ☠️ DECEASED
Time of Death: 2024
Cause: Reality
Next Steps: Build something useful

"The market can remain irrational longer than you can remain solvent." - Keynes
"But more importantly, the market can remain efficient longer than you can find an edge." - Me, after 300 hours
Contact
If you want to discuss why this failed or explore actual profitable development opportunities:

Focus on B2B SaaS
Build automation tools
Create value, don't chase alpha

License
MIT License - Take this code and learn from my mistakes. But seriously, don't trade with it.

## The Hidden Section for True Believers

If your friends STILL want to try trading after reading this, add this section:

```markdown
## Appendix: If You MUST Trade

Since some of you will ignore all evidence and try anyway, here's the truth:

### The Only "Strategies" That Sometimes Work for Retail:
1. **Buy Bitcoin, hold 4+ years** (not really trading)
2. **Sell options to WSB degenerates** (picking up pennies in front of steamroller)
3. **Inside information** (illegal, don't do this)
4. **Get extremely lucky once** (not repeatable)

### The Minimum Requirements for Algo Trading:
- $100k+ capital (to survive drawdowns)
- Sub-5ms execution (impossible from home)
- 0% fees (need institutional accounts)
- Full-time dedication (it's a job, not passive income)
- Advanced mathematics degree (helpful but not sufficient)

### Red Flags That Your Strategy Won't Work:
- You found it on YouTube/Reddit/Twitter
- Backtests show >30% annual returns
- Win rate >60% with retail execution
- It uses common indicators (RSI, MACD, etc.)
- It worked great from 2020-2021 (everything did)
- You think you've found something "they" don't want you to know

Remember: If you've found a profitable strategy, why would you share it?
````
