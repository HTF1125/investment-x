"""CFTC Commitments of Traders (COT) report collector.

Fetches weekly futures positioning data from the CFTC website.
Uses the disaggregated report for physical commodities and the
Traders in Financial Futures (TFF) report for financial contracts.
Stores net/long/short positioning as Timeseries entries.
"""

import io
import zipfile
from datetime import datetime

import pandas as pd
import requests

from ix.collectors.base import BaseCollector
from ix.db.conn import Session


class CFTCCollector(BaseCollector):
    name = "cftc"
    display_name = "CFTC COT Reports"
    schedule = "0 18 * * 5"  # Friday 6 PM
    category = "positioning"

    # Financial futures use the TFF report
    FINANCIAL_CONTRACTS = {
        "SP500": {
            "cftc_code": "13874A",
            "name": "S&P 500 E-mini",
        },
        "NASDAQ": {
            "cftc_code": "20974A",
            "name": "Nasdaq 100 E-mini",
        },
        "UST10Y": {
            "cftc_code": "043602",
            "name": "10Y Treasury Note",
        },
        "UST2Y": {
            "cftc_code": "042601",
            "name": "2Y Treasury Note",
        },
        "EUR": {
            "cftc_code": "099741",
            "name": "Euro FX",
        },
        "JPY": {
            "cftc_code": "097741",
            "name": "Japanese Yen",
        },
        "USD": {
            "cftc_code": "098662",
            "name": "US Dollar Index",
        },
    }

    # Physical commodities use the disaggregated report
    COMMODITY_CONTRACTS = {
        "GOLD": {
            "cftc_code": "088691",
            "name": "Gold",
        },
        "OIL": {
            "cftc_code": "067651",
            "name": "Crude Oil WTI",
        },
    }

    # Report URLs
    TFF_URL = "https://www.cftc.gov/files/dea/history/fut_fin_txt_{year}.zip"
    DISAGG_URL = "https://www.cftc.gov/files/dea/history/fut_disagg_txt_{year}.zip"

    def collect(self, progress_cb=None) -> dict:
        inserted = 0
        errors = 0

        try:
            # Download both reports
            tff_df = self._download_report(self.TFF_URL, "TFF")
            disagg_df = self._download_report(self.DISAGG_URL, "disaggregated")

            all_contracts = len(self.FINANCIAL_CONTRACTS) + len(self.COMMODITY_CONTRACTS)
            total = all_contracts * 3  # 3 series per contract
            current = 0

            with Session() as db:
                # Process financial contracts from TFF report
                if tff_df is not None and not tff_df.empty:
                    for prefix, info in self.FINANCIAL_CONTRACTS.items():
                        count, err = self._process_contract(
                            db, tff_df, prefix, info,
                            long_col="Asset_Mgr_Positions_Long_All",
                            short_col="Asset_Mgr_Positions_Short_All",
                            fallback_long="Lev_Money_Positions_Long_All",
                            fallback_short="Lev_Money_Positions_Short_All",
                            progress_cb=progress_cb,
                            current=current, total=total,
                        )
                        inserted += count
                        errors += err
                        current += 3
                else:
                    self.logger.warning("No TFF data available")
                    errors += len(self.FINANCIAL_CONTRACTS)
                    current += len(self.FINANCIAL_CONTRACTS) * 3

                # Process commodity contracts from disaggregated report
                if disagg_df is not None and not disagg_df.empty:
                    for prefix, info in self.COMMODITY_CONTRACTS.items():
                        count, err = self._process_contract(
                            db, disagg_df, prefix, info,
                            long_col="M_Money_Positions_Long_All",
                            short_col="M_Money_Positions_Short_All",
                            fallback_long="Asset_Mgr_Positions_Long_All",
                            fallback_short="Asset_Mgr_Positions_Short_All",
                            progress_cb=progress_cb,
                            current=current, total=total,
                        )
                        inserted += count
                        errors += err
                        current += 3
                else:
                    self.logger.warning("No disaggregated data available")
                    errors += len(self.COMMODITY_CONTRACTS)

            self.update_state(last_data_date=str(datetime.now().date()))

        except Exception as e:
            self.logger.exception(f"CFTC collector failed: {e}")
            self.update_state(error=str(e))
            return {"inserted": 0, "updated": 0, "errors": 1, "message": str(e)}

        return {
            "inserted": inserted,
            "updated": 0,
            "errors": errors,
            "message": f"CFTC: {inserted} series updated, {errors} errors",
        }

    def _process_contract(
        self, db, df, prefix, info, *,
        long_col, short_col,
        fallback_long, fallback_short,
        progress_cb, current, total,
    ):
        """Process a single contract from the COT data."""
        inserted = 0
        errors = 0

        try:
            contract_df = df[
                df["CFTC_Contract_Market_Code"].str.strip() == info["cftc_code"]
            ]
            if contract_df.empty:
                self.logger.warning(f"No data for {prefix} ({info['cftc_code']})")
                return 0, 1

            contract_df = contract_df.copy()
            contract_df["date"] = pd.to_datetime(
                contract_df["Report_Date_as_YYYY-MM-DD"], errors="coerce"
            )
            contract_df = contract_df.dropna(subset=["date"])
            contract_df = contract_df.sort_values("date").drop_duplicates(
                subset=["date"], keep="last"
            )
            contract_df = contract_df.set_index("date")

            # Pick position columns
            lc = long_col if long_col in contract_df.columns else fallback_long
            sc = short_col if short_col in contract_df.columns else fallback_short

            if lc not in contract_df.columns or sc not in contract_df.columns:
                self.logger.warning(f"Missing position columns for {prefix}")
                return 0, 1

            long_series = pd.to_numeric(contract_df[lc], errors="coerce").dropna()
            short_series = pd.to_numeric(contract_df[sc], errors="coerce").dropna()
            net_series = long_series - short_series

            for suffix, series in [("LONG", long_series), ("SHORT", short_series), ("NET", net_series)]:
                code = f"CFTC_{prefix}_{suffix}"
                step = current + inserted + 1
                if progress_cb:
                    progress_cb(step, total, f"Updating {code}")

                self._upsert_timeseries(
                    db,
                    source="CFTC",
                    code=code,
                    source_code=f"{prefix}:{suffix}",
                    name=f"{info['name']} {suffix.title()} Positioning",
                    category="Positioning",
                    data=series,
                    frequency="W",
                    unit="contracts",
                )
                inserted += 1

        except Exception as e:
            self.logger.error(f"Error processing {prefix}: {e}")
            errors += 1

        return inserted, errors

    def _download_report(self, url_template: str, label: str) -> pd.DataFrame:
        """Download and parse a CFTC report (current + previous year)."""
        year = datetime.now().year
        frames = []

        for y in [year - 1, year]:
            url = url_template.format(year=y)
            try:
                self.logger.info(f"Downloading CFTC {label} data from {url}")
                resp = requests.get(url, timeout=60)
                if resp.status_code != 200:
                    self.logger.warning(f"CFTC download failed for {y}: HTTP {resp.status_code}")
                    continue

                with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                    for fname in zf.namelist():
                        if fname.endswith(".txt"):
                            with zf.open(fname) as f:
                                df = pd.read_csv(f, low_memory=False)
                                frames.append(df)
            except Exception as e:
                self.logger.warning(f"Failed to download CFTC {label} {y}: {e}")

        if not frames:
            return None
        return pd.concat(frames, ignore_index=True)
