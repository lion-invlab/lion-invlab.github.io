import json, math, os, time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

CONSTITUENTS_URL = 'https://raw.githubusercontent.com/chinobing/historical_sp500_constituents/main/sp500_constituents.csv'
OUTPUT = Path('data/company_profiles.json')
TEMP = Path('data/company_profiles.tmp.json')
SLEEP_SECONDS = 0.75
SAVE_EVERY = 10
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/140.0 Safari/537.36'


def now():
    return datetime.now(timezone.utc).isoformat()


def num(x):
    try:
        x = float(x)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def txt(x):
    if x is None:
        return None
    x = str(x).strip()
    return x or None


def yahoo_symbol(s):
    return str(s).strip().replace('.', '-')


def load_cache():
    if not OUTPUT.exists():
        return {'meta': {}, 'data_quality': {}, 'companies': {}}
    try:
        with OUTPUT.open(encoding='utf-8') as f:
            d = json.load(f)
        d.setdefault('companies', {})
        return d
    except Exception as e:
        print('Cache read failed:', e)
        return {'meta': {}, 'data_quality': {}, 'companies': {}}


def load_constituents():
    r = requests.get(CONSTITUENTS_URL, headers={'User-Agent': UA}, timeout=30)
    r.raise_for_status()
    from io import StringIO
    df = pd.read_csv(StringIO(r.text))
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
    required = {'symbol', 'security', 'gics_sector'}
    missing = required - set(df.columns)
    if missing:
        raise RuntimeError(f'Missing constituent columns: {sorted(missing)}')
    return df.dropna(subset=['symbol']).drop_duplicates('symbol')


def stmt_value(df, names):
    if df is None or getattr(df, 'empty', True):
        return None, None
    for name in names:
        if name not in df.index:
            continue
        row = df.loc[name]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        for period in row.index:
            v = num(row.loc[period])
            if v is not None:
                return v, str(period)
    return None, None


def yoy(df, names):
    if df is None or getattr(df, 'empty', True):
        return None, None
    for name in names:
        if name not in df.index:
            continue
        row = df.loc[name]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        vals = []
        for period in row.index:
            v = num(row.loc[period])
            if v is not None:
                vals.append((str(period), v))
        if len(vals) >= 2 and vals[1][1] != 0:
            return vals[0][1] / vals[1][1] - 1, f'{vals[0][0]} vs {vals[1][0]}'
    return None, None


def fetch_one(yahoo_ticker, original, fallback_company, fallback_sector):
    t = yf.Ticker(yahoo_ticker)
    info = t.get_info()
    income = t.get_income_stmt(freq='yearly')
    balance = t.get_balance_sheet(freq='yearly')
    cashflow = t.get_cash_flow(freq='yearly')

    revenue, rev_period = stmt_value(income, ['TotalRevenue', 'OperatingRevenue'])
    growth, growth_period = yoy(income, ['TotalRevenue', 'OperatingRevenue'])
    gross, gross_period = stmt_value(income, ['GrossProfit'])
    op_income, op_period = stmt_value(income, ['OperatingIncome', 'OperatingIncomeLoss'])
    net_income, net_period = stmt_value(income, ['NetIncome', 'NetIncomeCommonStockholders'])
    eps, eps_period = stmt_value(income, ['DilutedEPS', 'BasicEPS'])
    ocf, ocf_period = stmt_value(cashflow, ['OperatingCashFlow', 'TotalCashFromOperatingActivities'])
    capex, capex_period = stmt_value(cashflow, ['CapitalExpenditure', 'CapitalExpenditureReported'])
    cash, cash_period = stmt_value(balance, ['CashCashEquivalentsAndShortTermInvestments', 'CashAndCashEquivalents'])
    debt, debt_period = stmt_value(balance, ['TotalDebt'])
    ca, ca_period = stmt_value(balance, ['CurrentAssets'])
    cl, cl_period = stmt_value(balance, ['CurrentLiabilities'])

    return {
        'ticker': original,
        'yahoo_ticker': yahoo_ticker,
        'company': txt(info.get('longName') or info.get('shortName') or fallback_company),
        'sector': txt(info.get('sector') or fallback_sector),
        'industry': txt(info.get('industry')),
        'industry_key': txt(info.get('industryKey')),
        'location': {'city': txt(info.get('city')), 'state': txt(info.get('state')), 'country': txt(info.get('country'))},
        'website': txt(info.get('website')),
        'business': {'summary': txt(info.get('longBusinessSummary')), 'employees': info.get('fullTimeEmployees')},
        'competitive_advantages': None,
        'competitive_advantages_source': None,
        'competitive_advantages_status': '待以最新10-K／公司IR公開資料整理；目前不做推論',
        'financials': {
            'revenue': revenue,
            'revenue_growth_yoy': growth,
            'gross_margin': gross / revenue if revenue and gross is not None else None,
            'operating_margin': op_income / revenue if revenue and op_income is not None else None,
            'net_margin': net_income / revenue if revenue and net_income is not None else None,
            'eps_diluted': eps,
            'roe': num(info.get('returnOnEquity')),
            'roa': num(info.get('returnOnAssets')),
            'operating_cash_flow': ocf,
            'free_cash_flow': ocf + capex if ocf is not None and capex is not None else None,
            'cash': cash,
            'total_debt': debt,
            'debt_to_equity': num(info.get('debtToEquity')),
            'current_ratio': ca / cl if ca is not None and cl not in (None, 0) else None,
        },
        'valuation': {
            'market_cap': num(info.get('marketCap')),
            'trailing_pe': num(info.get('trailingPE')),
            'forward_pe': num(info.get('forwardPE')),
            'price_to_book': num(info.get('priceToBook')),
            'price_to_sales': num(info.get('priceToSalesTrailing12Months')),
            'peg_ratio': num(info.get('pegRatio')),
            'ev_to_ebitda': num(info.get('enterpriseToEbitda')),
            'price_to_fcf': None,
            'dividend_yield': num(info.get('dividendYield')),
        },
        'market': {'current_price': num(info.get('currentPrice') or info.get('regularMarketPrice')), 'currency': txt(info.get('currency'))},
        'periods': {
            'revenue': rev_period, 'revenue_growth': growth_period, 'gross_profit': gross_period,
            'operating_income': op_period, 'net_income': net_period, 'eps': eps_period,
            'operating_cash_flow': ocf_period, 'capex': capex_period, 'cash': cash_period,
            'total_debt': debt_period, 'current_assets': ca_period, 'current_liabilities': cl_period,
        },
        'source': {'profile_and_market': 'Yahoo Finance via yfinance', 'financial_statements': 'Yahoo Finance via yfinance', 'fetched_at_utc': now()}
    }


def save(d):
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with TEMP.open('w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(TEMP, OUTPUT)


def main():
    print('S&P 500 Company Profiles Update')
    constituents = load_constituents()
    data = load_cache()
    companies = data['companies']
    success = failed = 0

    for i, row in enumerate(constituents.itertuples(index=False), 1):
        original = str(row.symbol).strip()
        yahoo_ticker = yahoo_symbol(original)
        try:
            companies[original] = fetch_one(yahoo_ticker, original, str(row.security), str(row.gics_sector))
            success += 1
            print(f'[{i}/{len(constituents)}] OK {original}')
        except Exception as e:
            failed += 1
            print(f'[{i}/{len(constituents)}] FAILED {original}: {e}')
            if original in companies:
                companies[original].setdefault('source', {})['last_update_error'] = str(e)
                companies[original]['source']['last_attempted_at_utc'] = now()

        if i % SAVE_EVERY == 0:
            data['meta'] = {'title': 'S&P 500 Company Profiles', 'updated_at_utc': now(), 'data_type': 'actual', 'demo_data': False,
                            'profile_source': 'Yahoo Finance via yfinance', 'constituent_source': 'GitHub historical_sp500_constituents',
                            'competitive_advantages_note': '競爭優勢不由模型推測；待以10-K／公司IR資料補充並標註來源。'}
            data['data_quality'] = {'constituent_count': len(constituents), 'successful_this_run': success, 'failed_this_run': failed,
                                    'records_in_cache': len(companies), 'coverage': len(companies) / len(constituents)}
            save(data)
            print('checkpoint saved')
        time.sleep(SLEEP_SECONDS)

    data['meta'] = {'title': 'S&P 500 Company Profiles', 'updated_at_utc': now(), 'data_type': 'actual', 'demo_data': False,
                    'profile_source': 'Yahoo Finance via yfinance', 'constituent_source': 'GitHub historical_sp500_constituents',
                    'competitive_advantages_note': '競爭優勢不由模型推測；待以10-K／公司IR資料補充並標註來源。'}
    data['data_quality'] = {'constituent_count': len(constituents), 'successful_this_run': success, 'failed_this_run': failed,
                            'records_in_cache': len(companies), 'coverage': len(companies) / len(constituents) if len(constituents) else 0}
    save(data)
    print(f'Completed: success={success}, failed={failed}, cached={len(companies)}')


if __name__ == '__main__':
    main()
