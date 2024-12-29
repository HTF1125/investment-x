import pandas as pd
import yfinance as yf
import pandas_datareader as pdr
from ix.misc.terminal import get_logger
from ix.misc.date import tomorrow

logger = get_logger(__name__)


def get_bloomberg_data(
    code: str,
    field: str = "PX_LAST",
    start: str = "1950-1-1",
    end: str = tomorrow().date().strftime("%Y-%m-%d"),
) -> pd.DataFrame:
    try:
        from xbbg import blp

        data = blp.bdh(code, field, start_date=start, end_date=end)
        data.columns = [code]
        data.index.name = "date"
        data.index = pd.to_datetime(data.index)
        return data
    except Exception as e:
        return pd.DataFrame()


def get_yahoo_data(
    code: str,
    start: str = "1950-1-1",
    end: str = tomorrow().date().strftime("%Y-%m-%d"),
    progress: bool = False,
    actions: bool = True,
) -> pd.DataFrame:
    logger = get_logger(get_fred_data)
    try:
        data = yf.download(
            tickers=code,
            start=start,
            end=end,
            progress=progress,
            actions=actions,
        )
        return data
    except Exception as exc:
        logger.warning(f"Download data from `yahoo` fail for ticker {code}")
        logger.exception(exc)
        return pd.DataFrame()


def get_fred_data(
    ticker: str,
    start: str = "1900-1-1",
    end: str = tomorrow().date().strftime("%Y-%m-%d"),
) -> pd.DataFrame:

    logger = get_logger(get_fred_data)
    try:
        data = pdr.DataReader(
            name=ticker,
            data_source="fred",
            start=start,
            end=end,
        )
        return data
    except Exception as exc:
        logger.warning(f"Download data from `fred` fail for ticker {ticker}")
        logger.exception(exc)
        return pd.DataFrame()
