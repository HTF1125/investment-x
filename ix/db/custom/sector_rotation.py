from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series
from ix.core.transforms import StandardScalar


# ── US GICS Sector ETFs ─────────────────────────────────────────────────────

US_SECTORS = {
    "Tech": "XLK US EQUITY:PX_LAST",
    "Financials": "XLF US EQUITY:PX_LAST",
    "Energy": "XLE US EQUITY:PX_LAST",
    "Discretionary": "XLY US EQUITY:PX_LAST",
    "Healthcare": "XLV US EQUITY:PX_LAST",
    "Industrials": "XLI US EQUITY:PX_LAST",
    "Materials": "XLB US EQUITY:PX_LAST",
    "Comm Services": "XLC US EQUITY:PX_LAST",
    "Staples": "XLP US EQUITY:PX_LAST",
    "Real Estate": "XLRE US EQUITY:PX_LAST",
}

US_CYCLICAL = ["Tech", "Financials", "Discretionary", "Industrials", "Materials", "Energy"]
US_DEFENSIVE = ["Healthcare", "Staples", "Comm Services", "Real Estate"]

# ── KOSPI Sector Indices ─────────────────────────────────────────────────────

KR_SECTORS = {
    "전기/전자": "A013:PX_LAST",
    "화학": "A008:PX_LAST",
    "금융": "A021:PX_LAST",
    "기계/장비": "A012:PX_LAST",
    "제조": "A027:PX_LAST",
    "금속": "A011:PX_LAST",
    "건설": "A018:PX_LAST",
    "운송장비/부품": "A015:PX_LAST",
    "섬유/의류": "A006:PX_LAST",
    "IT서비스": "A046:PX_LAST",
    "비금속": "A010:PX_LAST",
    "음식료/담배": "A005:PX_LAST",
    "제약": "A009:PX_LAST",
    "전기/가스": "A017:PX_LAST",
    "통신": "A020:PX_LAST",
    "보험": "A025:PX_LAST",
    "의료/정밀기기": "A014:PX_LAST",
    "종이/목재": "A007:PX_LAST",
    "증권": "A024:PX_LAST",
    "유통": "A016:PX_LAST",
    "운송/창고": "A019:PX_LAST",
    "일반서비스": "A026:PX_LAST",
    "부동산": "A045:PX_LAST",
    "오락/문화": "A047:PX_LAST",
}

KR_CYCLICAL = ["전기/전자", "화학", "금융", "기계/장비", "제조", "금속", "건설", "운송장비/부품", "섬유/의류", "IT서비스", "비금속"]
KR_DEFENSIVE = ["음식료/담배", "제약", "전기/가스", "통신", "보험", "의료/정밀기기", "종이/목재"]


# ── Helper ───────────────────────────────────────────────────────────────────

def _load_sectors(sector_map: dict[str, str], freq: str = "W") -> pd.DataFrame:
    """Load sector price data into a DataFrame."""
    data = {}
    for name, code in sector_map.items():
        try:
            s = Series(code, freq=freq)
            if len(s.dropna()) > 100:
                data[name] = s
        except Exception:
            pass
    return pd.DataFrame(data).dropna(how="all")


def _relative_strength(sector_df: pd.DataFrame, benchmark: pd.Series, window: int = 52) -> pd.DataFrame:
    """Relative strength: sector / benchmark, normalized as z-score of log ratio momentum."""
    ratios = sector_df.div(benchmark, axis=0)
    log_mom = np.log(ratios).diff(window)
    return log_mom.dropna(how="all")


def _cyclical_defensive_basket(
    sector_df: pd.DataFrame,
    cyclical_names: list[str],
    defensive_names: list[str],
) -> pd.Series:
    """Equal-weighted cyclical basket / defensive basket ratio."""
    cyc_cols = [c for c in cyclical_names if c in sector_df.columns]
    def_cols = [c for c in defensive_names if c in sector_df.columns]
    if not cyc_cols or not def_cols:
        return pd.Series(dtype=float)

    # Rebase each to 1.0 at first valid date for equal weighting
    rebased = sector_df.div(sector_df.bfill().iloc[0])
    cyc = rebased[cyc_cols].mean(axis=1)
    dfc = rebased[def_cols].mean(axis=1)
    return (cyc / dfc).dropna()


# ── US Sector Indicators ────────────────────────────────────────────────────

def us_sector_relative_strength(window: int = 52, freq: str = "W") -> pd.DataFrame:
    """US GICS sector relative strength vs SPX (52-week log return of ratio).

    Each column is a sector's momentum relative to S&P 500.
    Positive = outperforming, Negative = underperforming.
    """
    sectors = _load_sectors(US_SECTORS, freq=freq)
    spx = Series("SPX INDEX:PX_LAST", freq=freq)
    return _relative_strength(sectors, spx, window)


def us_cyclical_defensive_ratio(freq: str = "W") -> pd.Series:
    """US cyclical vs defensive sector basket ratio.

    Rising = growth/risk-on rotation. Falling = defensive rotation.
    Equal-weighted baskets: Cyclical (Tech, Fins, Disc, Industrials, Materials, Energy)
    vs Defensive (Healthcare, Staples, Comm Svc, Real Estate).
    """
    sectors = _load_sectors(US_SECTORS, freq=freq)
    s = _cyclical_defensive_basket(sectors, US_CYCLICAL, US_DEFENSIVE)
    s.name = "US Cyclical/Defensive Ratio"
    return s


def us_sector_breadth(window: int = 52, freq: str = "W") -> pd.Series:
    """% of US GICS sectors outperforming SPX over trailing window.

    High breadth = healthy broad-based rally.
    Low breadth = narrow leadership (fragile).
    """
    rs = us_sector_relative_strength(window, freq)
    positive = (rs > 0).sum(axis=1)
    valid = rs.notna().sum(axis=1)
    s = (positive / valid * 100).dropna()
    s.name = "US Sector Breadth"
    return s


def us_sector_dispersion(window: int = 52, freq: str = "W") -> pd.Series:
    """Cross-sectional dispersion of US sector relative strength.

    High dispersion = strong sector rotation opportunities.
    Low dispersion = correlated market (macro-driven, hard to add alpha).
    """
    rs = us_sector_relative_strength(window, freq)
    s = rs.std(axis=1).dropna()
    s.name = "US Sector Dispersion"
    return s


# ── Korea Sector Indicators ─────────────────────────────────────────────────

def kr_sector_relative_strength(window: int = 52, freq: str = "W") -> pd.DataFrame:
    """KOSPI sector relative strength vs KOSPI (52-week log return of ratio).

    Each column is a Korean sector's momentum relative to KOSPI index.
    """
    sectors = _load_sectors(KR_SECTORS, freq=freq)
    kospi = Series("KOSPI INDEX:PX_LAST", freq=freq)
    return _relative_strength(sectors, kospi, window)


def kr_cyclical_defensive_ratio(freq: str = "W") -> pd.Series:
    """KOSPI cyclical vs defensive sector basket ratio.

    Rising = growth/export-led rotation. Falling = defensive rotation.
    Cyclical: 전기/전자, 화학, 금융, 기계, 제조, 금속, 건설, 운송장비, 섬유, IT서비스, 비금속.
    Defensive: 음식료, 제약, 전기/가스, 통신, 보험, 의료, 종이/목재.
    """
    sectors = _load_sectors(KR_SECTORS, freq=freq)
    s = _cyclical_defensive_basket(sectors, KR_CYCLICAL, KR_DEFENSIVE)
    s.name = "KR Cyclical/Defensive Ratio"
    return s


def kr_sector_breadth(window: int = 52, freq: str = "W") -> pd.Series:
    """% of KOSPI sectors outperforming KOSPI over trailing window.

    High breadth = broad rally participation.
    Low breadth = narrow leadership (top-heavy market).
    """
    rs = kr_sector_relative_strength(window, freq)
    positive = (rs > 0).sum(axis=1)
    valid = rs.notna().sum(axis=1)
    s = (positive / valid * 100).dropna()
    s.name = "KR Sector Breadth"
    return s


def kr_sector_dispersion(window: int = 52, freq: str = "W") -> pd.Series:
    """Cross-sectional dispersion of KOSPI sector relative strength.

    High = strong rotation / stock-picking environment.
    Low = correlated macro-driven market.
    """
    rs = kr_sector_relative_strength(window, freq)
    s = rs.std(axis=1).dropna()
    s.name = "KR Sector Dispersion"
    return s


# ── Cross-market sector ratios ──────────────────────────────────────────────

def kr_tech_vs_us_tech(freq: str = "W") -> pd.Series:
    """KOSPI 전기/전자 vs US XLK relative ratio.

    Rising = Korean tech outperforming US tech (EM tech rotation).
    Falling = US tech leadership.
    """
    kr = Series("A013:PX_LAST", freq=freq)
    us = Series("XLK US EQUITY:PX_LAST", freq=freq)
    s = (kr / us).dropna()
    s.name = "KR Tech / US Tech"
    return s


def kr_financials_vs_us_financials(freq: str = "W") -> pd.Series:
    """KOSPI 금융 vs US XLF relative ratio.

    Rising = Korean financials outperforming (KR rate/growth cycle favorable).
    """
    kr = Series("A021:PX_LAST", freq=freq)
    us = Series("XLF US EQUITY:PX_LAST", freq=freq)
    s = (kr / us).dropna()
    s.name = "KR Financials / US Financials"
    return s


def kr_export_vs_domestic(freq: str = "W") -> pd.Series:
    """KOSPI export-oriented vs domestic-oriented sector ratio.

    Export: 전기/전자, 화학, 기계/장비, 운송장비/부품, 금속.
    Domestic: 금융, 건설, 유통, 통신, 음식료/담배.
    Rising = global trade cycle favoring Korea exporters.
    """
    sectors = _load_sectors(KR_SECTORS, freq=freq)
    export_names = ["전기/전자", "화학", "기계/장비", "운송장비/부품", "금속"]
    domestic_names = ["금융", "건설", "유통", "통신", "음식료/담배"]

    export_cols = [c for c in export_names if c in sectors.columns]
    domestic_cols = [c for c in domestic_names if c in sectors.columns]
    if not export_cols or not domestic_cols:
        return pd.Series(dtype=float)

    rebased = sectors.div(sectors.bfill().iloc[0])
    exp = rebased[export_cols].mean(axis=1)
    dom = rebased[domestic_cols].mean(axis=1)
    s = (exp / dom).dropna()
    s.name = "KR Export/Domestic Ratio"
    return s
