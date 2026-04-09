from __future__ import annotations

import pandas as pd

from ix.db.query import Series, MultiSeries
from ix.common.data.transforms import Offset, MonthEndOffset, daily_ffill
from ix.core.indicators.growth import NumOfOECDLeadingPositiveMoM
from ix.core.indicators.growth import NumOfPmiMfgPositiveMoM, NumOfPmiServicesPositiveMoM
from ix.core.indicators.fci import financial_conditions_us
from ix.core.indicators.liquidity import m2_world_total


def macro_data() -> pd.DataFrame:
    """Macro dashboard indicators combined into a single DataFrame."""
    components: dict[str, pd.Series] = {}

    acwi = Series("ACWI US EQUITY:PX_LAST", freq="ME")
    if not acwi.empty:
        components["ACWI YoY"] = acwi.ffill().pct_change(12).mul(100)
    rty = Series("RTY INDEX:PX_LAST", freq="ME")
    if not rty.empty:
        components["Russell2000 YoY"] = rty.ffill().pct_change(12).mul(100)

    components["OECD CLI Diffusion Index"] = NumOfOECDLeadingPositiveMoM()
    components["PMI Manufacturing Diffusion Index"] = NumOfPmiMfgPositiveMoM()
    components["PMI Services Diffusion Index"] = NumOfPmiServicesPositiveMoM()

    cpi = Series("USPR1980783:PX_LAST", freq="ME")
    if not cpi.empty:
        components["US CPI YoY"] = cpi.ffill().pct_change(12).mul(100)
    tw_exp = Series("TW.FTEXP")
    if not tw_exp.empty:
        components["Taiwan Exports YoY"] = tw_exp.pct_change(12) * 100
    sg_exp = Series("SGFT1039935")
    if not sg_exp.empty:
        components["Singapore Exports YoY"] = sg_exp.pct_change(12) * 100
    kr_exp = Series("KR.FTEXP")
    if not kr_exp.empty:
        components["Korea Exports YoY"] = kr_exp.pct_change(12) * 100
    ppi = Series("USPR7664543:PX_LAST", freq="ME")
    if not ppi.empty:
        components["US PPI YoY"] = ppi.ffill().pct_change(12).mul(100)
    if not cpi.empty and not ppi.empty:
        components["GAP(CPI-PPI)"] = (
            cpi.ffill().pct_change(12).mul(100)
            - ppi.ffill().pct_change(12).mul(100)
        )
    xlp = Series("XLP US EQUITY:PX_LAST")
    spy = Series("SPY US EQUITY:PX_LAST")
    if not xlp.empty and not spy.empty:
        components["Staples/S&P500 YoY"] = xlp.div(spy).pct_change(250).mul(100)

    fci = financial_conditions_us()
    if not fci.empty:
        components["Financial Conditions (US, 26W Lead)"] = Offset(fci.mul(100), days=26)

    ism_pmi = Series("ISMPMI_M:PX_LAST")
    if not ism_pmi.empty:
        components["ISM Manufacturing PMI"] = ism_pmi

    m2 = m2_world_total()
    if not m2.empty:
        components["Global M2 YoY (%, 9M Lead)"] = Offset(m2.pct_change(12), months=9) * 100

    cesi = Series("USFXCESIUSD:PX_LAST")
    if not cesi.empty:
        components["Citi Economic Surprise Index (US)"] = cesi

    dxy = Series("DXY Index:PX_LAST", freq="W-Fri")
    if not dxy.empty:
        components["Dollar deviation from ST Trend (%, 10W Lead)"] = Offset(
            dxy.rolling(30).mean() - dxy, days=70,
        )
    ust10 = Series("TRYUS10Y:PX_YTM", freq="W-Fri")
    if not ust10.empty:
        components["UST10Y deviation from Trend (%, 10W Lead)"] = (
            Offset(ust10.rolling(30).mean() - ust10, days=70) * 100
        )
    ust10d = Series("TRYUS10Y:PX_YTM")
    ust3y = Series("TRYUS3Y:PX_LAST")
    if not ust10d.empty and not ust3y.empty:
        components["UST10-3Y Spread (bps)"] = ust10d.sub(ust3y).mul(100)
    loans = Series("FRBBCABLBA@US:PX_LAST", freq="W-Fri")
    if not loans.empty:
        components["Loans & Leases in Bank Credit YoY"] = loans.ffill().pct_change(52).mul(100)
    sloos = Series("USSU0486263", freq="ME")
    if not sloos.empty:
        components["SLOOS, C&I Standards Large & Medium Firms (12M Lead)"] = MonthEndOffset(
            sloos.ffill(), 12
        )
    adp = Series("USLM0985981")
    if not adp.empty:
        components["ADP Payroll MoM"] = adp.diff()
    nfp = Series("BLSCES0000000001:PX_LAST")
    if not nfp.empty:
        components["NonFarm Payroll MoM"] = nfp.diff()
    nfp_priv = Series("BLSCES0500000001:PX_LAST")
    if not nfp_priv.empty:
        components["NonFarm Payroll (Private) MoM"] = nfp_priv.diff()
    nfib = Series("USSU0062562:PX_LAST")
    if not nfib.empty:
        components["NFIB Actual 3 Month Earnings Change YoY"] = nfib.diff(12)

    if not components:
        return pd.DataFrame()
    return MultiSeries(**components)


# ── Seasonality (merged from seasonality.py) ────────────────────────────────


def _prepare_pivot(series: pd.Series, exclude_years=None, rebase: bool = False) -> pd.DataFrame:
    s = daily_ffill(series)
    s.index = pd.to_datetime(s.index)
    df = s.dropna().to_frame(name="value")
    df["year"] = df.index.year
    df["month"] = df.index.month
    df["day"] = df.index.day
    df = df[~((df["month"] == 2) & (df["day"] == 29))]
    pivot = df.pivot_table(index=["month", "day"], columns="year", values="value")

    if exclude_years:
        pivot = pivot.drop(columns=exclude_years, errors="ignore")

    if rebase:
        pivot = pivot.div(pivot.iloc[0]).sub(1)

    return pivot


def _calculate_statistics(pivot: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({"Average": pivot.mean(axis=1)})


def calendar_year_seasonality(series: pd.Series, exclude_years=None) -> pd.DataFrame:
    """Analyze seasonality of a daily time series by calendar day across years."""
    if not isinstance(series.index, pd.DatetimeIndex):
        raise ValueError("Input series must have a DateTimeIndex.")
    pivot = _prepare_pivot(series, exclude_years=exclude_years, rebase=False)
    latest_year = pivot.columns.max()
    current_year_series = pivot[latest_year].rename(str(latest_year))
    stats = _calculate_statistics(pivot)
    return pd.concat([stats, current_year_series], axis=1)


def calendar_year_seasonality_rebased(series: pd.Series, exclude_years=None) -> pd.DataFrame:
    """Rebased seasonality of a daily time series by calendar day across years."""
    if not isinstance(series.index, pd.DatetimeIndex):
        raise ValueError("Input series must have a DateTimeIndex.")
    pivot = _prepare_pivot(series, exclude_years=exclude_years, rebase=True)
    latest_year = pivot.columns.max()
    current_year_series = pivot[latest_year].rename(str(latest_year))
    stats = _calculate_statistics(pivot)
    return pd.concat([stats, current_year_series], axis=1)


# Backward-compatible wrapper
class CalendarYearSeasonality:
    def __init__(self, series: pd.Series):
        if not isinstance(series.index, pd.DatetimeIndex):
            raise ValueError("Input series must have a DateTimeIndex.")
        self._series = series

    def seasonality(self, exclude_years=None, include_stats=True) -> pd.DataFrame:
        return calendar_year_seasonality(self._series, exclude_years=exclude_years)

    def rebased(self, exclude_years=None) -> pd.DataFrame:
        return calendar_year_seasonality_rebased(self._series, exclude_years=exclude_years)
