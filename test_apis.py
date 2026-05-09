"""
Test suite for News API (port 5001) and Stock API (port 5002).
Run both servers first:  bash run_all.sh
Then in another terminal: python test_apis.py
"""

import sys
import json
import time
import requests

NEWS_BASE  = "http://localhost:5001"
STOCK_BASE = "http://localhost:5002"

PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"

results = {"passed": 0, "failed": 0}


def check(label: str, condition: bool, detail: str = ""):
    if condition:
        print(f"{PASS} {label}")
        results["passed"] += 1
    else:
        print(f"{FAIL} {label}" + (f"  ← {detail}" if detail else ""))
        results["failed"] += 1


def get(url: str, params: dict = None, expected_status: int = 200):
    try:
        r = requests.get(url, params=params, timeout=5)
        return r
    except requests.exceptions.ConnectionError:
        print(f"\033[91m CONNECTION ERROR\033[0m  {url}")
        print("  Make sure the server is running: bash run_all.sh")
        sys.exit(1)


def section(title: str):
    print(f"\n{'─' * 55}")
    print(f"  {title}")
    print(f"{'─' * 55}")


# ─────────────────────────────────────────────────────────
# NEWS API TESTS
# ─────────────────────────────────────────────────────────
section("NEWS API — /health")

r = get(f"{NEWS_BASE}/health")
check("GET /health returns 200", r.status_code == 200)
d = r.json()
check("service name present", "service" in d)
check("status is ok", d.get("status") == "ok")

# ── /v2/top-headlines ─────────────────────────────────────
section("NEWS API — /v2/top-headlines")

r = get(f"{NEWS_BASE}/v2/top-headlines")
check("GET /v2/top-headlines returns 200", r.status_code == 200)
d = r.json()
check("status = ok", d.get("status") == "ok")
check("articles key present", "articles" in d)
check("totalResults > 0", d.get("totalResults", 0) > 0)
check("first article has title", len(d["articles"]) > 0 and "title" in d["articles"][0])

r = get(f"{NEWS_BASE}/v2/top-headlines", {"category": "technology"})
check("category=technology filter works", r.status_code == 200 and r.json().get("totalResults", 0) > 0)

r = get(f"{NEWS_BASE}/v2/top-headlines", {"category": "sports"})
check("category=sports filter works", r.status_code == 200 and r.json().get("totalResults", 0) > 0)

r = get(f"{NEWS_BASE}/v2/top-headlines", {"category": "health"})
check("category=health filter works", r.status_code == 200 and r.json().get("totalResults", 0) > 0)

r = get(f"{NEWS_BASE}/v2/top-headlines", {"pageSize": "3"})
d = r.json()
check("pageSize=3 limits results to 3", len(d.get("articles", [])) <= 3)

r = get(f"{NEWS_BASE}/v2/top-headlines", {"q": "AI"})
check("q=AI returns results", r.status_code == 200 and r.json().get("totalResults", 0) > 0)

r = get(f"{NEWS_BASE}/v2/top-headlines", {"category": "invalid_cat"})
check("invalid category returns 400", r.status_code == 400)

r = get(f"{NEWS_BASE}/v2/top-headlines", {"sources": "techcrunch", "category": "technology"})
check("sources + category returns 400 (incompatible)", r.status_code == 400)

# ── /v2/everything ────────────────────────────────────────
section("NEWS API — /v2/everything")

r = get(f"{NEWS_BASE}/v2/everything")
check("GET /v2/everything returns 200", r.status_code == 200)
d = r.json()
check("totalResults ≥ 30", d.get("totalResults", 0) >= 30)

r = get(f"{NEWS_BASE}/v2/everything", {"q": "vaccine"})
d = r.json()
check("q=vaccine returns ≥ 1 result", d.get("totalResults", 0) >= 1)

r = get(f"{NEWS_BASE}/v2/everything", {"q": "xyzabcnotfound123"})
check("no-match query returns 0 results", r.json().get("totalResults", -1) == 0)

r = get(f"{NEWS_BASE}/v2/everything", {"sortBy": "popularity"})
check("sortBy=popularity returns 200", r.status_code == 200)

r = get(f"{NEWS_BASE}/v2/everything", {"sortBy": "bad"})
check("sortBy=bad returns 400", r.status_code == 400)

r = get(f"{NEWS_BASE}/v2/everything", {"from": "2026-05-06"})
d = r.json()
check("from=2026-05-06 filters to recent articles", d.get("totalResults", 0) > 0)

r = get(f"{NEWS_BASE}/v2/everything", {"sources": "espn"})
d = r.json()
check("sources=espn filters correctly", all(
    a["source"]["id"] == "espn" for a in d.get("articles", [])
) and d.get("totalResults", 0) > 0)

r = get(f"{NEWS_BASE}/v2/everything", {"page": "2", "pageSize": "5"})
check("page=2&pageSize=5 returns 200", r.status_code == 200)

# ── /v2/sources ───────────────────────────────────────────
section("NEWS API — /v2/sources")

r = get(f"{NEWS_BASE}/v2/sources")
check("GET /v2/sources returns 200", r.status_code == 200)
d = r.json()
check("sources list not empty", len(d.get("sources", [])) > 0)
src = d["sources"][0]
check("source has required fields", all(k in src for k in ("id", "name", "category", "language", "country")))

r = get(f"{NEWS_BASE}/v2/sources", {"category": "technology"})
d = r.json()
check("sources category=technology filter", all(s["category"] == "technology" for s in d.get("sources", [])))

r = get(f"{NEWS_BASE}/v2/sources", {"country": "us"})
d = r.json()
check("sources country=us filter", all(s["country"] == "us" for s in d.get("sources", [])))


# ─────────────────────────────────────────────────────────
# STOCK API TESTS
# ─────────────────────────────────────────────────────────
section("STOCK API — /health")

r = get(f"{STOCK_BASE}/health")
check("GET /health returns 200", r.status_code == 200)
d = r.json()
check("status is ok", d.get("status") == "ok")
check("supported_functions list present", "supported_functions" in d)

# ── GLOBAL_QUOTE ──────────────────────────────────────────
section("STOCK API — GLOBAL_QUOTE")

r = get(f"{STOCK_BASE}/query", {"function": "GLOBAL_QUOTE", "symbol": "AAPL"})
check("GLOBAL_QUOTE AAPL returns 200", r.status_code == 200)
d = r.json()
check("Global Quote key present", "Global Quote" in d)
gq = d["Global Quote"]
check("has 10 fields", len(gq) == 10)
check("01. symbol = AAPL", gq.get("01. symbol") == "AAPL")
check("05. price is numeric string", float(gq.get("05. price", "bad")) > 0)

r = get(f"{STOCK_BASE}/query", {"function": "GLOBAL_QUOTE", "symbol": "MSFT"})
check("GLOBAL_QUOTE MSFT returns 200", r.status_code == 200)

r = get(f"{STOCK_BASE}/query", {"function": "GLOBAL_QUOTE", "symbol": "FAKEXYZ"})
d = r.json()
check("GLOBAL_QUOTE unknown symbol returns empty quote", d.get("Global Quote") == {})

r = get(f"{STOCK_BASE}/query", {"function": "GLOBAL_QUOTE"})
check("GLOBAL_QUOTE without symbol returns 400", r.status_code == 400)

# ── SYMBOL_SEARCH ─────────────────────────────────────────
section("STOCK API — SYMBOL_SEARCH")

r = get(f"{STOCK_BASE}/query", {"function": "SYMBOL_SEARCH", "keywords": "apple"})
check("SYMBOL_SEARCH 'apple' returns 200", r.status_code == 200)
d = r.json()
check("bestMatches key present", "bestMatches" in d)
check("AAPL in matches", any(m["1. symbol"] == "AAPL" for m in d.get("bestMatches", [])))

r = get(f"{STOCK_BASE}/query", {"function": "SYMBOL_SEARCH", "keywords": "NVDA"})
d = r.json()
check("SYMBOL_SEARCH NVDA found", any(m["1. symbol"] == "NVDA" for m in d.get("bestMatches", [])))

r = get(f"{STOCK_BASE}/query", {"function": "SYMBOL_SEARCH", "keywords": "bank"})
d = r.json()
check("SYMBOL_SEARCH 'bank' finds BAC or JPM", any(
    m["1. symbol"] in ("BAC", "JPM") for m in d.get("bestMatches", [])
))

r = get(f"{STOCK_BASE}/query", {"function": "SYMBOL_SEARCH"})
check("SYMBOL_SEARCH without keywords returns 400", r.status_code == 400)

# ── TIME_SERIES_DAILY ─────────────────────────────────────
section("STOCK API — TIME_SERIES_DAILY")

r = get(f"{STOCK_BASE}/query", {"function": "TIME_SERIES_DAILY", "symbol": "TSLA"})
check("TIME_SERIES_DAILY TSLA returns 200", r.status_code == 200)
d = r.json()
check("Meta Data present", "Meta Data" in d)
check("Time Series (Daily) present", "Time Series (Daily)" in d)
days = d["Time Series (Daily)"]
check("Has ≥ 50 trading days", len(days) >= 50)
first_day = next(iter(days))
day_data = days[first_day]
check("Each day has OHLCV", all(k in day_data for k in ("1. open", "2. high", "3. low", "4. close", "5. volume")))

r = get(f"{STOCK_BASE}/query", {"function": "TIME_SERIES_DAILY", "symbol": "NOTREAL"})
check("TIME_SERIES_DAILY unknown symbol returns 404", r.status_code == 404)

# ── TIME_SERIES_INTRADAY ──────────────────────────────────
section("STOCK API — TIME_SERIES_INTRADAY")

r = get(f"{STOCK_BASE}/query", {"function": "TIME_SERIES_INTRADAY", "symbol": "AAPL", "interval": "5min"})
check("TIME_SERIES_INTRADAY AAPL 5min returns 200", r.status_code == 200)
d = r.json()
check("Meta Data interval is 5min", d.get("Meta Data", {}).get("4. Interval") == "5min")
check("Time Series (5min) present", "Time Series (5min)" in d)
check("Has ≥ 60 intraday points", len(d.get("Time Series (5min)", {})) >= 60)

r = get(f"{STOCK_BASE}/query", {"function": "TIME_SERIES_INTRADAY", "symbol": "NVDA", "interval": "60min"})
check("TIME_SERIES_INTRADAY NVDA 60min returns 200", r.status_code == 200 and "Time Series (60min)" in r.json())

r = get(f"{STOCK_BASE}/query", {"function": "TIME_SERIES_INTRADAY", "symbol": "AAPL", "interval": "99min"})
check("TIME_SERIES_INTRADAY invalid interval returns 400", r.status_code == 400)

# ── Commodities ───────────────────────────────────────────
section("STOCK API — Commodities (WTI, BRENT, GOLD…)")

for func in ("WTI", "BRENT", "NATURAL_GAS", "COPPER", "ALUMINUM", "WHEAT", "CORN", "COFFEE"):
    r = get(f"{STOCK_BASE}/query", {"function": func, "interval": "monthly"})
    d = r.json()
    ok = (
        r.status_code == 200
        and "name" in d
        and "data" in d
        and len(d["data"]) >= 12
        and "date" in d["data"][0]
        and "value" in d["data"][0]
    )
    check(f"{func} monthly series (≥12 data points)", ok)

r = get(f"{STOCK_BASE}/query", {"function": "ALL_COMMODITIES", "interval": "monthly"})
check("ALL_COMMODITIES returns 200", r.status_code == 200)
d = r.json()
check("ALL_COMMODITIES has ≥ 8 entries", len(d.get("data", [])) >= 8)

r = get(f"{STOCK_BASE}/query", {"function": "WTI", "interval": "bad"})
check("WTI with invalid interval returns 400", r.status_code == 400)

# ── CURRENCY_EXCHANGE_RATE ────────────────────────────────
section("STOCK API — CURRENCY_EXCHANGE_RATE")

r = get(f"{STOCK_BASE}/query", {"function": "CURRENCY_EXCHANGE_RATE", "from_currency": "BTC", "to_currency": "USD"})
check("BTC/USD exchange rate returns 200", r.status_code == 200)
d = r.json()
check("Realtime Currency Exchange Rate key present", "Realtime Currency Exchange Rate" in d)
rate_data = d["Realtime Currency Exchange Rate"]
check("1. From_Currency Code = BTC", rate_data.get("1. From_Currency Code") == "BTC")
check("5. Exchange Rate > 0", float(rate_data.get("5. Exchange Rate", 0)) > 0)

r = get(f"{STOCK_BASE}/query", {"function": "CURRENCY_EXCHANGE_RATE", "from_currency": "ETH"})
check("ETH exchange rate returns 200", r.status_code == 200)

r = get(f"{STOCK_BASE}/query", {"function": "CURRENCY_EXCHANGE_RATE", "from_currency": "EUR"})
check("EUR fiat exchange rate returns 200", r.status_code == 200)

r = get(f"{STOCK_BASE}/query", {"function": "CURRENCY_EXCHANGE_RATE", "from_currency": "FAKECOIN"})
check("Unknown currency returns 404", r.status_code == 404)

# ── DIGITAL_CURRENCY_DAILY ────────────────────────────────
section("STOCK API — DIGITAL_CURRENCY_DAILY")

r = get(f"{STOCK_BASE}/query", {"function": "DIGITAL_CURRENCY_DAILY", "symbol": "BTC", "market": "USD"})
check("DIGITAL_CURRENCY_DAILY BTC/USD returns 200", r.status_code == 200)
d = r.json()
check("Meta Data present", "Meta Data" in d)
check("Time Series (Digital Currency Daily) present", "Time Series (Digital Currency Daily)" in d)
series = d["Time Series (Digital Currency Daily)"]
check("Has ≥ 90 daily entries", len(series) >= 90)
first_entry = next(iter(series))
entry = series[first_entry]
check("Entry has open/high/low/close USD fields", "1a. open (USD)" in entry and "4a. close (USD)" in entry)

r = get(f"{STOCK_BASE}/query", {"function": "DIGITAL_CURRENCY_DAILY", "symbol": "SOL"})
check("DIGITAL_CURRENCY_DAILY SOL returns 200", r.status_code == 200)

r = get(f"{STOCK_BASE}/query", {"function": "DIGITAL_CURRENCY_DAILY", "symbol": "FAKECOIN"})
check("DIGITAL_CURRENCY_DAILY unknown symbol returns 404", r.status_code == 404)

# ── Bad function name ─────────────────────────────────────
section("STOCK API — Error handling")

r = get(f"{STOCK_BASE}/query", {"function": "NONEXISTENT_FUNCTION"})
check("Unknown function returns 400 with Error Message", r.status_code == 400 and "Error Message" in r.json())

r = get(f"{STOCK_BASE}/query")
check("Missing function param returns 400", r.status_code == 400)


# ─────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────
total = results["passed"] + results["failed"]
print(f"\n{'═' * 55}")
print(f"  Results: {results['passed']}/{total} passed", end="")
if results["failed"] == 0:
    print("  \033[92m✓ All tests passed!\033[0m")
else:
    print(f"  \033[91m✗ {results['failed']} failed\033[0m")
print(f"{'═' * 55}\n")

sys.exit(0 if results["failed"] == 0 else 1)
