from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from ix.common.data.transforms import StandardScalar, daily_ffill
from ix.db.query import Series

logger = logging.getLogger(__name__)


# ── Cross-Asset ─────────────────────────────────────────────────────────────


def dollar_index(freq: str = "W") -> pd.Series:
    """DXY Dollar Index."""
    s = Series("DXY INDEX:PX_LAST", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "Dollar Index"
    return s.dropna()


def copper_gold_ratio(freq: str = "W") -> pd.Series:
    """Copper / Gold price ratio. Rising = growth optimism."""
    copper = Series("COPPER CURNCY:PX_LAST", freq=freq)
    gold = Series("GOLDCOMP:PX_LAST", freq=freq)
    if copper.empty or gold.empty:
        return pd.Series(dtype=float)
    s = (copper / gold).dropna()
    s.name = "Copper/Gold Ratio"
    return s


def em_vs_dm(freq: str = "W") -> pd.Series:
    """MSCI EM vs MSCI World total return ratio."""
    em = Series("891800:FG_TOTAL_RET_IDX", freq=freq)
    dm = Series("990100:FG_TOTAL_RET_IDX", freq=freq)
    if em.empty or dm.empty:
        return pd.Series(dtype=float)
    s = (em / dm).dropna()
    s.name = "EM vs DM Relative"
    return s


def china_sse(freq: str = "W") -> pd.Series:
    """Shanghai Composite Index."""
    s = Series("SHCOMP INDEX:PX_LAST", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "China SSE"
    return s.dropna()


def nikkei(freq: str = "W") -> pd.Series:
    """Nikkei 225 Index."""
    s = Series("NKY INDEX:PX_LAST", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "Nikkei 225"
    return s.dropna()


def vix(freq: str = "W") -> pd.Series:
    """CBOE VIX Index."""
    s = Series("VIX INDEX:PX_LAST", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "VIX"
    return s.dropna()


def commodities_crb(freq: str = "W") -> pd.Series:
    """Bloomberg Commodity Index."""
    s = Series("BCOM-CME:PX_LAST", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "Commodities CRB"
    return s.dropna()


def baltic_dry_index(freq: str = "W") -> pd.Series:
    """Baltic Dry Index — leads global trade by 2-3 months."""
    s = Series("BDI-BAX:PX_LAST", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "Baltic Dry Index"
    return s.dropna()


def baltic_capesize_index(freq: str = "W") -> pd.Series:
    """Baltic Capesize Index — iron ore / coal bulk shipping rates.

    More volatile than BDI and more sensitive to China demand impulses.
    Capesize vessels (>100k DWT) carry iron ore and coal exclusively,
    making this a purer signal of heavy industry / infrastructure demand.

    Extreme moves (>200% YoY) often precede commodity and EM equity rallies.
    Near-zero readings signal global industrial recession.

    Source: Baltic Exchange (BCI-BAX).
    """
    s = Series("BCI-BAX:PX_LAST", freq=freq)
    if s.empty:
        return pd.Series(dtype=float, name="Baltic Capesize Index")
    s.name = "Baltic Capesize Index"
    return s.dropna()


def baltic_capesize_yoy() -> pd.Series:
    """Baltic Capesize Index year-over-year change (%).

    More actionable than level — captures the acceleration of
    demand for heavy bulk shipping. Positive = industrial expansion.
    """
    bci = Series("BCI-BAX:PX_LAST", freq="W")
    if bci.empty:
        return pd.Series(dtype=float, name="Baltic Capesize YoY %")
    s = bci.pct_change(52) * 100
    s.name = "Baltic Capesize YoY %"
    return s.dropna()


def real_rate_differential(target_bond: str, freq: str = "W") -> pd.Series:
    """Real rate differential: US real yield minus target region real yield.

    Positive = capital flows toward US = headwind for target.
    Uses nominal yields as proxy (breakevens not available for all regions).
    """
    us_10y = Series("TRYUS10Y:PX_YTM", freq=freq)
    target_10y = Series(target_bond, freq=freq)
    if us_10y.empty or target_10y.empty:
        return pd.Series(dtype=float)
    diff = (us_10y - target_10y).dropna()
    diff.name = "Real Rate Differential"
    return diff


# ── Local Indices (merged from indices.py) ──────────────────────────────────

LOCAL_INDICES_CODES = {
    "SP500": "SPX Index:PX_LAST",
    "DJIA30": "INDU Index:PX_LAST",
    "NASDAQ": "CCMP Index:PX_LAST",
    "Russell2": "RTY Index:PX_LAST",
    "Stoxx50": "SX5E Index:PX_LAST",
    "FTSE100": "UKX Index:PX_LAST",
    "DAX": "DAX Index:PX_LAST",
    "CAC": "CAC Index:PX_LAST",
    "Nikkei225": "NKY Index:PX_LAST",
    "TOPIX": "TPX Index:PX_LAST",
    "KOSPI": "KOSPI Index:PX_LAST",
    "NIFTY": "NIFTY Index:PX_LAST",
    "HangSeng": "HSI Index:PX_LAST",
    "SSE": "SHCOMP Index:PX_LAST",
}


def local_indices_performance() -> pd.DataFrame:
    """Level, 1D, 1W, 1M, 3M, 1Y, YTD performance table."""
    from ix.db import get_timeseries

    series_list = []
    for name, ticker in LOCAL_INDICES_CODES.items():
        ts = get_timeseries(ticker).data
        ts.name = name
        series_list.append(ts)

    datas = pd.concat(series_list, axis=1)
    datas = daily_ffill(datas)

    today = datas.index[-1]
    start_year = pd.Timestamp(year=today.year, month=1, day=1)
    one_month = today - pd.DateOffset(months=1)
    three_mo = today - pd.DateOffset(months=3)
    one_year = today - pd.DateOffset(years=1)

    def pct_from(base_date):
        base = datas.asof(base_date)
        return (datas.iloc[-1] / base - 1).round(4) * 100

    output = [
        datas.iloc[-1].round(2).rename("Level"),
        pct_from(today - pd.DateOffset(days=1)).rename("1D"),
        pct_from(today - pd.DateOffset(days=7)).rename("1W"),
        pct_from(one_month).rename("1M"),
        pct_from(three_mo).rename("3M"),
        pct_from(one_year).rename("1Y"),
        pct_from(start_year).rename("YTD"),
    ]
    return pd.concat(output, axis=1).dropna()


# Backward-compatible aliases
def LocalIndices() -> pd.DataFrame:
    return local_indices_performance()


# ── Intermarket Signals ─────────────────────────────────────────────────────


def equity_bond_correlation(window: int = 60) -> pd.Series:
    """Rolling correlation between SPX daily returns and 10Y yield changes.

    Positive = "good news is good news" (growth-driven market).
    Negative = "bad news is good news" (inflation/flight-to-safety regime).
    Regime shifts in this correlation are among the most important
    signals for portfolio construction and hedging.
    """
    spx = Series("SPX INDEX:PX_LAST").pct_change()
    y10 = Series("TRYUS10Y:PX_YTM").diff()
    if spx.empty or y10.empty:
        return pd.Series(dtype=float)
    s = spx.rolling(window).corr(y10).dropna()
    s.name = "Equity-Bond Correlation"
    return s


def risk_on_off_breadth(window: int = 160) -> pd.Series:
    """Breadth of risk-on vs risk-off signals across asset classes (%).

    Checks z-scored direction of 6 cross-asset signals:
    SPX (up=risk-on), VIX (down=risk-on), HY spread (down=risk-on),
    copper/gold (up=risk-on), DXY (down=risk-on), 2s10s (up=risk-on).

    100% = all risk-on. 0% = all risk-off.
    Consensus extremes (>80% or <20%) mark fragile positioning.
    """
    from ix.core.indicators.rates import us_2s10s

    raw = {
        "SPX": Series("SPX INDEX:PX_LAST"),
        "VIX": Series("VIX INDEX:PX_LAST"),
        "HY": Series("BAMLH0A0HYM2"),
        "Cu": Series("COPPER CURNCY:PX_LAST"),
        "Au": Series("GOLDCOMP:PX_LAST"),
        "DXY": Series("DXY INDEX:PX_LAST"),
    }
    if all(s.empty for s in raw.values()):
        return pd.Series(dtype=float, name="Risk-On Breadth")
    signals = {}
    if not raw["SPX"].empty:
        signals["SPX"] = StandardScalar(raw["SPX"], window)
    if not raw["VIX"].empty:
        signals["VIX"] = -StandardScalar(raw["VIX"], window)
    if not raw["HY"].empty:
        signals["HY"] = -StandardScalar(raw["HY"], window)
    if not raw["Cu"].empty and not raw["Au"].empty:
        signals["Cu/Au"] = StandardScalar(
            (raw["Cu"] / raw["Au"]).dropna(), window,
        )
    if not raw["DXY"].empty:
        signals["DXY"] = -StandardScalar(raw["DXY"], window)
    curve = us_2s10s()
    if not curve.empty:
        signals["Curve"] = StandardScalar(curve, window)
    if not signals:
        return pd.Series(dtype=float, name="Risk-On Breadth")
    df = pd.DataFrame(signals).dropna(how="all")
    risk_on = (df > 0).sum(axis=1)
    valid = df.notna().sum(axis=1)
    s = (risk_on / valid * 100).dropna()
    s.name = "Risk-On Breadth"
    return s


def small_large_cap_ratio(freq: str = "W") -> pd.Series:
    """Russell 2000 / S&P 500 relative performance ratio.

    Rising = broadening rally, improving growth outlook.
    Falling = narrowing leadership, late-cycle or risk-off.
    """
    rty = Series("RTY INDEX:PX_LAST", freq=freq)
    spx = Series("SPX INDEX:PX_LAST", freq=freq)
    if rty.empty or spx.empty:
        return pd.Series(dtype=float)
    s = (rty / spx).dropna()
    s.name = "Small/Large Cap Ratio"
    return s


def cyclical_defensive_ratio(freq: str = "W") -> pd.Series:
    """SPY / XLP relative performance (cyclical vs defensive).

    Rising = cyclical outperformance = growth confidence.
    Falling = defensive rotation = late-cycle caution.
    """
    spy = Series("SPY US EQUITY:PX_LAST", freq=freq)
    xlp = Series("XLP US EQUITY:PX_LAST", freq=freq)
    if spy.empty or xlp.empty:
        return pd.Series(dtype=float)
    s = (spy / xlp).dropna()
    s.name = "Cyclical/Defensive Ratio"
    return s



def credit_equity_divergence(window: int = 60) -> pd.Series:
    """Divergence between equity momentum and credit spread momentum.

    When SPX rises but HY spreads also widen, credit is not confirming
    the equity rally — bearish divergence.
    Computed as: z(SPX momentum) + z(inverted HY spread momentum).
    Large negative values = dangerous divergence.
    """
    spx_mom = Series("SPX INDEX:PX_LAST").pct_change(window).mul(100)
    hy_mom = Series("BAMLH0A0HYM2").diff(window)
    if spx_mom.empty or hy_mom.empty:
        return pd.Series(dtype=float)

    z_spx = StandardScalar(spx_mom.dropna(), window * 4)
    z_hy = -StandardScalar(hy_mom.dropna(), window * 4)

    s = pd.concat([z_spx, z_hy], axis=1).mean(axis=1).dropna()
    s.name = "Credit-Equity Divergence"
    return s


def vix_realized_vol_spread(window: int = 20) -> pd.Series:
    """VIX minus SPX realized volatility (annualized, %).

    Positive = VIX elevated vs realized = fear premium (contrarian bullish).
    Negative = VIX depressed vs realized = complacency (contrarian bearish).
    """
    vix = Series("VIX INDEX:PX_LAST")
    spx = Series("SPX INDEX:PX_LAST")
    if vix.empty or spx.empty:
        return pd.Series(dtype=float)
    realized = spx.pct_change().rolling(window).std() * np.sqrt(252) * 100
    s = (vix - realized).dropna()
    s.name = "VIX-Realized Vol Spread"
    return s


def market_fear_composite(z_window: int = 78, halflife: int = 4) -> pd.Series:
    """Market fear/stress composite — contrarian predictor of forward equity returns.

    Equal-weight z-score average of three contrarian signals:
      - VIX (high fear = higher forward returns)
      - HY OAS (wide spreads = higher forward returns)
      - -ISM PMI (weak economy = higher forward returns)

    When this composite is high, the market is fearful/stressed and
    forward 12M returns tend to be above average. When low, the market
    is complacent and forward returns tend to be below average.

    Empirical Spearman r vs S&P 500 forward returns:
      3M: +0.09, 6M: +0.13, 12M: +0.23

    This is a contrarian regime indicator — DO NOT invert it.
    High = fear regime. Low = complacency regime.

    NOT a leading indicator. The correlation increasing with horizon
    (0.06 at 1M → 0.23 at 12M) does not mean it "leads by 12 months."
    It means the current fear/complacency state is coincident with the
    return regime you're already in. Low readings (complacency) coincide
    with periods where cumulative forward returns tend to be poor — the
    damage is happening now, not being predicted.

    Best used as: a regime overlay. When fear composite is elevated,
    the risk/reward for adding equity exposure is favorable. When
    depressed, the market is priced for perfection.

    Limitations:
      - Coincident regime classifier, not a timing signal
      - r=0.23 at 12M is modest — explains ~5% of forward return variance
      - Performs best at extremes (2008, 2020 spikes) but noisy in the middle
      - Individual components: VIX r=+0.17, HY r=+0.15, -ISM r=-0.24.
        Composite (r=+0.23) beats any single component at 12M

    Source: Composite of CBOE VIX, ICE BofA HY OAS, ISM Manufacturing PMI.
    """
    vix = Series("VIX INDEX:PX_LAST", freq="W")
    hy = Series("BAMLH0A0HYM2", freq="W")
    ism = Series("ISMPMI@M:PX_LAST", freq="W")

    components = {}
    if not vix.empty:
        components["VIX"] = StandardScalar(vix, z_window)
    if not hy.empty:
        components["HY"] = StandardScalar(hy, z_window)
    if not ism.empty:
        components["-ISM"] = -StandardScalar(ism, z_window)

    if not components:
        return pd.Series(dtype=float, name="Market Fear Composite")

    result = pd.DataFrame(components).mean(axis=1).ewm(halflife=halflife).mean()
    result.name = "Market Fear Composite"
    return result.dropna()


def move_vix_ratio() -> pd.Series:
    """MOVE/VIX ratio — relative bond vs equity volatility.

    When MOVE/VIX is elevated, bond market stress is disproportionate
    to equity market stress.  Historically this divergence resolves
    with equities catching down to bonds (risk-off) or bonds calming
    (rates find a level).

    Interpretation:
    - Rising ratio → rate vol leading; equity complacency may be misplaced
    - Falling ratio → equity vol catching up or rate vol normalizing
    - Extreme highs (>4) preceded equity selloffs in 2022-2023

    The ratio is most useful as a regime divergence detector, not a
    standalone timing signal.  Best combined with risk_appetite() or
    fci_stress() for confirmation.

    Source: ICE BofA MOVE Index / CBOE VIX Index.
    """
    move = Series("MOVE INDEX:PX_LAST")
    vix = Series("VIX INDEX:PX_LAST")
    if move.empty or vix.empty:
        return pd.Series(dtype=float, name="MOVE/VIX Ratio")
    s = (move / vix).dropna()
    s.name = "MOVE/VIX Ratio"
    return s


def move_vix_ratio_zscore(window: int = 252) -> pd.Series:
    """Z-score of MOVE/VIX ratio vs trailing distribution.

    Extreme positive z = bond vol disproportionately high vs equity vol.
    Extreme negative z = equity vol disproportionately high vs bond vol.

    Source: ICE BofA MOVE Index / CBOE VIX Index.
    """
    return StandardScalar(move_vix_ratio(), window)


# ── Correlation Regime (merged from correlation_regime.py) ──────────────────


def equity_bond_corr_regime(window: int = 60, threshold: float = 0.0) -> pd.Series:
    """Equity-bond correlation regime classification.

    Positive correlation = 'stagflationary' regime (stocks and bonds fall together).
    Negative correlation = 'normal' regime (bonds hedge equities).
    Returns: 1 = positive corr (dangerous), -1 = negative corr (normal), 0 = neutral.
    """
    spx = Series("SPX INDEX:PX_LAST").pct_change()
    y10 = Series("TRYUS10Y:PX_YTM").diff()
    corr = spx.rolling(window).corr(y10).dropna()
    regime = pd.Series(0, index=corr.index, dtype=float)
    if spx.empty or y10.empty or regime.empty:
        return pd.Series(dtype=float)
    regime[corr > threshold] = 1
    regime[corr < -threshold] = -1
    regime.name = "Eq-Bond Corr Regime"
    return regime


def equity_bond_corr_zscore(window: int = 60) -> pd.Series:
    """Z-score of rolling equity-bond correlation.

    Extreme positive z-scores = correlation regime shift (rare, important).
    """
    spx = Series("SPX INDEX:PX_LAST").pct_change()
    y10 = Series("TRYUS10Y:PX_YTM").diff()
    if spx.empty or y10.empty:
        return pd.Series(dtype=float)
    corr = spx.rolling(window).corr(y10).dropna()
    s = StandardScalar(corr, 252)
    s.name = "Eq-Bond Corr Z-Score"
    return s.dropna()


def cross_asset_correlation(window: int = 60) -> pd.Series:
    """Average pairwise correlation across major asset classes.

    High correlation = "correlation crisis" (diversification fails).
    Low correlation = normal diversification benefits.
    Spikes to >0.5 historically mark systemic stress events.
    """
    assets = {
        "SPX": Series("SPX INDEX:PX_LAST"),
        "Bonds": Series("TLT US EQUITY:PX_LAST"),
        "Gold": Series("GOLDCOMP:PX_LAST"),
        "DXY": Series("DXY INDEX:PX_LAST"),
        "Commodities": Series("BCOM-CME:PX_LAST"),
        "VIX": Series("VIX INDEX:PX_LAST"),
    }
    # Filter out empty series
    rets = {}
    for name, s in assets.items():
        if not s.empty:
            rets[name] = s.pct_change().dropna()

    if len(rets) < 3:
        return pd.Series(dtype=float, name="Cross-Asset Correlation")

    df = pd.DataFrame(rets).dropna()

    # Rolling average pairwise correlation
    n = len(rets)
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    cols = list(rets.keys())

    avg_corr = pd.Series(dtype=float)
    for idx in range(window, len(df)):
        sub = df.iloc[idx - window:idx]
        corr_matrix = sub.corr().values
        pair_corrs = [abs(corr_matrix[i][j]) for i, j in pairs]
        avg_corr.loc[df.index[idx]] = np.mean(pair_corrs)

    avg_corr.name = "Cross-Asset Avg Correlation"
    return avg_corr.dropna()


def cross_asset_correlation_fast(window: int = 60) -> pd.Series:
    """Fast version: average absolute correlation using expanding pairs.

    Uses SPX-TLT, SPX-Gold, SPX-DXY as key pairs.
    More efficient than full pairwise computation.
    """
    spx = Series("SPX INDEX:PX_LAST").pct_change()
    tlt = Series("TLT US EQUITY:PX_LAST").pct_change()
    gold = Series("GOLDCOMP:PX_LAST").pct_change()
    dxy = Series("DXY INDEX:PX_LAST").pct_change()

    pairs = []
    if not spx.empty and not tlt.empty:
        pairs.append(spx.rolling(window).corr(tlt).abs())
    if not spx.empty and not gold.empty:
        pairs.append(spx.rolling(window).corr(gold).abs())
    if not spx.empty and not dxy.empty:
        pairs.append(spx.rolling(window).corr(dxy).abs())
    if not tlt.empty and not gold.empty:
        pairs.append(tlt.rolling(window).corr(gold).abs())

    if not pairs:
        return pd.Series(dtype=float, name="Avg Abs Correlation")

    s = pd.concat(pairs, axis=1).mean(axis=1).dropna()
    s.name = "Avg Abs Correlation"
    return s


def diversification_index(window: int = 60) -> pd.Series:
    """Diversification benefit index (inverse of avg abs correlation).

    High = good diversification (correlations low).
    Low = poor diversification (everything moving together).
    100 = perfect diversification. 0 = perfect correlation.
    """
    corr = cross_asset_correlation_fast(window)
    s = ((1 - corr) * 100).dropna()
    s.name = "Diversification Index"
    return s


def correlation_surprise(window_short: int = 20, window_long: int = 252) -> pd.Series:
    """Correlation surprise: short-term vs long-term avg correlation.

    Positive = correlations spiking above normal (stress).
    Negative = correlations below normal (calm, good diversification).
    Large positive values mark systemic risk events.
    """
    short = cross_asset_correlation_fast(window_short)
    long_ = cross_asset_correlation_fast(window_long)
    s = (short - long_).dropna()
    s.name = "Correlation Surprise"
    return s


def safe_haven_demand(window: int = 20) -> pd.Series:
    """Safe haven demand index: gold + treasuries + yen vs equities + credit.

    Positive = safe haven assets outperforming (risk aversion).
    Negative = risk assets outperforming (risk appetite).
    """
    # Safe havens (rising = demand)
    gold = Series("GOLDCOMP:PX_LAST")
    tlt = Series("TLT US EQUITY:PX_LAST")

    # Risk assets (rising = risk-on)
    spx = Series("SPX INDEX:PX_LAST")

    haven_components = []
    if not gold.empty:
        haven_components.append(StandardScalar(gold.pct_change(window).dropna(), 252))
    if not tlt.empty:
        haven_components.append(StandardScalar(tlt.pct_change(window).dropna(), 252))

    risk_components = []
    if not spx.empty:
        risk_components.append(StandardScalar(spx.pct_change(window).dropna(), 252))

    if not haven_components or not risk_components:
        return pd.Series(dtype=float, name="Safe Haven Demand")

    haven = pd.concat(haven_components, axis=1).mean(axis=1)
    risk = pd.concat(risk_components, axis=1).mean(axis=1)
    s = (haven - risk).dropna()
    s.name = "Safe Haven Demand"
    return s


def tail_risk_index(window: int = 20) -> pd.Series:
    """Composite tail risk indicator.

    Combines: VIX term structure (backwardation), SKEW index,
    equity-bond correlation shift, and credit stress.
    Higher = more tail risk priced. Useful for hedging timing.
    """
    components = {}

    # VIX backwardation (stress)
    vix = Series("VIX INDEX:PX_LAST")
    vix3m = Series("VIX3M INDEX:PX_LAST")
    if not vix.empty and not vix3m.empty:
        ts = -(vix3m - vix)  # Negative term spread = backwardation = stress
        components["VIX TS"] = StandardScalar(ts.dropna(), 252)

    # SKEW (tail risk pricing)
    skew = Series("SKEW INDEX:PX_LAST")
    if not skew.empty:
        components["SKEW"] = StandardScalar(skew.dropna(), 252)

    # Credit stress
    hy = Series("BAMLH0A0HYM2")
    if not hy.empty:
        components["Credit"] = StandardScalar(hy.dropna(), 252)

    # Equity-bond regime (positive corr = stress)
    spx = Series("SPX INDEX:PX_LAST").pct_change()
    y10 = Series("TRYUS10Y:PX_YTM").diff()
    if not spx.empty and not y10.empty:
        corr = spx.rolling(window).corr(y10).dropna()
        components["Eq-Bond Corr"] = StandardScalar(corr, 252)

    if not components:
        return pd.Series(dtype=float, name="Tail Risk Index")

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Tail Risk Index"
    return s


# ── Sector Rotation ─────────────────────────────────────────────────────────


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


# ── Sector Helpers ──────────────────────────────────────────────────────────

def _load_sectors(sector_map: dict[str, str], freq: str = "W") -> pd.DataFrame:
    """Load sector price data into a DataFrame."""
    data = {}
    for name, code in sector_map.items():
        try:
            s = Series(code, freq=freq)
            if len(s.dropna()) > 100:
                data[name] = s
        except Exception:
            logger.debug("Failed to load sector data for '%s' (%s)", name, code, exc_info=True)
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
    if spx.empty:
        return pd.DataFrame()
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
    return s.dropna()


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
    if kospi.empty:
        return pd.DataFrame()
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
    return s.dropna()


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
    if kr.empty or us.empty:
        return pd.Series(dtype=float)
    s = (kr / us).dropna()
    s.name = "KR Tech / US Tech"
    return s


def kr_financials_vs_us_financials(freq: str = "W") -> pd.Series:
    """KOSPI 금융 vs US XLF relative ratio.

    Rising = Korean financials outperforming (KR rate/growth cycle favorable).
    """
    kr = Series("A021:PX_LAST", freq=freq)
    us = Series("XLF US EQUITY:PX_LAST", freq=freq)
    if kr.empty or us.empty:
        return pd.Series(dtype=float)
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
    if sectors.empty:
        return pd.Series(dtype=float)
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


# ── Fed Dollar Indices ───────────────────────────────────────────────────


def fed_broad_dollar() -> pd.Series:
    """Federal Reserve Broad Trade-Weighted Dollar Index.

    Broader than DXY (26 currencies vs 6). Includes EM currencies
    weighted by bilateral trade. Better measure of USD competitiveness.
    Rising = USD strengthening = headwind for EM and US multinationals.

    Source: Federal Reserve Board (FRBJXRATEB@US).
    """
    s = Series("FRBJXRATEB@US")
    if s.empty:
        return pd.Series(dtype=float, name="Fed Broad Dollar")
    s.name = "Fed Broad Dollar"
    return s.dropna()


def fed_em_dollar() -> pd.Series:
    """Federal Reserve Dollar Index vs Other Important Trading Partners (EM).

    Trade-weighted USD against emerging market and other non-major
    currencies. Rising = USD strength vs EM currencies.
    More sensitive to commodity and EM capital flow cycles than DXY.

    Source: Federal Reserve Board (FRBJXRATEOITP@US).
    """
    s = Series("FRBJXRATEOITP@US")
    if s.empty:
        return pd.Series(dtype=float, name="Fed EM Dollar")
    s.name = "Fed EM Dollar"
    return s.dropna()
