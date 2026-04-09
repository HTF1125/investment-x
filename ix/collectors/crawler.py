"""External data crawlers (Yahoo, FRED, Naver).

Lightweight downloaders used by collectors and ad-hoc data fetches. These
return raw pandas DataFrames — they do not write to the database.
"""
from typing import Optional, List
import pandas as pd
from ix.common.terminal import get_logger
from ix.common.date import tomorrow

logger = get_logger(__name__)


def _get_pandas_datareader():
    try:
        import pandas_datareader as pdr
    except Exception as exc:
        logger.warning("pandas_datareader unavailable: %s", exc)
        return None
    return pdr


def get_yahoo_data(
    code: str,
    start: str = "1950-1-1",
    end: str = "",
    progress: bool = False,
    actions: bool = True,
) -> pd.DataFrame:
    """Download OHLCV data from Yahoo Finance.

    Uses yf.Ticker().history() instead of yf.download() because the latter
    uses shared global state that corrupts results under concurrent access.
    """
    logger = get_logger(get_yahoo_data)
    if not end:
        end = tomorrow().date().strftime("%Y-%m-%d")
    try:
        import yfinance as yf

        data = yf.Ticker(code).history(
            start=start,
            end=end,
            auto_adjust=False,
            actions=actions,
        )
        if data is None or data.empty:
            raise ValueError(f"yfinance returned no data for ticker {code}")
        # Ticker.history() returns tz-aware index in the exchange's local
        # timezone (e.g. America/New_York, Asia/Tokyo). Use tz_localize(None)
        # to drop the tz while preserving wall-clock time — the exchange-local
        # calendar date is what we want to store. tz_convert(None) would shift
        # to UTC and cause off-by-one dates for non-US exchanges.
        if hasattr(data.index, "tz") and data.index.tz is not None:
            data.index = data.index.tz_localize(None)
        # Normalize index to midnight (date with 00:00:00 time component)
        data.index = pd.to_datetime(data.index).normalize()
        # Add 'Adj Close' column for backward compatibility (equals Close
        # when auto_adjust=False; some callers reference this column).
        if "Adj Close" not in data.columns and "Close" in data.columns:
            data["Adj Close"] = data["Close"]
        return data
    except Exception as exc:
        logger.warning("Download data from `yahoo` fail for ticker %s: %s", code, exc)
        return pd.DataFrame()


def _get_fred_via_browser(ticker: str, timeout_ms: int = 20000) -> pd.DataFrame:
    """Fetch FRED series using playwright to hit the FRED internal chart API.

    FRED's fredgraph.csv endpoint is blocked in some network environments (times out
    at the HTTP layer after TLS succeeds). The internal chart API at
    /graph/api/series/?obs=true&sid=<ID> is only accessible in a browser session
    context — this function uses playwright to load the series page and intercepts
    the API response containing all observations as [timestamp_ms, value] pairs.

    Returns a DataFrame with a PX_LAST column, or empty DataFrame on failure.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return pd.DataFrame()

    logger = get_logger(_get_fred_via_browser)
    captured = {}

    try:
        import time as _time
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            def _on_response(response):
                if "fred.stlouisfed.org/graph/api/series/" in response.url and "obs=true" in response.url:
                    try:
                        captured["body"] = response.body()
                    except Exception:
                        pass

            page.on("response", _on_response)
            # Use commit (first byte) so CSV-redirect pages don't hang at domcontentloaded
            try:
                page.goto(
                    f"https://fred.stlouisfed.org/series/{ticker}",
                    timeout=timeout_ms,
                    wait_until="commit",
                )
            except Exception:
                pass  # page may "fail" if it redirects to CSV — the API call still fires
            # Poll until API response captured or timeout
            deadline = _time.time() + timeout_ms / 1000
            while "body" not in captured and _time.time() < deadline:
                page.wait_for_timeout(200)
            browser.close()
    except Exception as exc:
        logger.warning("FRED browser fetch failed for %s: %s", ticker, exc)
        return pd.DataFrame()

    if "body" not in captured:
        logger.warning("FRED browser fetch: no API response captured for %s", ticker)
        return pd.DataFrame()

    try:
        import json as _json
        data = _json.loads(captured["body"])
        obs_list = data.get("observations", [])
        if not obs_list or not obs_list[0]:
            return pd.DataFrame()
        # observations is a list-of-lists: [[ts_ms, value], ...]
        pairs = obs_list[0]
        records = {}
        for pair in pairs:
            if len(pair) == 2 and pair[1] is not None:
                ts = pd.Timestamp(pair[0], unit="ms")
                records[ts] = float(pair[1])
        if not records:
            return pd.DataFrame()
        s = pd.Series(records, name="PX_LAST", dtype=float)
        s.index.name = "DATE"
        logger.info("FRED browser fetch: %d observations for %s", len(s), ticker)
        return s.to_frame()
    except Exception as exc:
        logger.warning("FRED browser fetch: parse error for %s: %s", ticker, exc)
        return pd.DataFrame()


def get_fred_data(
    ticker: str,
    start: str = "1900-1-1",
    end: str = tomorrow().date().strftime("%Y-%m-%d"),
    retries: int = 2,
    timeout: int = 30,
) -> pd.DataFrame:
    """Fetch FRED series data.

    Strategy (in order):
    1. FRED JSON API (api.stlouisfed.org) when FRED_API_KEY is set — fastest, reliable.
    2. Playwright browser fetch — intercepts the internal FRED chart API; works even
       when fredgraph.csv is blocked (e.g. Windows TLS renegotiation / geo-block).
    3. pandas_datareader (fredgraph.csv) — fallback, may timeout on Windows.
    """
    import os, time

    logger = get_logger(get_fred_data)
    api_key = os.getenv("FRED_API_KEY", "").strip()

    if api_key:
        import requests
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": ticker,
            "api_key": api_key,
            "file_type": "json",
            "observation_start": start,
            "observation_end": end,
        }
        for attempt in range(retries + 1):
            try:
                r = requests.get(url, params=params, timeout=timeout)
                r.raise_for_status()
                observations = r.json().get("observations", [])
                if not observations:
                    return pd.DataFrame()
                records = {
                    pd.Timestamp(o["date"]): float(o["value"])
                    for o in observations
                    if o["value"] not in (".", "")
                }
                s = pd.Series(records, name="PX_LAST", dtype=float)
                s.index.name = "DATE"
                return s.to_frame()
            except Exception as exc:
                if attempt < retries:
                    wait = 5 * (attempt + 1)
                    logger.info("FRED %s attempt %d failed, retrying in %ds: %s", ticker, attempt + 1, wait, exc)
                    time.sleep(wait)
                else:
                    logger.warning("Download data from `fred` (API) fail for ticker %s: %s", ticker, exc)
                    return pd.DataFrame()

    # Try playwright browser fetch (works when fredgraph.csv is geo-blocked)
    df = _get_fred_via_browser(ticker)
    if not df.empty:
        return df

    # Final fallback: pandas_datareader (may timeout on Windows)
    pdr = _get_pandas_datareader()
    if pdr is None:
        raise ImportError("pandas_datareader is required for FRED data")

    for attempt in range(retries + 1):
        try:
            reader = pdr.fred.FredReader(symbols=ticker, start=start, end=end)
            reader.timeout = timeout
            data = reader.read()
            if not data.empty:
                data.columns = ["PX_LAST"]
            return data
        except Exception as exc:
            if "timed out" in str(exc).lower() or isinstance(exc, TimeoutError):
                logger.warning("FRED connection timed out for %s", ticker)
                return pd.DataFrame()
            if attempt < retries:
                wait = 5 * (attempt + 1)
                logger.info("FRED %s attempt %d failed, retrying in %ds...", ticker, attempt + 1, wait)
                time.sleep(wait)
            else:
                logger.warning("Download data from `fred` fail for ticker %s: %s", ticker, exc)
                return pd.DataFrame()


def get_naver_data(
    ticker: str,
    start: str = "1990-1-1",
    end: str = tomorrow().date().strftime("%Y-%m-%d"),
) -> pd.DataFrame:

    logger = get_logger(get_naver_data)
    try:
        pdr = _get_pandas_datareader()
        if pdr is None:
            raise ImportError("pandas_datareader is required for Naver data")

        data = pdr.DataReader(
            name=ticker,
            data_source="naver",
            # start=start,
            # end=end,
        )
        data.index = pd.to_datetime(data.index)
        data = data.apply(pd.to_numeric)
        return data
    except Exception as exc:
        logger.warning("Download data from `naver` fail for ticker %s: %s", ticker, exc)
        return pd.DataFrame()
