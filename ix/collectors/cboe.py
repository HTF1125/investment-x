"""CBOE Put/Call Ratio and VIX Term Structure collector.

Uses yfinance for VIX3M (term structure) and falls back to CBOE CDN with
browser-like headers for put/call CSVs. If CBOE blocks the request, skips
gracefully — the VIX term structure metrics still work from existing VIX data.
"""

from datetime import datetime

import pandas as pd
import requests

from ix.collectors.base import BaseCollector
from ix.db.conn import Session


class CBOECollector(BaseCollector):
    name = "cboe"
    display_name = "CBOE Put/Call & VIX"
    schedule = "0 20 * * 1-5"  # Weekdays 8 PM
    category = "sentiment"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/csv,text/plain,*/*",
        "Referer": "https://www.cboe.com/",
    }

    PC_URLS = {
        "CBOE_EQUITY_PC": {
            "url": "https://cdn.cboe.com/api/global/us_options/market_statistics/daily/equity_put_call_ratio.csv",
            "name": "CBOE Equity Put/Call Ratio",
            "source_code": "CBOE:EQUITY_PC",
        },
        "CBOE_INDEX_PC": {
            "url": "https://cdn.cboe.com/api/global/us_options/market_statistics/daily/index_put_call_ratio.csv",
            "name": "CBOE Index Put/Call Ratio",
            "source_code": "CBOE:INDEX_PC",
        },
        "CBOE_TOTAL_PC": {
            "url": "https://cdn.cboe.com/api/global/us_options/market_statistics/daily/total_put_call_ratio.csv",
            "name": "CBOE Total Put/Call Ratio",
            "source_code": "CBOE:TOTAL_PC",
        },
    }

    def collect(self, progress_cb=None) -> dict:
        inserted = 0
        errors = 0
        steps = 4  # PC ratios + VIX3M fetch + VIX term structure
        current = 0

        with Session() as db:
            # 1) Try CBOE put/call CSVs (may be blocked)
            current += 1
            if progress_cb:
                progress_cb(current, steps, "Fetching put/call ratios")
            pc_count = self._fetch_put_call_ratios(db)
            inserted += pc_count

            # 2) Fetch VIX3M via yfinance and store
            current += 1
            if progress_cb:
                progress_cb(current, steps, "Fetching VIX3M")
            try:
                vix3m_count = self._fetch_vix3m(db)
                inserted += vix3m_count
            except Exception as e:
                self.logger.error(f"VIX3M fetch error: {e}")
                errors += 1

            # 3) Compute VIX term structure from existing data
            current += 1
            if progress_cb:
                progress_cb(current, steps, "Computing VIX term structure")
            try:
                vix_count = self._compute_vix_term_structure(db)
                inserted += vix_count
            except Exception as e:
                self.logger.error(f"VIX term structure error: {e}")
                errors += 1

            current += 1
            if progress_cb:
                progress_cb(current, steps, "Done")

        self.update_state(last_data_date=str(datetime.now().date()))
        return {
            "inserted": inserted,
            "updated": 0,
            "errors": errors,
            "message": f"CBOE: {inserted} series updated",
        }

    def _fetch_put_call_ratios(self, db) -> int:
        """Try to fetch CBOE put/call ratio CSVs."""
        count = 0
        for code, info in self.PC_URLS.items():
            try:
                series = self._fetch_pc_csv(info["url"])
                if series is not None and not series.empty:
                    self._upsert_timeseries(
                        db,
                        source="CBOE",
                        code=code,
                        source_code=info["source_code"],
                        name=info["name"],
                        category="Sentiment",
                        data=series,
                        unit="ratio",
                    )
                    count += 1
                else:
                    self.logger.warning(f"No data for {code} (CBOE may be blocking)")
            except Exception as e:
                self.logger.error(f"Error fetching {code}: {e}")
        return count

    def _fetch_pc_csv(self, url: str) -> pd.Series:
        """Download and parse a CBOE put/call ratio CSV."""
        try:
            resp = requests.get(url, timeout=30, headers=self.HEADERS)
            if resp.status_code != 200:
                return None

            from io import StringIO
            df = pd.read_csv(StringIO(resp.text))

            date_col = None
            ratio_col = None
            for c in df.columns:
                cl = c.lower().strip()
                if "date" in cl or "trade_date" in cl:
                    date_col = c
                elif "ratio" in cl or "p/c" in cl:
                    ratio_col = c

            if date_col is None:
                date_col = df.columns[0]
            if ratio_col is None:
                ratio_col = df.columns[-1]

            df["date"] = pd.to_datetime(df[date_col], errors="coerce")
            df = df.dropna(subset=["date"])
            df = df.set_index("date").sort_index()
            return pd.to_numeric(df[ratio_col], errors="coerce").dropna()
        except Exception as e:
            self.logger.warning(f"Failed to parse PC ratio from {url}: {e}")
            return None

    def _fetch_vix3m(self, db) -> int:
        """Fetch VIX3M (3-month VIX) via yfinance and store as timeseries."""
        import yfinance as yf

        ticker = yf.Ticker("^VIX3M")
        hist = ticker.history(period="max")
        if hist.empty:
            self.logger.warning("No VIX3M data from yfinance")
            return 0

        series = hist["Close"].dropna()
        idx = pd.DatetimeIndex(series.index)
        if idx.tz is not None:
            idx = idx.tz_localize(None)
        series.index = idx.normalize()

        self._upsert_timeseries(
            db,
            source="Yahoo",
            code="VIX3M INDEX:PX_LAST",
            source_code="^VIX3M:Adj Close",
            name="CBOE 3-Month Volatility Index (VIX3M), Close",
            category="Volatility",
            data=series,
            unit="index",
        )
        return 1

    def _compute_vix_term_structure(self, db) -> int:
        """Compute VIX contango ratio and term slope from VIX & VIX3M data."""
        from ix.db.models import Timeseries

        count = 0

        # Get VIX close
        vix_ts = (
            db.query(Timeseries)
            .filter(Timeseries.code == "VIX INDEX:PX_LAST")
            .first()
        )
        if vix_ts is None:
            self.logger.info("No VIX timeseries found; skipping term structure")
            return 0

        vix3m_ts = (
            db.query(Timeseries)
            .filter(Timeseries.code == "VIX3M INDEX:PX_LAST")
            .first()
        )
        if vix3m_ts is None:
            self.logger.info("No VIX3M timeseries found; skipping term structure")
            return 0

        vix_data = vix_ts.data
        vix3m_data = vix3m_ts.data

        if vix_data is None or vix_data.empty or vix3m_data is None or vix3m_data.empty:
            return 0

        # Align and compute
        combined = pd.concat([vix_data, vix3m_data], axis=1, keys=["VIX", "VIX3M"])
        combined = combined.dropna()
        if combined.empty:
            return 0

        # Contango ratio = VIX3M / VIX (>1 = contango = normal)
        contango = combined["VIX3M"] / combined["VIX"]
        contango = contango.replace([float("inf"), float("-inf")], pd.NA).dropna()

        self._upsert_timeseries(
            db,
            source="CBOE",
            code="VIX_CONTANGO_RATIO",
            source_code="CBOE:VIX_CONTANGO",
            name="VIX Contango Ratio (VIX3M/VIX)",
            category="Volatility",
            data=contango,
            unit="ratio",
        )
        count += 1

        # Term slope = VIX3M - VIX (positive = contango)
        slope = combined["VIX3M"] - combined["VIX"]
        self._upsert_timeseries(
            db,
            source="CBOE",
            code="VIX_TERM_SLOPE",
            source_code="CBOE:VIX_SLOPE",
            name="VIX Term Structure Slope (VIX3M - VIX)",
            category="Volatility",
            data=slope,
            unit="points",
        )
        count += 1

        return count
