#!/usr/bin/env python3
"""Daily-bar paper trading; next-session OPEN fills, no broker integration."""
import csv
import io
import json
import math
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

STATE = Path("paper/state.json")
REPORT = Path("paper/latest_report.json")
SYMBOLS = ["AAPL.US", "MSFT.US", "NVDA.US", "AMD.US", "SPY.US"]
START_CASH = 500.0
RISK_EUR = 10.0
DAILY_LOSS_LIMIT_EUR = 15.0
MAX_POSITION_EUR = 150.0
SIDE_COST_RATE = 0.001
MAX_MARKET_AGE_DAYS = 5

def get_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "ai-daytrader-paper/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)

def fetch_usd_eur():
    data = get_json("https://api.frankfurter.dev/v1/latest?base=USD&symbols=EUR")
    rate = float(data["rates"]["EUR"])
    fx_date = date.fromisoformat(data["date"])
    age = (datetime.now(timezone.utc).date() - fx_date).days
    if not math.isfinite(rate) or not 0 <= age <= 4:
        raise RuntimeError("Missing/stale USD-EUR FX data")
    if not 0.5 < rate < 1.5:
        raise RuntimeError("Implausible USD-EUR FX data")
    return rate, str(fx_date)

def fetch_bars(symbol):
    request = urllib.request.Request(
        "https://stooq.com/q/d/l/?s=" + symbol.lower() + "&i=d",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        rows = csv.DictReader(io.StringIO(response.read().decode("utf-8")))
        bars = []
        for row in rows:
            try:
                bar = {"date": row["Date"], **{k.lower(): float(row[k]) for k in ("Open", "High", "Low", "Close")}}
                if all(math.isfinite(bar[k]) and bar[k] > 0 for k in ("open", "high", "low", "close")):
                    bars.append(bar)
            except (KeyError, TypeError, ValueError):
                continue
    if len(bars) < 26 or any(bars[i]["date"] >= bars[i+1]["date"] for i in range(len(bars)-1)):
        raise RuntimeError("Invalid history for " + symbol)
    return bars

def mean(values):
    return sum(values) / len(values)

def crossed_up(bars):
    """Use only bars BEFORE the execution day."""
    prior = [b["close"] for b in bars[:-1]]
    return mean(prior[-5:]) > mean(prior[-20:]) and mean(prior[-6:-1]) <= mean(prior[-21:-1])

def below_sma20(bars):
    prior = [b["close"] for b in bars[:-1]]
    return prior[-1] < mean(prior[-20:])

def equity(state, close_eur):
    pos = state["position"]
    return state["cash_eur"] + (pos["shares"] * close_eur[pos["symbol"]] if pos else 0)

def sell(state, symbol, shares, fill_price, day, reason, actions):
    proceeds = shares * fill_price * (1 - SIDE_COST_RATE)
    pnl = proceeds - state["position"]["entry_total_eur"]
    state["cash_eur"] += proceeds
    state["position"] = None
    state["trades"].append({"date": day, "side": "SELL", "symbol": symbol, "shares": shares,
                            "price_eur": round(fill_price, 4), "realized_pnl_eur": round(pnl, 4), "reason": reason})
    actions.append("SELL " + symbol + " (" + reason + ")")

def run_day(state, market, fx_rate):
    day = next(iter(market.values()))[-1]["date"]
    opens = {s: b[-1]["open"] * fx_rate for s, b in market.items()}
    closes = {s: b[-1]["close"] * fx_rate for s, b in market.items()}
    lows = {s: b[-1]["low"] * fx_rate for s, b in market.items()}
    actions = []
    start_equity = state.get("last_equity_eur", START_CASH)
    position = state["position"]
    if position:
        symbol = position["symbol"]
        stop = position["stop_eur"]
        if opens[symbol] <= stop:
            sell(state, symbol, position["shares"], opens[symbol], day, "gap_below_stop", actions)
        elif below_sma20(market[symbol]):
            sell(state, symbol, position["shares"], opens[symbol], day, "previous_close_below_sma20", actions)
        elif lows[symbol] <= stop:
            sell(state, symbol, position["shares"], stop, day, "intraday_stop_approximation", actions)
    # Daily loss gate based on mark-to-market, not just realized P&L.
    current_equity = equity(state, closes)
    if state["position"] is None and current_equity - start_equity > -DAILY_LOSS_LIMIT_EUR:
        for symbol in SYMBOLS:
            if not crossed_up(market[symbol]):
                continue
            price = opens[symbol]
            stop = price * 0.98
            shares = int(min(MAX_POSITION_EUR / price, RISK_EUR / (price - stop),
                             state["cash_eur"] / (price * (1 + SIDE_COST_RATE))))
            if shares < 1:
                continue
            total = shares * price * (1 + SIDE_COST_RATE)
            state["cash_eur"] -= total
            state["position"] = {"symbol": symbol, "shares": shares, "entry_total_eur": total,
                                 "stop_eur": stop, "entry_date": day}
            state["trades"].append({"date": day, "side": "BUY", "symbol": symbol, "shares": shares,
                                    "price_eur": round(price, 4)})
            actions.append("BUY " + str(shares) + " " + symbol)
            # Today's intraday low is NOT used to stop a new position because
            # daily OHLC does not reveal whether low happened before or after entry.
            break
    end_equity = equity(state, closes)
    state["cash_eur"] = round(state["cash_eur"], 6)
    state["last_equity_eur"] = round(end_equity, 6)
    state["last_processed_date"] = day
    return actions, end_equity, start_equity

def main():
    fx_rate, fx_date = fetch_usd_eur()
    market = {symbol: fetch_bars(symbol) for symbol in SYMBOLS}
    dates = {bars[-1]["date"] for bars in market.values()}
    if len(dates) != 1:
        raise RuntimeError("Different trading dates in feeds; refusing to simulate")
    market_day = dates.pop()
    age = (datetime.now(timezone.utc).date() - date.fromisoformat(market_day)).days
    if age < 0 or age > MAX_MARKET_AGE_DAYS:
        raise RuntimeError("Stale or future market data")
    state = json.loads(STATE.read_text()) if STATE.exists() else {
        "cash_eur": START_CASH, "position": None, "trades": [],
        "last_processed_date": None, "last_equity_eur": START_CASH}
    if state["last_processed_date"] == market_day:
        print("Already processed " + market_day)
        return
    if state["last_processed_date"] and state["last_processed_date"] > market_day:
        raise RuntimeError("Market date older than last processed date")
    actions, end_equity, start_equity = run_day(state, market, fx_rate)
    report = {"generated_utc": datetime.now(timezone.utc).isoformat(),
              "market_date": market_day, "mode": "PAPER_ONLY",
              "usd_eur_rate": fx_rate, "fx_rate_date": fx_date,
              "cash_eur": round(state["cash_eur"], 2), "equity_eur": round(end_equity, 2),
              "day_pnl_eur": round(end_equity - start_equity, 2),
              "pnl_since_start_eur": round(end_equity - START_CASH, 2),
              "position": state["position"], "actions": actions, "trades_count": len(state["trades"]),
              "limitations": ["Daily OHLC is not intraday data; stop timing approximate.",
                              "FX reference rates are not historical transaction rates.",
                              "Daily loss limit is an entry gate, not a guaranteed loss cap.",
                              "No validated backtest or live execution; paper only."]}
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2) + "\n")
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
