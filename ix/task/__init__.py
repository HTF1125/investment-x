import pandas as pd
from ix.misc import get_yahoo_data
from ix.misc import get_bloomberg_data
from ix.misc import get_logger
from ix import db
from ix import misc


logger = get_logger(__name__)


def run():

    update_price_data()
    db.Performance.delete_all()
    update_price_performance()
    update_economic_calendar()


def update_price_data():
    logger.debug("Initialization complete.")

    for ticker in db.Ticker.find_all():

        px_last = db.PxLast.find_one(db.PxLast.code == ticker.code).run()
        if px_last is None:
            px_last = db.PxLast(code=ticker.code).create()
        data = None

        if ticker.source == "YAHOO":
            if ticker.yahoo is None:
                logger.debug(f"Skipping {ticker.code}: No Yahoo ID.")
                continue
            data = get_yahoo_data(code=ticker.yahoo)["Adj Close"]
            logger.debug(f"Fetched data from Yahoo for {ticker.code}")

        elif ticker.source == "BLOOMBERG":
            if ticker.bloomberg is None:
                logger.debug(f"Skipping {ticker.code}: No Bloomberg ID.")
                continue
            data = get_bloomberg_data(code=ticker.bloomberg)
            if data.empty:
                continue
            data = data.iloc[:, 0]
            logger.debug(f"Fetched data from Bloomberg for {ticker.code}")

        else:
            logger.debug(f"Skipping {ticker.code}: Unsupported source {ticker.source}.")
            continue

        if data is None or data.empty:
            logger.debug(f"No data found for {ticker.code}, skipping.")
            continue

        data = data.combine_first(pd.Series(px_last.data)).loc[
            : misc.last_business_day()
        ]
        px_last.set({"data": data.to_dict()})

    logger.debug("Timeseries update process completed.")


def update_economic_calendar():

    import investpy
    from ix.misc import as_date, onemonthbefore, onemonthlater
    from ix.db import EconomicCalendar
    import pandas as pd

    data = investpy.economic_calendar(
        from_date=as_date(onemonthbefore(), "%d/%m/%Y"),
        to_date=as_date(onemonthlater(), "%d/%m/%Y"),
    )

    if not isinstance(data, pd.DataFrame):
        return
    data["date"] = pd.to_datetime(data["date"], dayfirst=True).dt.strftime("%Y-%m-%d")
    data = data.drop(columns=["id"])

    EconomicCalendar.delete_all()
    objs = []
    for record in data.to_dict("records"):
        record = {str(key): value for key, value in record.items()}
        objs.append(EconomicCalendar(**record))
    EconomicCalendar.insert_many(objs)


def update_price_performance():

    pxlasts = []
    asofdate = misc.last_business_day().date()

    for ticker in db.Ticker.find_many(db.Ticker.source == "YAHOO").run():
        if ticker.source == "YAHOO":
            pxlast = db.PxLast.find_one(db.PxLast.code == ticker.code).run()
            if pxlast is None:
                continue
            pxlast_data = pd.Series(data=pxlast.data, name=pxlast.code)
            pxlasts.append(pxlast_data)
    pxlasts = pd.concat(pxlasts, axis=1)
    pxlasts.index = pd.to_datetime(pxlasts.index)
    pxlasts = pxlasts.sort_index().loc[:asofdate].resample("D").last().ffill()


    print(f"update performance for {pxlasts.index[-1]}")
    for code in pxlasts:
        pxlast = pxlasts[code]
        level = pxlast.iloc[-1]
        pct_chg = (level / pxlast).sub(1).mul(100).round(2)
        pct_chg_1d = pct_chg.get(asofdate - pd.offsets.BusinessDay(1), None)
        pct_chg_1w = pct_chg.get(asofdate - pd.DateOffset(days=7), None)
        pct_chg_1m = pct_chg.get(asofdate - pd.DateOffset(months=1), None)
        pct_chg_3m = pct_chg.get(asofdate - pd.DateOffset(months=3), None)
        pct_chg_6m = pct_chg.get(asofdate - pd.DateOffset(months=6), None)
        pct_chg_1y = pct_chg.get(asofdate - pd.DateOffset(months=12), None)
        pct_chg_3y = pct_chg.get(asofdate - pd.DateOffset(months=12 * 3), None)
        pct_chg_mtd = pct_chg.get(
            asofdate - pd.offsets.MonthBegin() - pd.DateOffset(days=1), None
        )
        pct_chg_ytd = pct_chg.get(
            asofdate - pd.offsets.YearBegin() - pd.DateOffset(days=1), None
        )

        # Check if a Performance document with the same date and code exists
        existing_performance = db.Performance.find_one(
            db.Performance.code == ticker.code, db.Performance.date == asofdate
        ).run()

        performance_data = {
            "code": code,
            "date": asofdate,
            "level": level,
            "pct_chg_1d": pct_chg_1d,
            "pct_chg_1w": pct_chg_1w,
            "pct_chg_1m": pct_chg_1m,
            "pct_chg_3m": pct_chg_3m,
            "pct_chg_6m": pct_chg_6m,
            "pct_chg_1y": pct_chg_1y,
            "pct_chg_3y": pct_chg_3y,
            "pct_chg_mtd": pct_chg_mtd,
            "pct_chg_ytd": pct_chg_ytd,
        }
        try:
            if existing_performance:
                # Update the existing document
                existing_performance.update({"$set": performance_data})
                print(f"Updated Performance for {code} on {asofdate}")
            else:
                # Create a new document
                new_performance = db.Performance(**performance_data)
                new_performance.create()
                print(f"Created new Performance for {code} on {asofdate}")
        except Exception as exc:
            print(exc)
            print(performance_data)




import requests
from typing import Dict, List, Optional
from datetime import date
import yfinance as yf
from ix.misc import get_bloomberg_data
from ix.misc import get_logger


logger = get_logger(__name__)


class Task:
    def __init__(self, base_url: str):
        """
        Initialize the Task class.

        Args:
            base_url (str): The base URL for the API.
        """
        self.base_url = base_url
        self.session = requests.Session()

    def update_pxlast_api(self, ticker_code: str, update_pxlast: Dict[date, float]) -> None:
        """
        Update the PxLast values for a given ticker via the API.

        Args:
            ticker_code (str): The ticker code to update.
            update_pxlast (Dict[date, float]): Dictionary of date-value pairs to update.
        """
        if not update_pxlast:
            logger.error(f"Update data for ticker '{ticker_code}' is empty.")
            return

        endpoint = f"{self.base_url}/api/data/tickers/update_pxlast/{ticker_code}"
        payload = {
            "update_pxlast": {
                key.strftime("%Y-%m-%d"): round(float(value), 2)
                for key, value in update_pxlast.items()
            }
        }

        try:
            response = self.session.put(endpoint, json=payload)
            response.raise_for_status()
            logger.info(f"Successfully updated PxLast for ticker '{ticker_code}'")
        except requests.exceptions.RequestException as err:
            logger.error(f"Failed to update PxLast for ticker '{ticker_code}': {err}")
            if response is not None:
                logger.error(f"Response content: {response.text}")

    def fetch_all_tickers(self) -> Optional[List[Dict]]:
        """
        Fetch all tickers from the API.

        Returns:
            List[Dict]: A list of tickers or None if fetching fails.
        """
        endpoint = f"{self.base_url}/api/data/tickers/all"
        try:
            response = self.session.get(endpoint)
            response.raise_for_status()
            tickers = response.json()
            logger.info(f"Fetched {len(tickers)} tickers.")
            return tickers
        except requests.exceptions.RequestException as err:
            logger.error(f"Failed to fetch tickers: {err}")
            return None

    def process_yahoo_ticker(self, ticker: Dict) -> Optional[Dict[date, float]]:
        """
        Process a Yahoo Finance ticker and retrieve its adjusted close prices.

        Args:
            ticker (Dict): Ticker details from the API.

        Returns:
            Dict[date, float]: Date-value pairs of adjusted close prices or None.
        """
        code = ticker.get("yahoo")
        if not code:
            logger.warning(f"No Yahoo code found for ticker: {ticker.get('code')}")
            return None

        try:
            data = yf.download(code, progress=False)["Adj Close"]
            return {key.to_pydatetime().date(): float(value) for key, value in data.items()}
        except Exception as err:
            logger.error(f"Error processing Yahoo ticker '{code}': {err}")
            return None

    def process_bloomberg_ticker(self, ticker: Dict) -> Optional[Dict[date, float]]:
        """
        Process a Bloomberg ticker and retrieve its data.

        Args:
            ticker (Dict): Ticker details from the API.

        Returns:
            Dict[date, float]: Date-value pairs of Bloomberg data or None.
        """
        code = ticker.get("bloomberg")
        if not code:
            logger.warning(f"No Bloomberg code found for ticker: {ticker.get('code')}")
            return None

        try:
            data = get_bloomberg_data(code=code)
            if data.empty:
                logger.warning(f"No data found for Bloomberg ticker '{code}'.")
                return None
            return {key.to_pydatetime().date(): float(value) for key, value in data.iloc[:, 0].items()}
        except Exception as err:
            logger.error(f"Error processing Bloomberg ticker '{code}': {err}")
            return None

    def run(self):
        """
        Main method to fetch tickers and update their PxLast data.
        """
        tickers = self.fetch_all_tickers()
        if not tickers:
            logger.error("No tickers available for processing.")
            return

        for ticker in tickers:
            source = ticker.get("source")
            update_data = None

            if source == "YAHOO":
                update_data = self.process_yahoo_ticker(ticker)
            elif source == "BLOOMBERG":
                update_data = self.process_bloomberg_ticker(ticker)
            else:
                logger.warning(f"Unknown source '{source}' for ticker: {ticker.get('code')}")
                continue

            if update_data:
                self.update_pxlast_api(ticker["code"], update_data)


# Example usage:
if __name__ == "__main__":
    base_url = "https://port-0-investmentx-ghdys32bls2zef7e.sel5.cloudtype.app"
    task = Task(base_url)
    task.run()
