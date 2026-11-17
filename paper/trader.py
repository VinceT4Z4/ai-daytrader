#!/usr/bin/env python3
"""Daily-bar paper trader. Simulation only; never sends broker orders."""
import csv
import io
import json
import math
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

STATE = Path("paper/state.json")
REPORT = Path("paper/latest_report.json")
SYMBOLS = ["AAPL.US", "MSFT.US", "NVDA.US", "AMD.US", "SPY.US"]
START_CASH = 500.0
RISK_EUR = 10.0
DAILY_LOSS_LIMIT_EUR = 15.0
MAX_POSITION_EUR = 150.0
ROUND_TRIP_COST_RATE = 0.002  # 0.1% each side, proxy for spread/slippage/fees
USD_EUR = float(os.environ.get("USD_EUR", "0"))
if USD_EUR <= 0:
    raise RuntimeError("Set USD_EUR to a current, verified USD-to-EUR rate; do not assume 1:1.")

def prices(symbol):
    url = "https://stooq.com/q/d/l/?s=" + symbol.lower() + "&i=d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read().decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(raw)))
    valid = []
    for row in rows:
        try:
            close = float(row["Close"])
            if close > 0 and math.isfinite(close):
                valid.append({"date": row["Date"], "close": close})
        except (KeyError, ValueError, TypeError):
            continue
    if len(valid) < 25:
        raise RuntimeError(f"Insufficient price history for {symbol}")
    return valid

def sma(vals, n):
    return sum(vals[-n:]) / n

def main():
    now = datetime.now(timezone.utc).isoformat()
    market = {s: prices(s) for s in SYMBOLS}  # fail closed if any feed is unavailable
    dates = {bars[-1]["date"] for bars in market.values()}
    if len(dates) != 1:
        raise RuntimeError("Price feeds have different last trading dates; no trades executed")
    date = dates.pop()
    state = json.loads(STATE.read_text()) if STATE.exists() else {
        "cash_eur": START_CASH, "position": None, "trades": [],
        "last_processed_date": None, "day_start_equity_eur": START_CASH,
    }
    if state["last_processed_date"] == date:
        print(f"Already processed {date}; no duplicate execution")
        return
    closes = {s: market[s][-1]["close"] * USD_EUR for s in SYMBOLS}
    position = state["position"]
    start_equity = state["cash_eur"] + (position["shares"] * closes[position["symbol"]] if position else 0)
    state["day_start_equity_eur"] = round(start_equity, 4)
    actions = []
    # This is a simplified end-of-day close-price simulation, NOT a fill achievable
    # after observing the same close. Results are optimistic and not a backtest.
    if position:
        s = position["symbol"]
        bars = market[s]
        vals = [b["close"] for b in bars]
        exit_signal = vals[-1] < sma(vals, 20) or closes[s] <= position["stop_eur"]
        if exit_signal:
            proceeds = position["shares"] * closes[s] * (1 - ROUND_TRIP_COST_RATE / 2)
            state["cash_eur"] += proceeds
            pnl = proceeds - position["entry_total_eur"]
            state["trades"].append({"date": date, "symbol": s, "side": "SELL", "shares": position["shares"], "price_eur": round(closes[s], 4), "realized_pnl_eur": round(pnl, 4)})
            actions.append(f"SELL {s}: simulated P&L {pnl:.2f} EUR")
            state["position"] = None
    realized_today = sum(t.get("realized_pnl_eur", 0) for t in state["trades"] if t["date"] == date)
    if state["position"] is None and realized_today > -DAILY_LOSS_LIMIT_EUR:
        for s in SYMBOLS:
            vals = [b["close"] for b in market[s]]
            if sma(vals, 5) > sma(vals, 20) and sma(vals[:-1], 5) <= sma(vals[:-1], 20):
                price = closes[s]
                stop = price * 0.98
                shares = int(min(MAX_POSITION_EUR / price, RISK_EUR / (price - stop),
                                 state["cash_eur"] / (price * (1 + ROUND_TRIP_COST_RATE / 2))))
                if shares < 1:
                    continue
                total = shares * price * (1 + ROUND_TRIP_COST_RATE / 2)
                state["cash_eur"] -= total
                state["position"] = {"symbol": s, "shares": shares, "entry_total_eur": total,
                                     "stop_eur": round(stop, 4), "entry_date": date}
                state["trades"].append({"date": date, "symbol": s, "side": "BUY", "shares": shares, "price_eur": round(price, 4)})
                actions.append(f"BUY {shares} {s} (simulation)")
                break
    position = state["position"]
    equity = state["cash_eur"] + (position["shares"] * closes[position["symbol"]] if position else 0)
    state["cash_eur"] = round(state["cash_eur"], 4)
    state["last_processed_date"] = date
    report = {"generated_utc": now, "market_date": date, "mode": "PAPER_ONLY",
              "cash_eur": round(state["cash_eur"], 2), "equity_eur": round(equity, 2),
              "pnl_since_start_eur": round(equity - START_CASH, 2),
              "position": position, "actions": actions,
              "trades_count": len(state["trades"]),
              "warnings": ["End-of-day hindsight fills: not executable live prices.",
                           "Daily close data: intraday stops and gap losses not simulated.",
                           "USD_EUR must be supplied externally and updated.",
                           "No brokerage integration; results do not prove profitability."]}
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2) + "\n")
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
