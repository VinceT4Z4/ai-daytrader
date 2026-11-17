import unittest
from paper.trader import crossed_up, below_sma20, run_day

def bars(prior, open_, low, close, date="2026-11-17"):
    history = [{"date": f"2026-10-{i+1:02d}", "open": v, "high": v,
                "low": v, "close": v} for i, v in enumerate(prior)]
    return history + [{"date": date, "open": open_, "high": max(open_, close),
                       "low": low, "close": close}]

def state():
    return {"cash_eur": 500.0, "position": None, "trades": [],
            "last_processed_date": None, "last_equity_eur": 500.0}

class PaperTests(unittest.TestCase):
    def test_signal_ignores_execution_day_close(self):
        prior = [100.0] * 20 + [101.0]
        a = bars(prior, 100, 90, 1)
        b = bars(prior, 100, 90, 1000)
        self.assertEqual(crossed_up(a), crossed_up(b))

    def test_no_duplicate_trade_without_signal(self):
        data = {"AAPL.US": bars([100.0]*25, 100, 99, 100)}
        s = state()
        actions, end, start = run_day(s, data, 1.0)
        self.assertEqual(actions, [])
        self.assertEqual(end, 500.0)

    def test_gap_stop_uses_open_not_stop(self):
        s = state()
        s["cash_eur"] = 400.0
        s["position"] = {"symbol": "AAPL.US", "shares": 1,
                         "entry_total_eur": 100.1, "stop_eur": 98.0}
        data = {"AAPL.US": bars([100.0]*25, 90, 85, 89)}
        actions, end, _ = run_day(s, data, 1.0)
        self.assertIsNone(s["position"])
        self.assertEqual(s["trades"][-1]["reason"], "gap_below_stop")
        self.assertAlmostEqual(s["trades"][-1]["price_eur"], 90.0)
        self.assertTrue(actions)

    def test_position_size_limited(self):
        # Last five prices cross over last twenty, signal computed before execution bar.
        prior = [100.0]*20 + [101.0]
        data = {"AAPL.US": bars(prior, 100, 99, 101)}
        s = state()
        actions, _, _ = run_day(s, data, 1.0)
        self.assertLessEqual(s["cash_eur"], 500.0)
        if s["position"]:
            self.assertLessEqual(s["position"]["entry_total_eur"], 150.15)

if __name__ == "__main__":
    unittest.main()
