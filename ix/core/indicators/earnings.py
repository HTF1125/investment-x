from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series, MultiSeries
from ix.common.data.transforms import StandardScalar


# Regional forward EPS codes (EPS_NTMA = next-twelve-months aggregate)
EPS_REGION_CODES = {
    "World": "FR0000R1:EPS_NTMA",
    "North America": "FR0000R4:EPS_NTMA",
    "Europe": "FR0000R3:EPS_NTMA",
    "Asia Pacific": "FR0000R2:EPS_NTMA",
    "Emerging": "FR0000R5:EPS_NTMA",
    "Developed": "FR0000R6:EPS_NTMA",
    "Developed x US": "FR0000R7:EPS_NTMA",
}

# SPX sector forward EPS codes
EPS_SECTOR_CODES = {
    "Cons Disc": "S5COND INDEX:EPS_NTMA",
    "Cons Staples": "S5CONS INDEX:EPS_NTMA",
    "Energy": "S5ENRS INDEX:EPS_NTMA",
    "Financials": "S5FINL INDEX:EPS_NTMA",
    "Health Care": "S5HLTH INDEX:EPS_NTMA",
    "Industrials": "S5INDU INDEX:EPS_NTMA",
    "Info Tech": "S5INFT INDEX:EPS_NTMA",
    "Materials": "S5MATR INDEX:EPS_NTMA",
    "Comm Svc": "S5TELS INDEX:EPS_NTMA",
    "Utilities": "S5UTIL INDEX:EPS_NTMA",
}


def regional_eps_momentum(periods: int = 1) -> pd.DataFrame:
    """MoM (or period-over-period) % change in forward EPS by region."""
    EPS_REGION_CODES = {
        "World": "FR0000R1:EPS_NTMA",
        "North America": "FR0000R4:EPS_NTMA",
        "Europe": "FR0000R3:EPS_NTMA",
        "Asia Pacific": "FR0000R2:EPS_NTMA",
        "Emerging": "FR0000R5:EPS_NTMA",
        "Developed": "FR0000R6:EPS_NTMA",
        "Developed x US": "FR0000R7:EPS_NTMA",
    }

    data = {name: Series(code) for name, code in EPS_REGION_CODES.items()}
    df = pd.DataFrame(data).dropna(how="all")
    if df.empty:
        return pd.DataFrame()
    return df.pct_change(periods=periods).dropna(how="all") * 100


def sector_eps_momentum(periods: int = 1) -> pd.DataFrame:
    """MoM % change in forward EPS by S&P 500 sector."""
    data = {name: Series(code) for name, code in EPS_SECTOR_CODES.items()}
    df = pd.DataFrame(data).dropna(how="all")
    if df.empty:
        return pd.DataFrame()
    return df.pct_change(periods=periods).dropna(how="all") * 100


def regional_eps_breadth(lookback: int = 4, smooth: int = 4) -> pd.Series:
    """% of regions with positive forward EPS momentum.

    Uses 4-week pct_change (not 1-day) to avoid noise from tiny daily
    estimate moves, then smooths with a 4-week moving average.
    """
    data = {name: Series(code) for name, code in EPS_REGION_CODES.items()}
    df = pd.DataFrame(data).dropna(how="all")
    if df.empty:
        return pd.Series(dtype=float, name="EPS Breadth (Regions)")
    changes = df.pct_change(lookback)
    positive = (changes > 0).sum(axis=1)
    valid = changes.notna().sum(axis=1)
    result = (positive / valid * 100).rolling(smooth, min_periods=1).mean().dropna()
    result.name = "EPS Breadth (Regions)"
    return result


def sector_eps_breadth(lookback: int = 4, smooth: int = 4) -> pd.Series:
    """% of S&P 500 sectors with positive forward EPS momentum.

    Uses 4-week pct_change and 4-week smoothing to reduce noise.
    """
    data = {name: Series(code) for name, code in EPS_SECTOR_CODES.items()}
    df = pd.DataFrame(data).dropna(how="all")
    if df.empty:
        return pd.Series(dtype=float, name="EPS Breadth (Sectors)")
    changes = df.pct_change(lookback)
    positive = (changes > 0).sum(axis=1)
    valid = changes.notna().sum(axis=1)
    result = (positive / valid * 100).rolling(smooth, min_periods=1).mean().dropna()
    result.name = "EPS Breadth (Sectors)"
    return result


def spx_revision_ratio() -> pd.Series:
    """S&P 500 earnings revision ratio: up / (up + down)."""
    up = Series("SPX INDEX:EARNINGS_REVISION_UP_1M")
    down = Series("SPX INDEX:EARNINGS_REVISION_DO_1M")
    if up.empty or down.empty:
        return pd.Series(dtype=float)
    total = up + down
    ratio = (up / total * 100).dropna()
    ratio.name = "SPX Revision Ratio"
    return ratio


def spx_revision_breadth() -> pd.Series:
    """S&P 500 net revision breadth: (up - down) / (up + down)."""
    up = Series("SPX INDEX:EARNINGS_REVISION_UP_1M")
    down = Series("SPX INDEX:EARNINGS_REVISION_DO_1M")
    if up.empty or down.empty:
        return pd.Series(dtype=float)
    total = up + down
    breadth = ((up - down) / total * 100).dropna()
    breadth.name = "SPX Net Revision Breadth"
    return breadth


def EarningsGrowth_NTMA() -> pd.DataFrame:
    """Earnings growth: (NTMA / LTMA - 1) * 100 for major indices."""
    spx_ntma = Series("SPX INDEX:EPS_NTMA", freq="W-Fri")
    spx_ltma = Series("SPX INDEX:EPS_LTMA", freq="W-Fri")
    ndx_ntma = Series("CCMP INDEX:EPS_NTMA", freq="W-Fri")
    ndx_ltma = Series("CCMP INDEX:EPS_LTMA", freq="W-Fri")
    eur_ntma = Series("SXXP INDEX:EPS_NTMA", freq="W-Fri")
    eur_ltma = Series("SXXP INDEX:EPS_LTMA", freq="W-Fri")
    components = {}
    if not spx_ntma.empty and not spx_ltma.empty:
        components["S&P 500"] = (spx_ntma / spx_ltma - 1) * 100
    if not ndx_ntma.empty and not ndx_ltma.empty:
        components["NASDAQ"] = (ndx_ntma.ffill() / ndx_ltma.ffill() - 1) * 100
    if not eur_ntma.empty and not eur_ltma.empty:
        components["EUROSTOXX 600"] = (eur_ntma / eur_ltma - 1) * 100
    if not components:
        return pd.DataFrame()
    return MultiSeries(**components).iloc[-52 * 10 :]


# ── Earnings Deep Analytics (merged from earnings_deep.py) ──────────────────

# Subset for deep analytics divergence (5 major regions)
_DEEP_EPS_REGION_CODES = {
    "World": "FR0000R1:EPS_NTMA",
    "North America": "FR0000R4:EPS_NTMA",
    "Europe": "FR0000R3:EPS_NTMA",
    "Asia Pacific": "FR0000R2:EPS_NTMA",
    "Emerging": "FR0000R5:EPS_NTMA",
}


def eps_estimate_dispersion(lookback: int = 4) -> pd.Series:
    """Cross-sector EPS estimate dispersion (std of sector momentum).

    High dispersion = high uncertainty about earnings direction.
    Rising dispersion = increasing disagreement (typically bearish).
    Falling dispersion = consensus forming (can be bullish or bearish).
    """
    data = {name: Series(code) for name, code in EPS_SECTOR_CODES.items()}
    df = pd.DataFrame(data).dropna(how="all")
    if df.empty:
        return pd.Series(dtype=float, name="EPS Estimate Dispersion")
    mom = df.pct_change(lookback) * 100
    s = mom.std(axis=1).dropna()
    s.name = "EPS Estimate Dispersion"
    return s


def eps_dispersion_zscore(lookback: int = 4, window: int = 52) -> pd.Series:
    """Z-score of EPS estimate dispersion.

    > 2 = extreme disagreement (high uncertainty).
    < -1 = unusually low disagreement (complacent consensus).
    """
    disp = eps_estimate_dispersion(lookback)
    return StandardScalar(disp, window)


def earnings_surprise_persistence(window: int = 8) -> pd.Series:
    """Earnings revision ratio autocorrelation — do beats cluster?

    High persistence = revision momentum continues (trends persist).
    Low/negative = mean-reversion (beats followed by misses).
    """
    up = Series("SPX INDEX:EARNINGS_REVISION_UP_1M")
    down = Series("SPX INDEX:EARNINGS_REVISION_DO_1M")
    total = up + down
    if total.empty:
        return pd.Series(dtype=float, name="Surprise Persistence")
    ratio = (up / total).dropna()
    # Autocorrelation of revision ratio
    s = ratio.rolling(window * 4).apply(
        lambda x: x.autocorr(lag=window) if len(x) > window else np.nan,
        raw=False,
    ).dropna()
    s.name = "Surprise Persistence"
    return s


def earnings_momentum_score(lookback: int = 4) -> pd.Series:
    """Earnings momentum score: breadth-weighted revision direction.

    Combines revision ratio (direction) with cross-sector breadth
    (how widespread the revision trend is).
    """
    up = Series("SPX INDEX:EARNINGS_REVISION_UP_1M")
    down = Series("SPX INDEX:EARNINGS_REVISION_DO_1M")
    total = up + down
    if total.empty:
        return pd.Series(dtype=float, name="Earnings Momentum Score")
    ratio = (up / total * 100).dropna()

    # Sector breadth
    df = pd.DataFrame(
        {name: Series(code) for name, code in EPS_SECTOR_CODES.items()}
    ).dropna(how="all")
    changes = df.pct_change(lookback)
    positive = (changes > 0).sum(axis=1)
    valid = changes.notna().sum(axis=1)
    breadth = (positive / valid * 100).dropna()

    # Combine revision ratio with breadth
    combined = pd.concat(
        {"ratio": StandardScalar(ratio, 52), "breadth": StandardScalar(breadth, 52)},
        axis=1,
    ).mean(axis=1).dropna()
    combined.name = "Earnings Momentum Score"
    return combined


def guidance_proxy() -> pd.Series:
    """Guidance direction proxy from NTMA vs LTMA EPS gap.

    When NTMA > LTMA, analysts expect earnings acceleration (positive guidance).
    When NTMA < LTMA, analysts expect deceleration (negative guidance).
    The gap magnitude indicates confidence in the direction.
    """
    ntma = Series("SPX INDEX:EPS_NTMA")
    ltma = Series("SPX INDEX:EPS_LTMA")
    if ntma.empty or ltma.empty:
        return pd.Series(dtype=float, name="Guidance Proxy")
    s = ((ntma / ltma - 1) * 100).dropna()
    s.name = "Guidance Proxy (%)"
    return s


def guidance_momentum(window: int = 4) -> pd.Series:
    """Change in guidance proxy over window weeks.

    Rising = management outlook improving. Falling = deteriorating.
    """
    gp = guidance_proxy()
    s = gp.diff(window).dropna()
    s.name = "Guidance Momentum"
    return s


def earnings_yield_gap() -> pd.Series:
    """SPX earnings yield minus BBB bond yield (adjusted ERP).

    Uses BBB yield instead of risk-free rate for a more relevant comparison.
    Positive = stocks cheap vs investment-grade bonds.
    Negative = bonds more attractive than stocks.
    """
    eps = Series("SPX INDEX:EPS_NTMA")
    px = Series("SPX INDEX:PX_LAST")
    bbb = Series("BAMLC0A4CBBB")
    if eps.empty or px.empty:
        return pd.Series(dtype=float, name="Earnings Yield Gap")
    ey = (eps / px * 100).dropna()
    # Add risk-free rate to BBB OAS to get total yield
    y10 = Series("TRYUS10Y:PX_YTM")
    if bbb.empty or y10.empty:
        s = ey  # Just return earnings yield
    else:
        bbb_total = (bbb / 100 + y10).dropna()  # OAS is in %, convert
        s = (ey - bbb_total).dropna()
    s.name = "Earnings Yield Gap"
    return s


def regional_earnings_divergence(lookback: int = 4) -> pd.Series:
    """Divergence in regional EPS revisions (std dev of regional momentum).

    High divergence = regional decoupling (idiosyncratic opportunities).
    Low divergence = global synchronization.
    """
    data = {name: Series(code) for name, code in _DEEP_EPS_REGION_CODES.items()}
    df = pd.DataFrame(data).dropna(how="all")
    if df.empty:
        return pd.Series(dtype=float, name="Regional EPS Divergence")
    mom = df.pct_change(lookback) * 100
    s = mom.std(axis=1).dropna()
    s.name = "Regional EPS Divergence"
    return s


def us_vs_world_earnings(lookback: int = 4) -> pd.Series:
    """US vs World EPS momentum differential.

    Positive = US earnings outperforming (US exceptionalism).
    Negative = RoW catching up (broadening global recovery).
    """
    us = Series("FR0000R4:EPS_NTMA")
    world = Series("FR0000R1:EPS_NTMA")
    if us.empty or world.empty:
        return pd.Series(dtype=float, name="US vs World EPS")
    us_mom = us.pct_change(lookback) * 100
    world_mom = world.pct_change(lookback) * 100
    s = (us_mom - world_mom).dropna()
    s.name = "US vs World EPS Momentum"
    return s


def earnings_composite(window: int = 52) -> pd.Series:
    """Composite earnings health indicator.

    Combines: revision ratio, sector breadth, estimate dispersion (inverted),
    guidance proxy, and earnings momentum. Z-scored and averaged.
    Positive = earnings environment healthy. Negative = deteriorating.
    """
    components = {}

    # Revision ratio
    up = Series("SPX INDEX:EARNINGS_REVISION_UP_1M")
    down = Series("SPX INDEX:EARNINGS_REVISION_DO_1M")
    total = up + down
    if not total.empty:
        ratio = (up / total * 100).dropna()
        components["Revisions"] = StandardScalar(ratio, window)

    # Sector breadth
    df = pd.DataFrame(
        {name: Series(code) for name, code in EPS_SECTOR_CODES.items()}
    ).dropna(how="all")
    if not df.empty:
        changes = df.pct_change(4)
        positive = (changes > 0).sum(axis=1)
        valid = changes.notna().sum(axis=1)
        breadth = (positive / valid * 100).dropna()
        components["Breadth"] = StandardScalar(breadth, window)

    # Dispersion (inverted — low dispersion = healthy)
    disp = eps_estimate_dispersion()
    if not disp.empty:
        components["Dispersion"] = -StandardScalar(disp, window)

    # Guidance
    gp = guidance_proxy()
    if not gp.empty:
        components["Guidance"] = StandardScalar(gp, window)

    if not components:
        return pd.Series(dtype=float, name="Earnings Composite")

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Earnings Composite"
    return s
