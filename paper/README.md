# AI Daytrader — experimental paper trading

## Safety and scope
- **NO BROKER, NO REAL ORDERS.** Real holdings are a read-only watchlist snapshot.
- EUR 500 virtual cash; EUR 10 intended stop distance risk; EUR 15 daily loss entry gate; EUR 150 max nominal per position.
- Five paper-trading symbols: AAPL, MSFT, NVDA, AMD, SPY.
- 5/20-day simple moving-average crossover on the **previous session**; simulate entry at **next session open**.
- Exit at next open on prior close below SMA20, or approximate intraday stop; gaps below stop exit at open.
- Integer shares, 0.1% cost per side, max one position.
- Stooq daily OHLC and Frankfurter/ECB reference FX; fail closed on stale/missing data.
- Real watchlist: `portfolio/holdings_snapshot.json`; `portfolio/watchlist.py` produces a separate read-only report.

## Running
`python -m unittest discover -s tests -v`
`python paper/trader.py`
`python portfolio/watchlist.py`

GitHub Actions daily workflow is scheduled 23:30 UTC weekdays. GitHub only schedules workflows on the default branch, so **this feature branch will not auto-run on a schedule** until merged. Runs may be delayed; weekends/holidays skip duplicate market dates. Workflow requires Actions write permission to commit reports/state; GitHub repository settings may block that.

## Known limitations
- Not a daytrading strategy: **daily-bar swing-trading prototype**.
- Intraday OHLC order unknown. Same-day stop for newly opened position is deliberately not simulated.
- Stops, EUR 10 risk and EUR 15 daily gate **cannot guarantee** maximum realized loss.
- Reference FX applied to all historic OHLC of the current session, not transaction-specific historical FX.
- No robust backtest, no walk-forward validation, no real broker execution, no dividend/corporate-action audit, no benchmark.
- Do not interpret generated actions as investment recommendations.

Next steps: verify CI, instrument IDs for ETFs, add realistic walk-forward backtest and benchmark, then evaluate any move to higher-frequency trading with licensed market data.
