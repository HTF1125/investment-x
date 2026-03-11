"""FINRA dark pool / short interest data collector.

Fetches ATS transparency data and short interest reports from FINRA.
"""

import time
from datetime import datetime
from io import StringIO

import pandas as pd
import requests

from ix.collectors.base import BaseCollector
from ix.db.conn import Session


class FINRADarkPoolCollector(BaseCollector):
    name = "finra_darkpool"
    display_name = "FINRA Dark Pool"
    schedule = "0 8 1,16 * *"  # 1st and 16th of each month
    category = "filings"

    # FINRA short interest is published twice monthly
    SHORT_INTEREST_URL = "https://api.finra.org/data/group/otcMarket/name/shortInterest"

    TRACKED_SYMBOLS = ["SPY", "QQQ", "IWM", "DIA", "AAPL", "TSLA", "NVDA", "MSFT"]

    def collect(self, progress_cb=None) -> dict:
        inserted = 0
        errors = 0

        total = len(self.TRACKED_SYMBOLS) + 1
        current = 0

        with Session() as db:
            # Fetch short interest for tracked symbols
            for symbol in self.TRACKED_SYMBOLS:
                current += 1
                if progress_cb:
                    progress_cb(current, total, f"Fetching short interest: {symbol}")

                try:
                    series = self._fetch_short_interest(symbol)
                    if series is not None and not series.empty:
                        code = f"FINRA_SHORT_{symbol}"
                        self._upsert_timeseries(
                            db,
                            source="FINRA",
                            code=code,
                            source_code=f"FINRA:{symbol}:SHORT",
                            name=f"{symbol} Short Interest",
                            category="Dark Pool",
                            data=series,
                            frequency=None,
                            unit="shares",
                        )
                        inserted += 1
                except Exception as e:
                    self.logger.error(f"Error fetching short interest for {symbol}: {e}")
                    errors += 1
                time.sleep(0.5)

            current += 1
            if progress_cb:
                progress_cb(current, total, "Done")

        self.update_state(last_data_date=str(datetime.now().date()))
        return {
            "inserted": inserted,
            "updated": 0,
            "errors": errors,
            "message": f"FINRA: {inserted} short interest series updated",
        }

    def _fetch_short_interest(self, symbol: str) -> pd.Series:
        """Fetch short interest data for a symbol from FINRA API."""
        try:
            # FINRA API requires specific format
            url = "https://api.finra.org/data/group/otcMarket/name/shortInterest"
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            payload = {
                "fields": ["settlementDate", "currentShortPositionQuantity"],
                "dateRangeFilters": [],
                "domainFilters": [
                    {"fieldName": "symbolCode", "values": [symbol]}
                ],
                "compareFilters": [],
                "orFilters": [],
                "limit": 100,
                "offset": 0,
                "sortFields": ["-settlementDate"],
            }

            resp = requests.post(url, json=payload, headers=headers, timeout=30)

            if resp.status_code == 200:
                data = resp.json()
                if data:
                    records = {}
                    for row in data:
                        date_str = row.get("settlementDate", "")
                        quantity = row.get("currentShortPositionQuantity", 0)
                        if date_str and quantity:
                            records[date_str] = float(quantity)

                    if records:
                        series = pd.Series(records)
                        series.index = pd.to_datetime(series.index)
                        return series.sort_index()

            # Fallback: try CSV download
            return self._fetch_short_interest_csv(symbol)

        except Exception as e:
            self.logger.warning(f"FINRA API failed for {symbol}: {e}")
            return self._fetch_short_interest_csv(symbol)

    def _fetch_short_interest_csv(self, symbol: str) -> pd.Series:
        """Fallback: try to get short interest from alternative source."""
        try:
            # Try NASDAQ short interest page
            url = f"https://www.nasdaqtrader.com/trader.aspx?id=ShortInterest&name={symbol}"
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200 and "Settlement Date" in resp.text:
                dfs = pd.read_html(StringIO(resp.text))
                for df in dfs:
                    if "Settlement Date" in df.columns or any("settlement" in str(c).lower() for c in df.columns):
                        date_col = [c for c in df.columns if "date" in str(c).lower()][0]
                        si_col = [c for c in df.columns if "short" in str(c).lower() and "interest" in str(c).lower()]
                        if si_col:
                            df["date"] = pd.to_datetime(df[date_col], errors="coerce")
                            df = df.dropna(subset=["date"]).set_index("date")
                            return pd.to_numeric(df[si_col[0]], errors="coerce").dropna()
        except Exception as e:
            self.logger.warning(f"CSV fallback failed for {symbol}: {e}")

        return None
