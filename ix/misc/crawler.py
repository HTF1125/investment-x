from typing import Optional, List
import threading
import pandas as pd
from ix.misc.terminal import get_logger
from ix.misc.date import tomorrow

logger = get_logger(__name__)

# yfinance uses shared global state and is not thread-safe.
# Serialize all yf.download calls to prevent concurrent calls from
# returning corrupted/swapped data.
_yf_lock = threading.Lock()


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
    logger = get_logger(get_yahoo_data)
    if not end:
        end = tomorrow().date().strftime("%Y-%m-%d")
    try:
        import yfinance as yf

        with _yf_lock:
            data = yf.download(
                tickers=code,
                start=start,
                end=end,
                progress=progress,
                actions=actions,
                auto_adjust=False,
                multi_level_index=False,
            )
        if data is None:
            raise ValueError(f"yfinance returned None for ticker {code}")
        return data
    except Exception as exc:
        logger.warning("Download data from `yahoo` fail for ticker %s: %s", code, exc)
        return pd.DataFrame()


def get_fred_data(
    ticker: str,
    start: str = "1900-1-1",
    end: str = tomorrow().date().strftime("%Y-%m-%d"),
    retries: int = 2,
    timeout: int = 60,
) -> pd.DataFrame:

    logger = get_logger(get_fred_data)
    pdr = _get_pandas_datareader()
    if pdr is None:
        raise ImportError("pandas_datareader is required for FRED data")

    # Short timeout to gracefully skip if St. Louis Fed is blocked by Korean ISPs
    timeout = min(timeout, 10)

    for attempt in range(retries + 1):
        try:
            import requests

            session = requests.Session()
            session.headers.update(
                {"User-Agent": "Mozilla/5.0 (Investment-X Research)"}
            )
            reader = pdr.fred.FredReader(
                symbols=ticker,
                start=start,
                end=end,
            )
            reader.session = session
            reader.timeout = timeout
            data = reader.read()
            if not data.empty:
                data.columns = ["PX_LAST"]
            return data
        except Exception as exc:
            if "timed out" in str(exc).lower() or isinstance(exc, TimeoutError):
                logger.warning(
                    "FRED connection timed out (likely firewall/ISP block) for %s", ticker
                )
                return pd.DataFrame()  # Fail fast instead of retrying forever

            if attempt < retries:
                import time

                wait = 5 * (attempt + 1)
                logger.info(
                    "FRED %s attempt %d failed, retrying in %ds...", ticker, attempt + 1, wait
                )
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
