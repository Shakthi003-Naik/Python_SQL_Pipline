"""
extract.py — Pull daily stock data from Alpha Vantage API.

Alpha Vantage free tier: 25 requests/day, 5 requests/minute.
Docs: https://www.alphavantage.co/documentation/#daily
"""

import os
import time
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

BASE_URL = "https://www.alphavantage.co/query"
API_KEY  = os.getenv("API_KEY", "demo")


def fetch_daily_prices(symbol: str, outputsize: str = "compact") -> list[dict]:
    """
    Fetch daily OHLCV data for a single stock symbol.

    Args:
        symbol:     Stock ticker (e.g. 'AAPL')
        outputsize: 'compact' = last 100 days | 'full' = up to 20 years

    Returns:
        List of dicts, each representing one trading day.
        Example row:
            {
              'symbol':      'AAPL',
              'trade_date':  '2024-01-15',
              'open_price':  '185.0000',
              'high_price':  '188.4400',
              'low_price':   '184.3500',
              'close_price': '187.1500',
              'volume':      '55234100'
            }

    Raises:
        ValueError: If the API returns an error message.
        requests.RequestException: On network failures.
    """
    params = {
        "function":   "TIME_SERIES_DAILY",
        "symbol":     symbol,
        "outputsize": outputsize,
        "apikey":     API_KEY,
    }

    logger.info("Fetching data for %s …", symbol)
    response = requests.get(BASE_URL, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    # ── API-level error handling ───────────────────────────
    if "Error Message" in data:
        raise ValueError(f"API error for {symbol}: {data['Error Message']}")
    if "Note" in data:
        # Rate-limit warning from Alpha Vantage
        logger.warning("API rate-limit note for %s: %s", symbol, data["Note"])
    if "Information" in data:
        raise ValueError(f"API key issue: {data['Information']}")

    time_series = data.get("Time Series (Daily)", {})
    if not time_series:
        logger.warning("No time series data returned for %s.", symbol)
        return []

    rows = []
    for date_str, ohlcv in time_series.items():
        rows.append({
            "symbol":      symbol.upper(),
            "trade_date":  date_str,
            "open_price":  ohlcv["1. open"],
            "high_price":  ohlcv["2. high"],
            "low_price":   ohlcv["3. low"],
            "close_price": ohlcv["4. close"],
            "volume":      ohlcv["5. volume"],
        })

    logger.info("Extracted %d rows for %s.", len(rows), symbol)
    return rows


def fetch_all_symbols(symbols: list[str]) -> list[dict]:
    """
    Fetch data for multiple symbols with a short delay between
    requests to respect the free-tier rate limit (5 req/min).
    """
    all_rows = []
    for i, symbol in enumerate(symbols):
        rows = fetch_daily_prices(symbol)
        all_rows.extend(rows)
        # Pause between calls to avoid hitting rate limit
        if i < len(symbols) - 1:
            logger.debug("Sleeping 12 s to respect API rate limit …")
            time.sleep(12)
    logger.info("Total rows extracted: %d across %d symbol(s).", len(all_rows), len(symbols))
    return all_rows
