"""AAII Investor Sentiment Survey collector.

Scrapes weekly bull/bear/neutral sentiment data from AAII website.
Stores as Timeseries entries.
"""

from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

from ix.collectors.base import BaseCollector
from ix.db.conn import Session


class AAIISentimentCollector(BaseCollector):
    name = "aaii"
    display_name = "AAII Sentiment Survey"
    schedule = "0 12 * * 4"  # Thursday noon
    category = "sentiment"

    SURVEY_URL = "https://www.aaii.com/sentimentsurvey/sent_results"
    HISTORICAL_URL = "https://www.aaii.com/files/surveys/sentiment.xls"

    SERIES = [
        ("AAII_BULL", "Bullish", "Bullish %"),
        ("AAII_BEAR", "Bearish", "Bearish %"),
        ("AAII_NEUTRAL", "Neutral", "Neutral %"),
        ("AAII_BULL_BEAR_SPREAD", "Spread", "Bull-Bear Spread"),
    ]

    def collect(self, progress_cb=None) -> dict:
        inserted = 0
        errors = 0

        try:
            df = self._fetch_sentiment_data()
            if df is None or df.empty:
                self.update_state(error="Failed to fetch AAII data")
                return {"inserted": 0, "updated": 0, "errors": 1, "message": "No data"}

            total = len(self.SERIES)
            with Session() as db:
                for i, (code, suffix, label) in enumerate(self.SERIES):
                    if progress_cb:
                        progress_cb(i + 1, total, f"Updating {code}")
                    try:
                        if suffix == "Spread":
                            series = df["Bullish"] - df["Bearish"]
                        else:
                            series = df[suffix]
                        series = series.dropna()

                        self._upsert_timeseries(
                            db,
                            source="AAII",
                            code=code,
                            source_code=f"AAII:{suffix}",
                            name=f"AAII {label}",
                            category="Sentiment",
                            data=series,
                            frequency="W",
                            unit="percent",
                        )
                        inserted += 1
                    except Exception as e:
                        self.logger.error(f"Error processing {code}: {e}")
                        errors += 1

            last_date = str(df.index.max().date()) if not df.empty else None
            self.update_state(last_data_date=last_date)

        except Exception as e:
            self.logger.exception(f"AAII collector failed: {e}")
            self.update_state(error=str(e))
            return {"inserted": 0, "updated": 0, "errors": 1, "message": str(e)}

        return {
            "inserted": inserted,
            "updated": 0,
            "errors": errors,
            "message": f"AAII: {inserted} series updated",
        }

    def _fetch_sentiment_data(self) -> pd.DataFrame:
        """Try historical Excel first, fall back to page scraping."""
        # Try Excel download
        try:
            resp = requests.get(self.HISTORICAL_URL, timeout=30)
            if resp.status_code == 200:
                df = pd.read_excel(
                    resp.content,
                    sheet_name=0,
                    skiprows=3,
                    engine="openpyxl",
                )
                # Typical columns: Date, Bullish, Neutral, Bearish
                date_col = [c for c in df.columns if "date" in str(c).lower()]
                if date_col:
                    df = df.rename(columns={date_col[0]: "Date"})
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                df = df.dropna(subset=["Date"])
                df = df.set_index("Date").sort_index()

                # Normalize column names
                col_map = {}
                for c in df.columns:
                    cl = str(c).lower().strip()
                    if "bull" in cl:
                        col_map[c] = "Bullish"
                    elif "bear" in cl:
                        col_map[c] = "Bearish"
                    elif "neutral" in cl:
                        col_map[c] = "Neutral"
                df = df.rename(columns=col_map)

                for col in ["Bullish", "Bearish", "Neutral"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce") * 100
                return df[["Bullish", "Bearish", "Neutral"]].dropna()
        except Exception as e:
            self.logger.warning(f"Excel download failed, trying scrape: {e}")

        # Fallback: scrape current page
        return self._scrape_current()

    def _scrape_current(self) -> pd.DataFrame:
        """Scrape the current week's sentiment from the AAII website."""
        try:
            resp = requests.get(self.SURVEY_URL, timeout=30)
            soup = BeautifulSoup(resp.text, "html.parser")

            # Look for table with sentiment data
            tables = soup.find_all("table")
            for table in tables:
                text = table.get_text().lower()
                if "bullish" in text and "bearish" in text:
                    rows = table.find_all("tr")
                    data = {}
                    for row in rows:
                        cells = row.find_all(["td", "th"])
                        if len(cells) >= 2:
                            label = cells[0].get_text().strip().lower()
                            value = cells[1].get_text().strip().replace("%", "")
                            try:
                                val = float(value)
                                if "bull" in label:
                                    data["Bullish"] = val
                                elif "bear" in label:
                                    data["Bearish"] = val
                                elif "neutral" in label:
                                    data["Neutral"] = val
                            except ValueError:
                                continue

                    if data:
                        today = pd.Timestamp.now().normalize()
                        return pd.DataFrame([data], index=pd.DatetimeIndex([today]))

            self.logger.warning("Could not parse AAII sentiment page")
            return None
        except Exception as e:
            self.logger.error(f"AAII scrape failed: {e}")
            return None
