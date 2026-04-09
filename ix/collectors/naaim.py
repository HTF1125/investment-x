"""NAAIM Exposure Index collector.

Fetches weekly active manager equity exposure data from NAAIM website.
Primary source: Excel download with data since inception.
Fallback: Scrape current reading from the exposure index page.
"""

from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

from ix.collectors.base import BaseCollector
from ix.db.conn import Session


class NAAIMExposureCollector(BaseCollector):
    name = "naaim"
    display_name = "NAAIM Exposure Index"
    schedule = "0 12 * * 4"  # Thursday noon
    category = "sentiment"

    INDEX_URL = "https://naaim.org/programs/naaim-exposure-index/"

    def collect(self, progress_cb=None) -> dict:
        inserted = 0
        errors = 0

        try:
            data = self._fetch_exposure_data()
            if data is None or data.empty:
                self.update_state(error="Failed to fetch NAAIM data")
                return {"inserted": 0, "updated": 0, "errors": 1, "message": "No data"}

            with Session() as db:
                if progress_cb:
                    progress_cb(1, 1, "Updating NAAIM_EXPOSURE")
                try:
                    self._upsert_timeseries(
                        db,
                        source="NAAIM",
                        code="NAAIM_EXPOSURE:PX_LAST",
                        source_code="NAAIM:Mean",
                        name="NAAIM Exposure Index",
                        category="Sentiment",
                        data=data,
                        frequency="W",
                        unit="percent",
                    )
                    inserted += 1
                except Exception as e:
                    self.logger.error(f"Error upserting NAAIM_EXPOSURE: {e}")
                    errors += 1

            last_date = str(data.index.max().date()) if not data.empty else None
            self.update_state(last_data_date=last_date)

        except Exception as e:
            self.logger.exception(f"NAAIM collector failed: {e}")
            self.update_state(error=str(e))
            return {"inserted": 0, "updated": 0, "errors": 1, "message": str(e)}

        return {
            "inserted": inserted,
            "updated": 0,
            "errors": errors,
            "message": f"NAAIM: {inserted} series updated",
        }

    def _fetch_exposure_data(self) -> pd.Series:
        """Try Excel download first, fall back to page scraping."""
        # Step 1: Find the Excel download link from the index page
        excel_url = self._find_excel_url()
        if excel_url:
            try:
                data = self._parse_excel(excel_url)
                if data is not None and not data.empty:
                    return data
            except Exception as e:
                self.logger.warning(f"Excel download failed: {e}")

        # Fallback: scrape current reading
        return self._scrape_current()

    def _find_excel_url(self) -> str:
        """Find the Excel download URL from the NAAIM page."""
        try:
            resp = requests.get(self.INDEX_URL, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Look for link containing "Data-since-Inception" or "xlsx"
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if "Data-since-Inception" in href or (
                    href.endswith(".xlsx") and "USE_Data" in href
                ):
                    if href.startswith("/"):
                        return f"https://naaim.org{href}"
                    return href

            # Broader search for any xlsx link
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if href.endswith(".xlsx") and "naaim" in href.lower():
                    return href

        except Exception as e:
            self.logger.warning(f"Could not find Excel URL: {e}")
        return None

    def _parse_excel(self, url: str) -> pd.Series:
        """Download and parse NAAIM Excel file."""
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()

        from io import BytesIO

        df = pd.read_excel(BytesIO(resp.content), engine="openpyxl")

        # Find date column and mean/average column
        date_col = None
        mean_col = None
        for c in df.columns:
            cl = str(c).lower().strip()
            if "date" in cl:
                date_col = c
            elif "mean" in cl or "average" in cl:
                mean_col = c

        if date_col is None or mean_col is None:
            # Try first two columns as fallback
            cols = list(df.columns)
            if len(cols) >= 2:
                date_col = cols[0]
                mean_col = cols[1]
            else:
                self.logger.error(f"Cannot identify columns: {list(df.columns)}")
                return None

        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col])
        df = df.set_index(date_col).sort_index()
        series = pd.to_numeric(df[mean_col], errors="coerce").dropna()
        series.name = "NAAIM Exposure Index"
        return series

    def _scrape_current(self) -> pd.Series:
        """Scrape the current week's exposure from the NAAIM page."""
        try:
            resp = requests.get(self.INDEX_URL, timeout=30)
            soup = BeautifulSoup(resp.text, "html.parser")

            # Look for table rows with date and exposure data
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 2:
                        try:
                            date_text = cells[0].get_text().strip()
                            val_text = cells[1].get_text().strip()
                            date = pd.to_datetime(date_text, errors="coerce")
                            val = float(val_text)
                            if pd.notna(date):
                                return pd.Series(
                                    [val],
                                    index=pd.DatetimeIndex([date]),
                                    name="NAAIM Exposure Index",
                                )
                        except (ValueError, TypeError):
                            continue

            self.logger.warning("Could not parse NAAIM exposure page")
            return None
        except Exception as e:
            self.logger.error(f"NAAIM scrape failed: {e}")
            return None
