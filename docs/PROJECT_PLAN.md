# AI Daytrader — Strategie, Status und Roadmap

Stand: 2026-11-12. Diese Dokumentation beschreibt die vereinbarten Projektziele und den im Repository geprüften technischen Ist-Zustand. **Noch nicht implementierte Funktionen sind explizit als geplant markiert.**

## Ziel

Regelbasierten US-Aktien-Daytrading-Bot entwickeln, zunächst als nachvollziehbarer Scanner, danach als realistischen Paper-Trader mit protokollierter Performance. **Keine Echtgeldorders, bevor belastbare Tests und Risiko-Kontrollen vorliegen.**

## Aktueller Ist-Zustand (geprüft)

- Repository: `VinceT4Z4/ai-daytrader`, Hauptbranch `main`.
- `scanner.py`: holt mit `yfinance` 5-Minuten-Kerzen über fünf Tage und scannt `AAPL, MSFT, NVDA, AMD, MU, AMZN, SPY`.
- Einfache Opening-Range-Breakout-Logik: Hoch/Tief der ersten drei 5-Minuten-Kerzen; Long-Signal bei neuem Überschreiten des Hochs, Kurs über VWAP und Volumen > 1,5 × Referenzvolumen.
- Signale: `WATCH_LONG`, `HISTORICAL_SIGNAL`, `NO_TRADE`, `DATA_ERROR`.
- Scanner-Ausgabe: `reports/latest.json`; außerdem Ausgabe im Workflow-Log.
- GitHub Actions `.github/workflows/paper-trader.yml`: nur manuell über `workflow_dispatch`, installiert Python 3.11, pandas und yfinance, führt Scanner aus und lädt Bericht als Artifact `scan-report` hoch.
- Ein GitHub-Workflow-Lauf vom 2026-11-12 um 15:24 UTC war erfolgreich. **Ein erfolgreicher Workflow bedeutet weder profitables Trading noch valide Handelssignale.**
- Keine echte simulierte Orderausführung, keine Gebühren/Slippage, kein Portfolio-Ledger, keine laufende P&L, keine Broker-Anbindung, keine automatisierte Ausführung.

## Grundparameter (vereinbarter Ausgangspunkt)

| Parameter | Wert |
| --- | --- |
| Virtuelles Startkapital | 500 EUR |
| Risiko je Trade | 10 EUR / 2 % |
| Tagesverlustlimit | 15 EUR |
| Modus | `SCAN_ONLY` / keine Orders |
| Gehandelte Instrumente | US-Aktien/ETF als erste Scan-Watchlist |
| Priorität | Risikokontrolle und belastbare Nettorendite statt schöner Signale |

**Achtung:** Derzeit berechnet `scanner.py` Aktienanzahlen mit USD-Preisen gegen EUR-Kapital, ohne FX-Umrechnung. `max_whole_shares_illustrative` ist daher **keine korrekte positionsgrößenbasierte Empfehlung**. Die Tagesverlustgrenze von 15 EUR ist ein Berichtsfeld, keine technisch durchgesetzte Sperre.

## Bekannte methodische Probleme

1. **Falsche historische Session:** Die Auswahl erlaubt bei unvollständiger letzter Session die ältere Session (und markiert sie dann historisch). Das ist transparent, aber keine Echtzeit-Handelsfähigkeit.
2. **Erste 15 Minuten:** Opening Range wird anhand der ersten drei vorhandenen Balken, nicht zwingend anhand verifizierter regulärer NYSE/Nasdaq-Handelsminuten 09:30–09:45 ET, gebildet. Pre-/Postmarket, fehlende Kerzen und Marktfeiertage müssen sauber geprüft werden.
3. **VWAP:** Berechnet über die gewählte Tagesmenge, aber nicht gesondert gegenüber regulären Session-Zeiten abgesichert.
4. **Noch laufende Kerze:** Das Script verwirft pauschal die letzte Kerze, auch wenn die jüngste Kerze bereits abgeschlossen sein kann.
5. **Keine simulierten Fills:** Ohne tatsächliche Einstiege, Ausstiege, Stops, Gebühren, Spread und Slippage ist keine Performance messbar.
6. **Keine Reproduzierbarkeit:** Eingefrorene Daten, Tests, Versionsstände und deterministische Backtests fehlen.
7. **Datenqualität:** yfinance kann verzögert, unvollständig oder korrigiert sein; nicht als Broker-Execution-Feed behandeln.

## Implementierungs-Roadmap

### Phase 1: Daten und Signalqualität
- [ ] Exchange-Zeitzone `America/New_York`, offizielle RTH-Session und Handelskalender explizit prüfen
- [ ] Nur endgültig abgeschlossene 5-Minuten-Bars verarbeiten
- [ ] Fehlende/duplizierte Bars, Vor-/Nachbörse, Splits, Ausfälle und stale Daten erkennen
- [ ] Opening-Range- und VWAP-Berechnung mit Fixture-Tests absichern
- [ ] Einheitliche Signalausgabe mit Signalzeit, Datums-/Zeitzoneninformationen und Diagnostik
- [ ] EUR/USD-Konversion und Positionsgrößenformel konsistent implementieren

### Phase 2: Echter Paper-Trader (ohne Echtgeld)
- [ ] Simulierter Entry nur nach Schluss einer bestätigten Signalkerze
- [ ] Deterministische Fill-Konvention, Spread, Slippage und Gebühren
- [ ] Stops, Tagesverlustsperre, Gesamtposition-/Kapitalgrenzen, maximale offene Trades
- [ ] Ledger für Orders, Trades, realisierte/unrealisierte P&L, Equity Curve und Drawdown
- [ ] Trades und Entscheidungen nachvollziehbar speichern, Re-Run idempotent gestalten
- [ ] Kill-Switch und Sicherung gegen doppelte Entries

### Phase 3: Evaluation
- [ ] Chronologischer Backtest, Out-of-Sample-Test und Walk-Forward-Analyse
- [ ] Nettorendite nach Kosten, Winrate, Profit Factor, durchschnittliches R, Max Drawdown und Sample Size messen
- [ ] Gegen Buy-and-Hold bzw. passende Benchmarks vergleichen
- [ ] Robustheit nach Volatilitätsregimen, Spread, Slippage und parametrischen Veränderungen prüfen
- [ ] Keine Strategieauswahl allein anhand des besten historischen Ergebnisses

### Phase 4: Betrieb
- [ ] GitHub Actions Zeitplan mit US-Sommer-/Winterzeit, Börsenzeiten und Rate Limits entwerfen
- [ ] Maschinenlesbare Reports und menschenlesbare Tageszusammenfassung erzeugen
- [ ] Fehlerbenachrichtigungen und datenqualitätsbezogene Alerts
- [ ] Erst nach dokumentierter Eignung: Broker-Paper-API separat evaluieren
- [ ] **Echtgeld-Handel nur nach expliziter, separater Entscheidung und zusätzlichen Sicherheitsmaßnahmen**

## Entwicklungsregeln

- Niemals vergangene Signale als aktuell handelbare Gelegenheiten ausgeben.
- Ein grüner GitHub-Workflow ist nur ein Technikcheck, kein Profitabilitätsbeweis.
- Vor Funktionsänderungen Tests schreiben; Ergebnisse nachvollziehbar dokumentieren.
- Keine API-Keys oder Broker-Secrets in Code, Issues, Logs oder Reports einchecken.
- Am bestehenden funktionsfähigen `main` keine ungetesteten Änderungen vornehmen; Änderungen vorzugsweise über Pull Requests.

## Nächster sinnvoller Schritt

**Phase 1 zuerst:** Session-Validierung und FX-/Sizing-Bug mit Unit-Tests beheben. Anschließend einen echten, deterministischen Paper-Trading-Simulator erstellen — nicht direkt Live-Trading aktivieren.
