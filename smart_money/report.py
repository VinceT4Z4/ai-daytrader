#!/usr/bin/env python3
"""Summarize independently sourced investor disclosures; read-only, no orders."""
import json
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

SOURCE = Path("smart_money/events_2026_q3.json")
HOLDINGS = Path("portfolio/holdings_snapshot.json")
OUTPUT = Path("smart_money/latest_report.json")
ALIASES = {"MU": "Micron Technology", "MSFT": "Microsoft", "NVDA": "NVIDIA",
           "ASML": "ASML", "AMD": "AMD", "GOOGL": "Alphabet (A)"}

def build_report():
    source = json.loads(SOURCE.read_text())
    holdings = json.loads(HOLDINGS.read_text())
    owned = {p["name"] for p in holdings["positions"]}
    quarter_end = date.fromisoformat(source["quarter_end"])
    age = (datetime.now(timezone.utc).date() - quarter_end).days
    if age < 0:
        raise ValueError("Future quarter end")
    grouped = defaultdict(list)
    for event in source["events"]:
        if not event.get("source", "").startswith("https://"):
            raise ValueError("Missing source URL")
        grouped[event["ticker"]].append(event)
    overlaps = []
    for ticker, events in sorted(grouped.items()):
        name = ALIASES.get(ticker, ticker)
        if name in owned:
            actions = {e["action"] for e in events}
            overlaps.append({"ticker": ticker, "holding": name, "events": events,
                             "interpretation": "MIXED" if len(actions) > 1 else next(iter(actions)),
                             "trade_signal": "NONE"})
    return {"generated_utc": datetime.now(timezone.utc).isoformat(),
            "quarter_end": source["quarter_end"], "disclosure_age_days": age,
            "mode": "RESEARCH_ONLY", "overlaps": overlaps,
            "warnings": ["This is a manually curated snapshot, NOT an automated live SEC feed.",
                         "13F holdings may be delayed up to 45 days and omit shorts and many instruments.",
                         "A manager's quarterly change is not a buy/sell recommendation.",
                         "No orders, no impact on paper-trading strategy."]}

if __name__ == "__main__":
    report = build_report()
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"overlap_count": len(report["overlaps"]),
                      "tickers": [x["ticker"] for x in report["overlaps"]]}, indent=2))
