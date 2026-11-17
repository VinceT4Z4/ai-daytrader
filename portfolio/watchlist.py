#!/usr/bin/env python3
"""Read-only portfolio watchlist report; does not change paper-trading positions."""
import csv
import io
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SOURCE = Path("portfolio/holdings_snapshot.json")
TARGET = Path("portfolio/watchlist_report.json")

def latest_close(symbol):
    url = "https://stooq.com/q/d/l/?s=" + symbol.lower() + "&i=d"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        rows = list(csv.DictReader(io.StringIO(response.read().decode("utf-8"))))
    if not rows:
        raise ValueError("No price data")
    row = rows[-1]
    return {"last_market_date": row["Date"], "last_close_native_currency": float(row["Close"])}

def main():
    snapshot = json.loads(SOURCE.read_text())
    results = []
    for holding in snapshot["positions"]:
        result = {"name": holding["name"], "snapshot_value_eur": holding["market_value_eur"],
                  "snapshot_pnl_since_purchase_eur": holding["pnl_since_purchase_eur"],
                  "symbol_candidate": holding["data_symbol_candidate"]}
        if not holding["data_symbol_candidate"]:
            result["status"] = "NEEDS_INSTRUMENT_ID"
        else:
            try:
                result.update(latest_close(holding["data_symbol_candidate"]))
                result["status"] = "QUOTE_AVAILABLE_UNVERIFIED_MAPPING"
            except Exception as exc:
                result["status"] = "QUOTE_UNAVAILABLE"
                result["reason"] = str(exc)[:160]
        results.append(result)
    report = {"generated_utc": datetime.now(timezone.utc).isoformat(),
              "mode": "READ_ONLY_WATCHLIST", "positions": results,
              "warning": "Snapshot values are not updated. Native-currency close quotes cannot be compared with EUR snapshot without share quantities, currency conversion, and verified instrument mapping. No trade signals or orders."}
    TARGET.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"statuses": {x["name"]: x["status"] for x in results}}, indent=2))

if __name__ == "__main__":
    main()
