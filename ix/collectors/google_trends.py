"""Google Trends collector for financial fear/sentiment terms.

Uses pytrends to fetch weekly search interest for key financial terms.
"""

import time
from datetime import datetime

import pandas as pd

from ix.collectors.base import BaseCollector
from ix.db.conn import Session


class GoogleTrendsCollector(BaseCollector):
    name = "google_trends"
    display_name = "Google Trends"
    schedule = "0 6 * * 0"  # Sunday 6 AM
    category = "sentiment"

    TERMS = {
        "recession": {"code": "GTREND_RECESSION", "name": "Google Trends: Recession"},
        "inflation": {"code": "GTREND_INFLATION", "name": "Google Trends: Inflation"},
        "stock market crash": {"code": "GTREND_STOCK_CRASH", "name": "Google Trends: Stock Market Crash"},
        "bear market": {"code": "GTREND_BEAR_MARKET", "name": "Google Trends: Bear Market"},
        "fed rate cut": {"code": "GTREND_FED_RATE_CUT", "name": "Google Trends: Fed Rate Cut"},
        "unemployment": {"code": "GTREND_UNEMPLOYMENT", "name": "Google Trends: Unemployment"},
    }

    def collect(self, progress_cb=None) -> dict:
        inserted = 0
        errors = 0

        try:
            from pytrends.request import TrendReq
        except ImportError:
            self.update_state(error="pytrends not installed")
            return {"inserted": 0, "updated": 0, "errors": 1, "message": "pytrends not installed"}

        pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 30))
        total = len(self.TERMS)
        current = 0

        with Session() as db:
            for term, info in self.TERMS.items():
                current += 1
                if progress_cb:
                    progress_cb(current, total, f"Fetching '{term}'")

                try:
                    pytrends.build_payload([term], timeframe="today 5-y", geo="US")
                    df = pytrends.interest_over_time()

                    if df is not None and not df.empty and term in df.columns:
                        series = df[term].astype(float)
                        series.index = pd.to_datetime(series.index)

                        self._upsert_timeseries(
                            db,
                            source="GoogleTrends",
                            code=info["code"],
                            source_code=f"GT:{term}",
                            name=info["name"],
                            category="Sentiment",
                            data=series,
                            frequency="W",
                            unit="index",
                        )
                        inserted += 1
                    else:
                        self.logger.warning(f"No data returned for '{term}'")

                    # Respect rate limits
                    time.sleep(3)

                except Exception as e:
                    self.logger.error(f"Error fetching '{term}': {e}")
                    errors += 1
                    time.sleep(5)  # Longer wait on error

        self.update_state(last_data_date=str(datetime.now().date()))
        return {
            "inserted": inserted,
            "updated": 0,
            "errors": errors,
            "message": f"Google Trends: {inserted}/{total} terms updated",
        }
