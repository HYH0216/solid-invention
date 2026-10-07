"""Daily prices from Yahoo Finance's public chart endpoint (no API key needed)."""

import json
import urllib.error
import urllib.parse
import urllib.request

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1mo&interval=1d"

# Trading 212 marks non-US listings with a lowercase letter before _EQ, e.g. VUAGl_EQ (London).
T212_EXCHANGE_SUFFIX = {"l": ".L", "d": ".DE", "p": ".PA", "a": ".AS", "m": ".MI", "e": ".MC"}


def yahoo_symbol(ticker: str) -> str:
    """Map a Trading 212 ticker (TSLA_US_EQ, VUAGl_EQ) or a plain one (TSLA, RR.L) to Yahoo's format."""
    if ticker.endswith("_US_EQ"):
        return ticker[: -len("_US_EQ")].replace("_", "-")
    if ticker.endswith("_EQ"):
        base = ticker[: -len("_EQ")]
        suffix = T212_EXCHANGE_SUFFIX.get(base[-1:])
        if suffix:
            return base[:-1] + suffix
        return base
    return ticker.upper()


def _pct(new: float | None, old: float | None) -> float | None:
    if not new or not old:
        return None
    return round((new / old - 1) * 100, 2)


def fetch_quote(ticker: str, timeout: float = 15) -> dict:
    symbol = yahoo_symbol(ticker)
    request = urllib.request.Request(
        CHART_URL.format(symbol=urllib.parse.quote(symbol)),
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            result = json.load(resp)["chart"]["result"][0]
    except urllib.error.HTTPError as exc:
        return {"symbol": symbol, "error": f"Yahoo Finance returned HTTP {exc.code}"}
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, TypeError, ValueError) as exc:
        return {"symbol": symbol, "error": f"quote unavailable: {exc}"}

    meta = result.get("meta", {})
    closes = [c for c in (result.get("indicators", {}).get("quote", [{}])[0].get("close") or []) if c]
    price = meta.get("regularMarketPrice")
    previous_close = closes[-2] if len(closes) >= 2 else meta.get("chartPreviousClose")

    return {
        "symbol": symbol,
        "name": meta.get("longName") or meta.get("shortName"),
        "currency": meta.get("currency"),
        "price": price,
        "previous_close": round(previous_close, 4) if previous_close else None,
        "day_change_pct": _pct(price, previous_close),
        "five_day_change_pct": _pct(price, closes[-6] if len(closes) >= 6 else None),
        "one_month_change_pct": _pct(price, closes[0] if closes else None),
        "day_high": meta.get("regularMarketDayHigh"),
        "day_low": meta.get("regularMarketDayLow"),
        "fifty_two_week_high": meta.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": meta.get("fiftyTwoWeekLow"),
        "market_time_utc": meta.get("regularMarketTime"),
    }
