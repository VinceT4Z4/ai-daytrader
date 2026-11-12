import json, math, os
from datetime import datetime, timezone
import pandas as pd
import yfinance as yf

CAPITAL=500.0
RISK=CAPITAL*0.02
TICKERS=['AAPL','MSFT','NVDA','AMD','MU','AMZN','SPY']
results=[]
for symbol in TICKERS:
    try:
        df=yf.download(symbol,period='5d',interval='5m',auto_adjust=True,progress=False,threads=False)
        if df.empty: raise ValueError('no data')
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        df=df.dropna(subset=['Open','High','Low','Close','Volume'])
        # Latest US trading session, timestamps provided by Yahoo in exchange-local zone.
        dates=df.index.date
        sessions=[(d,df.loc[dates==d].copy()) for d in sorted(set(dates),reverse=True)]
        valid=[(d,bars) for d,bars in sessions if len(bars)>=20]
        if not valid: raise ValueError('no session with 20 intraday bars; counts='+str([(str(d),len(b)) for d,b in sessions]))
        session_date,day=valid[0]
        is_latest_session=(session_date==max(dates))
        # Only use complete historical bars; the newest bar may be in progress.
        day=day.iloc[:-1]
        if len(day)<19: raise ValueError('not enough completed bars')
        opening=day.iloc[:3]
        high=float(opening.High.max())
        low=float(opening.Low.min())
        typical=(day.High+day.Low+day.Close)/3
        volume=day.Volume.astype(float)
        vwap=float((typical*volume).sum()/volume.sum()) if volume.sum()>0 else math.nan
        last=float(day.Close.iloc[-1]); prev=float(day.Close.iloc[-2]); vol=float(volume.iloc[-1]); avg=float(volume.iloc[-19:-1].mean())
        confirmed=bool(last>high and prev<=high and last>vwap and vol>1.5*avg and avg>0)
        stop=low
        per_share=last-stop
        shares=math.floor(min(CAPITAL/last,RISK/per_share)) if confirmed and per_share>0 else 0
        results.append({'symbol':symbol,'session':str(session_date),'historical_session':not is_latest_session,'last_price_usd':round(last,3),'opening_high_usd':round(high,3),'vwap_usd':round(vwap,3),'volume_ratio':round(vol/avg,2) if avg else None,'signal':'WATCH_LONG' if confirmed and shares>0 and is_latest_session else ('HISTORICAL_SIGNAL' if confirmed and shares>0 else 'NO_TRADE'),'max_whole_shares_illustrative':shares if is_latest_session else 0,'note':'Signals only; no orders. EUR capital vs USD shares requires FX conversion before sizing.'})
    except Exception as e:
        results.append({'symbol':symbol,'signal':'DATA_ERROR','reason':str(e)[:160]})
report={'generated_utc':datetime.now(timezone.utc).isoformat(),'mode':'SCAN_ONLY','virtual_capital_eur':CAPITAL,'risk_per_trade_eur':RISK,'daily_loss_limit_eur':15,'warning':'No broker, no simulated execution, no P&L. Delayed/incomplete data possible. USD share sizing is illustrative only.','results':results}
os.makedirs('reports',exist_ok=True)
with open('reports/latest.json','w') as f: json.dump(report,f,indent=2)
print(json.dumps(report,indent=2))
