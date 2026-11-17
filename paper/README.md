# Paper Trading v1 (experimental)

This branch adds an **unvalidated daily-bar simulation**. It never connects to a broker.

- Universe: AAPL, MSFT, NVDA, AMD, SPY (Stooq daily USD closes).
- Entry: 5-day SMA crosses above 20-day SMA; one long position at a time.
- Exit: close below 20-day SMA or below a fixed 2% stop (evaluated only on daily close).
- Start capital EUR 500; target risk EUR 10 per trade; daily realized-loss gate EUR 15; max position EUR 150.
- Integer shares only; 0.1% cost proxy on entry and exit.
- Persisted files: `paper/state.json` and `paper/latest_report.json`.

**Major limitations:** same-close signal and execution introduces look-ahead bias; no intraday stops or realistic gap execution, stale daily data possible, FX rate must be maintained. This is a software smoke-test, **not** an honest performance backtest or live-ready strategy. Losses can exceed the intended stop.

### Setup
Create GitHub Actions repository variable `USD_EUR` with a **verified current** EUR value of one USD (e.g. not hardcoded in code). Enable Actions for this branch and manually dispatch the workflow. Scheduled workflows only run automatically when the workflow is present on the repository's **default branch**; merge after review if scheduling is desired. Workflow runs on weekdays at 23:30 UTC and may be delayed by GitHub.

Next: replace same-close execution with next-session open execution; use adjusted OHLC data, proper FX historical rates, backtest with costs, add tests, and validate risk controls before relying on results.
