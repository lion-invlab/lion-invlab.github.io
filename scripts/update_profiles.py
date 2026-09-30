import json, os, time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import yfinance as yf

INPUT_FILE='data/sp500_volatility.json'
OUTPUT_FILE='data/company_profiles.json'
MAX_AGE_DAYS=7
WORKERS=4

FIELDS={
 'company_name':'longName','sector':'sector','industry':'industry','country':'country','city':'city','state':'state',
 'website':'website','business_summary':'longBusinessSummary','market_cap':'marketCap','trailing_pe':'trailingPE',
 'forward_pe':'forwardPE','trailing_eps':'trailingEps','roe':'returnOnEquity','gross_margin':'grossMargins',
 'free_cash_flow':'freeCashflow','revenue':'totalRevenue','revenue_growth':'revenueGrowth','operating_margin':'operatingMargins',
 'profit_margin':'profitMargins','roa':'returnOnAssets','debt_to_equity':'debtToEquity','total_cash':'totalCash',
 'total_debt':'totalDebt','price_to_book':'priceToBook','peg_ratio':'pegRatio','ev_to_ebitda':'enterpriseToEbitda'
}


def val(info,k):
    v=info.get(k)
    return v if isinstance(v,(int,float)) and v is not None else None

def pctval(info,k):
    v=val(info,k)
    return v*100 if v is not None else None

def fetch_one(ticker, existing):
    now=datetime.now(timezone.utc)
    old=existing.get(ticker,{})
    try:
        if old.get('updated_at'):
            ts=datetime.fromisoformat(old['updated_at'].replace('Z','+00:00'))
            if (now-ts).total_seconds() < MAX_AGE_DAYS*86400:
                return ticker, old, 'cached'
        info=yf.Ticker(ticker).get_info()
        out={'ticker':ticker,'source':'Yahoo Finance','updated_at':now.isoformat()}
        for dst,src in FIELDS.items():
            if src in ('returnOnEquity','grossMargins','revenueGrowth','operatingMargins','profitMargins','returnOnAssets'):
                out[dst]=pctval(info,src)
            elif src in ('marketCap','trailingPE','forwardPE','trailingEps','freeCashflow','totalRevenue','debtToEquity','totalCash','totalDebt','priceToBook','pegRatio','enterpriseToEbitda'):
                out[dst]=val(info,src)
            else:
                out[dst]=info.get(src)
        # Do not invent competitive advantages. Keep an explicit status until 10-K based extraction is added.
        out['competitive_advantages']='目前先保留公開公司描述；競爭優勢需依最新10-K／公司公開資料逐家公司整理，避免把推測當成事實。'
        return ticker,out,'updated'
    except Exception as e:
        print(f'{ticker}: {e}')
        return ticker, old, 'error'

def main():
    with open(INPUT_FILE,encoding='utf-8') as f: d=json.load(f)
    tickers=[x['yahoo_ticker'] for x in d.get('stocks',[]) if x.get('yahoo_ticker')]
    existing={}
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE,encoding='utf-8') as f: existing=json.load(f)
        except Exception: existing={}
    result=dict(existing)
    counts={'updated':0,'cached':0,'error':0}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures=[ex.submit(fetch_one,t,existing) for t in tickers]
        for fut in as_completed(futures):
            t,obj,status=fut.result(); result[t]=obj; counts[status]+=1
    with open(OUTPUT_FILE,'w',encoding='utf-8') as f: json.dump(result,f,ensure_ascii=False,indent=2)
    print('Profiles:',len(result),counts)

if __name__=='__main__': main()
