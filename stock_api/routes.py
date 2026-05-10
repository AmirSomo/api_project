from flask import Blueprint, jsonify, request
import json
import os
from datetime import datetime, timedelta
import random

stock_bp = Blueprint('stock', __name__)

COMMODITY_META = {
    "WTI":         {"name": "West Texas Intermediate (WTI) Crude Oil",        "unit": "dollars per barrel",       "base": 78.45,  "volatility": 0.025},
    "BRENT":       {"name": "Brent Crude Oil",                                 "unit": "dollars per barrel",       "base": 82.15,  "volatility": 0.022},
    "NATURAL_GAS": {"name": "Henry Hub Natural Gas Spot Price",                "unit": "dollars per million BTU",  "base": 2.85,   "volatility": 0.045},
    "COPPER":      {"name": "Global price of Copper",                          "unit": "dollars per metric ton",   "base": 9500.0, "volatility": 0.018},
    "ALUMINUM":    {"name": "Global price of Aluminum",                        "unit": "dollars per metric ton",   "base": 2350.0, "volatility": 0.020},
    "WHEAT":       {"name": "Global price of Wheat",                           "unit": "dollars per metric ton",   "base": 245.0,  "volatility": 0.030},
    "CORN":        {"name": "Global price of Corn",                            "unit": "dollars per metric ton",   "base": 185.0,  "volatility": 0.028},
    "COTTON":      {"name": "Global price of Cotton",                          "unit": "cents per pound",          "base": 82.5,   "volatility": 0.022},
    "SUGAR":       {"name": "Global price of Sugar",                           "unit": "cents per pound",          "base": 19.8,   "volatility": 0.032},
    "COFFEE":      {"name": "Global price of Coffee, Other Mild Arabicas",     "unit": "cents per pound",          "base": 215.0,  "volatility": 0.035},
}


def _load_stocks():
    path = os.path.join(os.path.dirname(__file__), 'mock_data', 'stocks.json')
    with open(path) as f:
        return json.load(f)['stocks']


def _load_crypto():
    path = os.path.join(os.path.dirname(__file__), 'mock_data', 'crypto.json')
    with open(path) as f:
        return json.load(f)['crypto']


def _walk(symbol, step, base, vol):
    random.seed(sum(ord(c) for c in symbol) * 31 + step * 7)
    return base * (1 + random.uniform(-vol, vol))


def _daily_series(symbol, stock, n=100):
    series = {}
    today = datetime(2026, 5, 8)
    price = stock['price']
    for i in range(n):
        day = today - timedelta(days=i)
        if day.weekday() >= 5:
            continue
        random.seed(sum(ord(c) for c in symbol) * 31 + i * 7)
        chg = random.uniform(-0.03, 0.03)
        open_p = price
        price = round(price * (1 + chg), 4)
        high = round(max(open_p, price) * (1 + random.uniform(0, 0.008)), 4)
        low = round(min(open_p, price) * (1 - random.uniform(0, 0.008)), 4)
        vol = int(stock['volume'] * random.uniform(0.65, 1.35))
        series[day.strftime('%Y-%m-%d')] = {
            "1. open": f"{open_p:.4f}", "2. high": f"{high:.4f}",
            "3. low": f"{low:.4f}", "4. close": f"{price:.4f}", "5. volume": str(vol)
        }
    return series


def _intraday_series(symbol, stock, interval='5min', n=78):
    mins = {'1min': 1, '5min': 5, '15min': 15, '30min': 30, '60min': 60}
    step_min = mins.get(interval, 5)
    series = {}
    base_ts = datetime(2026, 5, 8, 20, 0, 0)
    price = stock['price']
    for i in range(n):
        ts = base_ts - timedelta(minutes=i * step_min)
        random.seed(sum(ord(c) for c in symbol) * 31 + i * 13)
        chg = random.uniform(-0.004, 0.004)
        open_p = price
        price = round(price * (1 + chg), 4)
        high = round(max(open_p, price) * (1 + random.uniform(0, 0.002)), 4)
        low = round(min(open_p, price) * (1 - random.uniform(0, 0.002)), 4)
        vol = int((stock['volume'] / 78) * random.uniform(0.4, 1.6))
        series[ts.strftime('%Y-%m-%d %H:%M:%S')] = {
            "1. open": f"{open_p:.4f}", "2. high": f"{high:.4f}",
            "3. low": f"{low:.4f}", "4. close": f"{price:.4f}", "5. volume": str(vol)
        }
    return series


def _commodity_series(function, n=60):
    meta = COMMODITY_META[function]
    price = meta['base']
    vol = meta['volatility']
    data = []
    anchor = datetime(2026, 5, 1)
    for i in range(n):
        month = (anchor - timedelta(days=i * 30)).replace(day=1)
        random.seed(sum(ord(c) for c in function) * 31 + i * 11)
        price = round(price * (1 + random.uniform(-vol, vol)), 4)
        data.append({"date": month.strftime('%Y-%m-%d'), "value": f"{price:.2f}" if price >= 1 else f"{price:.4f}"})
    return data


def _crypto_series(symbol, crypto, market, n=100):
    series = {}
    today = datetime(2026, 5, 8)
    price = crypto['price']
    for i in range(n):
        day = today - timedelta(days=i)
        random.seed(sum(ord(c) for c in symbol) * 31 + i * 17)
        chg = random.uniform(-0.06, 0.06)
        open_p = price
        price = round(price * (1 + chg), 5)
        high = round(max(open_p, price) * (1 + random.uniform(0, 0.015)), 5)
        low = round(min(open_p, price) * (1 - random.uniform(0, 0.015)), 5)
        vol = round(crypto['volume_24h'] * random.uniform(0.5, 1.5), 5)
        series[day.strftime('%Y-%m-%d')] = {
            f"1a. open ({market})": f"{open_p:.5f}", f"1b. open ({market})": f"{open_p:.5f}",
            f"2a. high ({market})": f"{high:.5f}", f"2b. high ({market})": f"{high:.5f}",
            f"3a. low ({market})": f"{low:.5f}", f"3b. low ({market})": f"{low:.5f}",
            f"4a. close ({market})": f"{price:.5f}", f"4b. close ({market})": f"{price:.5f}",
            "5. volume": f"{vol:.5f}", f"6. market cap ({market})": f"{price * vol:.5f}"
        }
    return series


def _av_error(msg, status=400):
    return jsonify({"Error Message": msg}), status


@stock_bp.route('/query', methods=['GET'])
def query():
    function = request.args.get('function', '').upper()

    if not function:
        return _av_error("Invalid API call. Please specify a function parameter.")

    if function == 'TIME_SERIES_INTRADAY':
        symbol = request.args.get('symbol', '').upper()
        interval = request.args.get('interval', '5min').lower()
        if not symbol:
            return _av_error("Invalid API call. Please specify a symbol.")
        if interval not in ('1min', '5min', '15min', '30min', '60min'):
            return _av_error(f"Invalid interval '{interval}'. Valid values: 1min, 5min, 15min, 30min, 60min")
        stock = next((s for s in _load_stocks() if s['symbol'] == symbol), None)
        if not stock:
            return _av_error(f"Invalid API call, symbol '{symbol}' not found.", 404)
        return jsonify({
            "Meta Data": {
                "1. Information": f"Intraday ({interval}) open, high, low, close prices and volume",
                "2. Symbol": symbol, "3. Last Refreshed": "2026-05-08 20:00:00",
                "4. Interval": interval, "5. Output Size": "Compact", "6. Time Zone": "US/Eastern"
            },
            f"Time Series ({interval})": _intraday_series(symbol, stock, interval)
        })

    if function == 'TIME_SERIES_DAILY':
        symbol = request.args.get('symbol', '').upper()
        if not symbol:
            return _av_error("Invalid API call. Please specify a symbol.")
        stock = next((s for s in _load_stocks() if s['symbol'] == symbol), None)
        if not stock:
            return _av_error(f"Invalid API call, symbol '{symbol}' not found.", 404)
        return jsonify({
            "Meta Data": {
                "1. Information": "Daily Prices (open, high, low, close) and Volumes",
                "2. Symbol": symbol, "3. Last Refreshed": "2026-05-08",
                "4. Output Size": "Compact", "5. Time Zone": "US/Eastern"
            },
            "Time Series (Daily)": _daily_series(symbol, stock)
        })

    if function == 'GLOBAL_QUOTE':
        symbol = request.args.get('symbol', '').upper()
        if not symbol:
            return _av_error("Invalid API call. Please specify a symbol.")
        stock = next((s for s in _load_stocks() if s['symbol'] == symbol), None)
        if not stock:
            return jsonify({"Global Quote": {}})
        prev_close = round(stock['price'] - stock['change'], 4)
        return jsonify({"Global Quote": {
            "01. symbol": symbol, "02. open": f"{stock['open']:.4f}",
            "03. high": f"{stock['high']:.4f}", "04. low": f"{stock['low']:.4f}",
            "05. price": f"{stock['price']:.4f}", "06. volume": str(stock['volume']),
            "07. latest trading day": "2026-05-08", "08. previous close": f"{prev_close:.4f}",
            "09. change": f"{stock['change']:.4f}", "10. change percent": f"{stock['changePercent']:.4f}%"
        }})

    if function == 'SYMBOL_SEARCH':
        keywords = request.args.get('keywords', '').lower()
        if not keywords:
            return _av_error("Invalid API call. Please specify a keywords parameter.")
        matches = []
        for s in _load_stocks():
            if keywords in s['symbol'].lower():
                score = "1.0000"
            elif keywords in s['name'].lower():
                score = "0.8000"
            else:
                continue
            matches.append({
                "1. symbol": s['symbol'], "2. name": s['name'], "3. type": "Equity",
                "4. region": "United States", "5. marketOpen": "09:30", "6. marketClose": "16:00",
                "7. timezone": "UTC-04", "8. currency": "USD", "9. matchScore": score
            })
        return jsonify({"bestMatches": matches})

    if function == 'CURRENCY_EXCHANGE_RATE':
        from_cur = request.args.get('from_currency', '').upper()
        to_cur = request.args.get('to_currency', 'USD').upper()
        if not from_cur:
            return _av_error("Invalid API call. Please specify from_currency.")
        crypto = next((c for c in _load_crypto() if c['symbol'] == from_cur), None)
        if crypto:
            rate, from_name = crypto['price'], crypto['name']
        else:
            fiat = {"EUR": (1.085, "Euro"), "GBP": (1.272, "British Pound Sterling"),
                    "JPY": (0.00672, "Japanese Yen"), "CAD": (0.737, "Canadian Dollar"),
                    "AUD": (0.652, "Australian Dollar"), "CHF": (1.102, "Swiss Franc")}
            if from_cur not in fiat:
                return _av_error(f"Currency '{from_cur}' not supported.", 404)
            rate, from_name = fiat[from_cur]
        spread = max(rate * 0.0001, 0.0001)
        return jsonify({"Realtime Currency Exchange Rate": {
            "1. From_Currency Code": from_cur, "2. From_Currency Name": from_name,
            "3. To_Currency Code": to_cur, "4. To_Currency Name": "United States Dollar",
            "5. Exchange Rate": f"{rate:.8f}", "6. Last Refreshed": "2026-05-08 20:00:00",
            "7. Time Zone": "UTC", "8. Bid Price": f"{rate - spread:.8f}", "9. Ask Price": f"{rate + spread:.8f}"
        }})

    if function == 'DIGITAL_CURRENCY_DAILY':
        symbol = request.args.get('symbol', '').upper()
        market = request.args.get('market', 'USD').upper()
        if not symbol:
            return _av_error("Invalid API call. Please specify a symbol.")
        crypto = next((c for c in _load_crypto() if c['symbol'] == symbol), None)
        if not crypto:
            return _av_error(f"Invalid API call, symbol '{symbol}' not found.", 404)
        return jsonify({
            "Meta Data": {
                "1. Information": "Daily Prices and Volumes for Digital Currency",
                "2. Digital Currency Code": symbol, "3. Digital Currency Name": crypto['name'],
                "4. Market Code": market, "5. Market Name": "United States Dollar",
                "6. Last Refreshed": "2026-05-08 00:00:00", "7. Time Zone": "UTC"
            },
            "Time Series (Digital Currency Daily)": _crypto_series(symbol, crypto, market)
        })

    if function == 'ALL_COMMODITIES':
        interval = request.args.get('interval', 'monthly').lower()
        result = [{"id": func, "name": meta['name'], "unit": meta['unit'], "interval": interval,
                   "data": _commodity_series(func, {'monthly': 12, 'weekly': 52, 'daily': 90}.get(interval, 12))}
                  for func, meta in COMMODITY_META.items()]
        return jsonify({"name": "All Commodities", "interval": interval, "data": result})

    if function in COMMODITY_META:
        interval = request.args.get('interval', 'monthly').lower()
        if interval not in ('daily', 'weekly', 'monthly'):
            return _av_error(f"Invalid interval '{interval}'. Valid values: daily, weekly, monthly")
        meta = COMMODITY_META[function]
        n = {'monthly': 60, 'weekly': 104, 'daily': 365}[interval]
        return jsonify({"name": meta['name'], "interval": interval, "unit": meta['unit'],
                        "data": _commodity_series(function, n)})

    return _av_error(
        f"Unsupported function '{function}'. Supported: TIME_SERIES_INTRADAY, TIME_SERIES_DAILY, "
        "GLOBAL_QUOTE, SYMBOL_SEARCH, CURRENCY_EXCHANGE_RATE, DIGITAL_CURRENCY_DAILY, ALL_COMMODITIES, "
        + ", ".join(COMMODITY_META.keys())
    )
