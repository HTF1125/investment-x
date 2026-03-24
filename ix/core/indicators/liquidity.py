from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series, MultiSeries
from ix.core.transforms import StandardScalar


# ── Fed Liquidity & M2 ───────────────────────────────────────────────────────


def fed_net_liquidity() -> pd.Series:
    """Fed Net Liquidity (Assets - Treasury General Account - Reverse Repo) in trillions USD."""
    asset = Series("WALCL").div(1_000_000)
    treasury = Series("WTREGEN").div(1_000_000)
    repo = Series("RRPONTSYD").div(1_000)
    if asset.empty or treasury.empty or repo.empty:
        return pd.Series(dtype=float)

    df = pd.concat({"asset": asset, "treasury": treasury, "repo": repo}, axis=1)
    weekly = df.resample("W-WED").last().ffill()
    weekly["net_liquidity_T"] = weekly["asset"] - weekly["treasury"] - weekly["repo"]
    daily = weekly["net_liquidity_T"].resample("B").ffill()
    return daily.dropna()


def m2_us(freq: str = "ME") -> pd.Series:
    """US M2 money supply in USD trillions."""
    s = Series("US.MAM2", freq=freq) / 1000
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "US"
    return s.dropna()


def m2_eu(freq: str = "ME") -> pd.Series:
    """EU M2 money supply in USD trillions."""
    fx = Series("EURUSD Curncy:PX_LAST", freq=freq)
    s = Series("EUZ.MAM2", freq=freq).mul(fx).div(1000_000)
    if fx.empty or s.empty:
        return pd.Series(dtype=float)
    s.name = "EU"
    return s.dropna()


def m2_uk(freq: str = "ME") -> pd.Series:
    """UK M2 money supply in USD trillions."""
    fx = Series("USDGBP Curncy:PX_LAST", freq=freq)
    s = Series("GB.MAM2", freq=freq).div(1000_000).div(fx)
    if fx.empty or s.empty:
        return pd.Series(dtype=float)
    s.name = "UK"
    return s.dropna()


def m2_cn(freq: str = "ME") -> pd.Series:
    """China M2 money supply in USD trillions."""
    fx = Series("USDCNY Curncy:PX_LAST", freq=freq)
    s = Series("CN.MAM2", freq=freq).div(10_000).div(fx)
    if fx.empty or s.empty:
        return pd.Series(dtype=float)
    s.name = "CN"
    return s.dropna()


def m2_jp(freq: str = "ME") -> pd.Series:
    """Japan M2 money supply in USD trillions."""
    fx = Series("USDJPY Curncy:PX_LAST", freq=freq)
    s = Series("JP.MAM2", freq=freq).div(10_000).div(fx)
    if fx.empty or s.empty:
        return pd.Series(dtype=float)
    s.name = "JP"
    return s.dropna()


def m2_kr(freq: str = "ME") -> pd.Series:
    """Korea M2 money supply in USD trillions."""
    fx = Series("USDKRW Curncy:PX_LAST", freq=freq)
    s = Series("KR.MAM2", freq=freq).div(1_000).div(fx)
    if fx.empty or s.empty:
        return pd.Series(dtype=float)
    s.name = "KR"
    return s.dropna()


def m2_ch(freq: str = "ME") -> pd.Series:
    """Switzerland M2 money supply in USD trillions."""
    fx = Series("USDCHF Curncy:PX_LAST", freq=freq)
    s = Series("CH.MAM2", freq=freq).div(1_000_000).div(fx)
    if fx.empty or s.empty:
        return pd.Series(dtype=float)
    s.name = "CH"
    return s.dropna()


def m2_ca(freq: str = "ME") -> pd.Series:
    """Canada M2 money supply in USD trillions."""
    fx = Series("USDCAD Curncy:PX_LAST", freq=freq).ffill()
    s = Series("CA.MAM2", freq=freq).div(1_000_000).div(fx)
    if fx.empty or s.empty:
        return pd.Series(dtype=float)
    s.name = "CA"
    return s.dropna()


def m2_world(freq: str = "ME") -> pd.DataFrame:
    """Global M2 breakdown by country in USD trillions."""
    data = pd.concat(
        [m2_us(freq), m2_uk(freq), m2_eu(freq), m2_cn(freq),
         m2_jp(freq), m2_kr(freq), m2_ca(freq), m2_ch(freq)],
        axis=1,
    ).ffill()
    return data.dropna()


def m2_world_total(freq: str = "ME") -> pd.Series:
    """Global M2 total in USD trillions."""
    return m2_world(freq).sum(axis=1).ffill()


def m2_world_total_yoy(freq: str = "ME") -> pd.Series:
    """Global M2 year-over-year growth (%)."""
    s = m2_world_total(freq).pct_change(12).mul(100)
    s.name = "Global M2 YoY"
    return s.dropna()


def credit_impulse(freq: str = "ME") -> pd.Series:
    """Credit impulse: change in credit growth (2nd derivative of credit).

    Uses US bank credit as proxy. Leads GDP and equities by 6-9 months.
    LOANINV = Bank Credit, All Commercial Banks (FRED H.8).
    """
    credit = Series("LOANINV", freq=freq)
    if credit.empty:
        credit = Series("TOTBKCR", freq=freq)  # legacy fallback
    if credit.empty:
        return pd.Series(dtype=float, name="Credit Impulse")
    credit_yoy = credit.pct_change(12 if freq == "ME" else 52)
    impulse = credit_yoy.diff(3 if freq == "ME" else 13)
    impulse.name = "Credit Impulse"
    return impulse.dropna()


def tga_drawdown() -> pd.Series:
    """Treasury General Account drawdown rate (13-week change in TGA balance).

    When TGA is being drawn down (negative change), it injects liquidity
    into the financial system — bullish for risk assets. When TGA is being
    refilled (positive change via T-bill issuance), it drains liquidity.

    Returns negative values when TGA is being drawn down (liquidity injection)
    and positive when being refilled (liquidity drain). Inverted in the
    indicator definition so that drawdown = bullish signal.
    """
    tga = Series("WTREGEN").div(1_000_000)  # Convert to trillions USD
    if tga.empty:
        return pd.Series(dtype=float)
    weekly = tga.resample("W-WED").last().ffill()
    # 13-week change (quarterly pace of drawdown/refill)
    drawdown = weekly.diff(13)
    drawdown.name = "TGA Drawdown"
    daily = drawdown.resample("B").ffill()
    return daily.dropna()


def treasury_net_issuance() -> pd.Series:
    """Net Treasury issuance pressure: TGA change + debt change.

    Combines TGA refilling (supply pressure) with public debt growth
    to capture net fiscal flow impact on liquidity. Rising = more
    supply pressure = bearish for liquidity.
    """
    tga = Series("WTREGEN").div(1_000_000)
    debt = Series("GFDEBTN")  # Federal debt, quarterly
    weekly_tga = tga.resample("W-WED").last().ffill()
    tga_chg = weekly_tga.diff(13)

    if debt.empty:
        result = tga_chg
    else:
        debt_q = debt.resample("W-WED").last().ffill()
        debt_chg = debt_q.pct_change(13).mul(100)
        df = pd.concat({"tga": tga_chg, "debt": debt_chg}, axis=1).dropna()
        # Standardize and combine (equal weight)
        for col in df.columns:
            m = df[col].rolling(52, min_periods=26).median()
            mad = (df[col] - m).abs().rolling(52, min_periods=26).median() * 1.4826
            df[col] = (df[col] - m) / mad.replace(0, float("nan"))
        result = df.mean(axis=1)

    result.name = "Treasury Net Issuance"
    daily = result.resample("B").ffill()
    return daily.dropna()


def global_liquidity_yoy(freq: str = "ME") -> pd.Series:
    """Global central bank liquidity proxy: Fed + ECB + BOJ balance sheets YoY.

    Uses Fed total assets (WALCL), proxied via M2 aggregates for other CBs.
    This is a simplified proxy — true CB balance sheet data requires Bloomberg.
    """
    total = m2_world_total(freq)
    yoy = total.pct_change(12 if freq == "ME" else 52).mul(100)
    yoy.name = "Global Liquidity YoY"
    return yoy.dropna()


# ── Cross Border Capital Style Global Liquidity ──────────────────────────────


# Central bank balance sheet codes (FactSet: local currency)
# Format: (country_code, CBASSET_code, FX_code, divisor_to_trillions_usd)
# divisor: scale local currency to trillions, then FX converts to USD
_CB_CONFIGS = [
    # (label, asset_code, fx_code, asset_divisor, fx_is_usdxxx)
    # US: Fed assets in Mil USD -> / 1e6 = T USD (no FX needed)
    ("Fed", "WALCL", None, 1_000_000, False),
    # ECB: Mil EUR -> / 1e6 * EURUSD = T USD
    ("ECB", "EUZ.CBASSET:PX_LAST", "EURUSD Curncy:PX_LAST", 1_000_000, False),
    # BOJ: Thous JPY -> * 1000 / USDJPY / 1e12 = T USD
    ("BOJ", "JP.CBASSET:PX_LAST", "USDJPY Curncy:PX_LAST", 1, True),
    # PBOC: 100 Mil CNY -> * 100 / USDCNY / 1e6 = T USD
    ("PBOC", "CN.CBASSET:PX_LAST", "USDCNY Curncy:PX_LAST", 1, True),
    # BOE: Mil GBP -> / 1e6 * GBPUSD = T USD
    ("BOE", "GB.CBASSET:PX_LAST", "GBPUSD Curncy:PX_LAST", 1_000_000, False),
    # BOC: Mil CAD -> / 1e6 / USDCAD = T USD
    ("BOC", "CA.CBASSET:PX_LAST", "USDCAD Curncy:PX_LAST", 1_000_000, True),
    # RBA: Mil AUD -> / 1e6 / USDAUD = T USD
    ("RBA", "AU.CBASSET:PX_LAST", "USDAUD Curncy:PX_LAST", 1_000_000, True),
    # RBI: Bil INR -> / 1e3 / USDINR = T USD
    ("RBI", "IN.CBASSET:PX_LAST", "USDINR Curncy:PX_LAST", 1_000, True),
    # SNB: Mil CHF -> / 1e6 / USDCHF = T USD
    ("SNB", "CH.CBASSET:PX_LAST", "USDCHF Curncy:PX_LAST", 1_000_000, True),
    # BOK: Bil KRW -> / 1e3 / USDKRW = T USD
    ("BOK", "KR.CBASSET:PX_LAST", "USDKRW Curncy:PX_LAST", 1_000, True),
    # Riksbank: Mil SEK -> / 1e6 / USDSEK = T USD
    ("Riksbank", "SE.CBASSET:PX_LAST", "USDSEK Curncy:PX_LAST", 1_000_000, True),
    # RBNZ: Mil NZD -> / 1e6 / USDNZD = T USD
    ("RBNZ", "NZ.CBASSET:PX_LAST", "USDNZD Curncy:PX_LAST", 1_000_000, True),
    # BNM: Mil MYR -> skip (no reliable FX)
    # BCB: Mil BRL -> / 1e6 / USDBRL = T USD
    ("BCB", "BR.CBASSET:PX_LAST", "USDBRL Curncy:PX_LAST", 1_000_000, True),
]


def global_liquidity_index(freq: str = "ME") -> pd.Series:
    """Cross Border Capital style Global Liquidity Index ($T).

    Sum of 13 central bank balance sheets converted to USD trillions,
    with US adjusted for TGA and RRP (net Fed liquidity).
    Inspired by Michael Howell / Cross Border Capital methodology.

    Components: Fed (net), ECB, BOJ, PBOC, BOE, BOC, RBA, RBI, SNB, BOK,
    Riksbank, RBNZ, BCB.

    The 65-month (5.4 year) global liquidity cycle drives asset prices.
    Rising = risk-on (equities, credit, crypto). Falling = risk-off.
    Source: Howell, 'Capital Wars' (2020); capitalwars.substack.com
    """
    components = {}

    for label, asset_code, fx_code, divisor, fx_is_usdxxx in _CB_CONFIGS:
        asset = Series(asset_code, freq=freq)
        # Fix RBI data: FactSet alternates between Crore INR (~100x) and Bil INR
        # Values > 200,000 are in Crore INR (10M), divide by 100 to get Bil INR
        if "IN.CBASSET" in asset_code and not asset.empty:
            asset = asset.where(asset < 200_000, asset / 100)
        if asset.empty:
            continue

        if fx_code is None:
            # USD-denominated (Fed)
            usd_t = asset / divisor
        else:
            fx = Series(fx_code, freq=freq).ffill()
            if fx.empty:
                continue
            if fx_is_usdxxx:
                # USDXXX: divide by FX to get USD
                if divisor == 1:
                    # Special: Thous JPY -> * 1000 / USDJPY / 1e12
                    if "JPY" in fx_code:
                        usd_t = (asset * 1_000 / fx / 1e12)
                    elif "CNY" in fx_code:
                        usd_t = (asset * 100 / fx / 1e6)
                    elif "BRL" in fx_code:
                        usd_t = (asset * 1_000 / fx / 1e12)
                    else:
                        usd_t = asset / divisor / fx
                else:
                    usd_t = asset / divisor / fx
            else:
                # XXXUSD: multiply by FX to get USD
                usd_t = asset / divisor * fx

        components[label] = usd_t.dropna()

    if not components:
        return pd.Series(dtype=float, name="Global Liquidity Index ($T)")

    # Resample all components to month-end (CB balance sheets are monthly)
    # then forward-fill to handle reporting lags
    monthly = {}
    for label, s in components.items():
        m = s.resample("ME").last()
        monthly[label] = m
    df = pd.DataFrame(monthly).ffill(limit=3).dropna(how="all")
    # Fill remaining NaN columns with 0 (CB not yet reporting in early dates)
    df = df.fillna(0)

    # Adjust Fed for TGA and RRP
    if "Fed" in df.columns:
        tga = Series("WTREGEN", freq=freq) / 1_000_000
        rrp = Series("RRPONTSYD", freq=freq) / 1_000
        if not tga.empty:
            tga_aligned = tga.reindex(df.index).ffill()
            df["Fed"] = df["Fed"] - tga_aligned.fillna(0)
        if not rrp.empty:
            rrp_aligned = rrp.reindex(df.index).ffill()
            df["Fed"] = df["Fed"] - rrp_aligned.fillna(0)

    total = df.sum(axis=1)
    total.name = "Global Liquidity Index ($T)"
    return total.dropna()


def global_liquidity_index_yoy() -> pd.Series:
    """Global Liquidity Index YoY change (%).

    Year-over-year change in the Cross Border Capital style global
    liquidity aggregate. Positive = expanding liquidity (risk-on).
    Leads equity returns by ~6 months per Howell's research.
    """
    total = global_liquidity_index()
    if total.empty:
        return pd.Series(dtype=float, name="Global Liquidity YoY %")
    yoy = total.pct_change(12) * 100
    yoy.name = "Global Liquidity YoY %"
    return yoy.dropna()


def global_liquidity_cycle(window: int = 18) -> pd.Series:
    """Global Liquidity Cycle oscillator (z-score).

    Z-scored momentum of global liquidity index. Howell's 65-month cycle
    shows liquidity peaks/troughs lead asset prices by 6-12 months.
    Values > 1 = expanding rapidly. < -1 = contracting.
    Source: Howell, 'Capital Wars'; Cross Border Capital
    """
    total = global_liquidity_index()
    if total.empty:
        return pd.Series(dtype=float, name="Global Liquidity Cycle")
    mom = total.pct_change(3)  # 3-month (quarterly) momentum
    z = StandardScalar(mom.dropna(), window)
    z.name = "Global Liquidity Cycle"
    return z.dropna()


def m2_world_contribution(freq: str = "ME") -> pd.DataFrame:
    """Global M2 contribution to growth by country."""
    if freq == "ME":
        period = 12
    elif freq.startswith("W"):
        period = 52
    else:
        period = 12

    world = m2_world(freq)
    total = m2_world_total(freq)
    return (
        world.diff(period)
        .dropna()
        .div(total.shift(period), axis=0)
        .dropna()
    )


# ── Money Markets ─────────────────────────────────────────────────────────────


# ── Overnight Rates ────────────────────────────────────────────────────────


def sofr_rate(freq: str = "D") -> pd.Series:
    """Secured Overnight Financing Rate (%).

    Baseline overnight funding cost, replaced LIBOR.
    Spikes indicate repo market stress (e.g., Sep 2019 event).
    """
    s = Series("SOFR", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "SOFR"
    return s.dropna()


def sofr_fed_funds_spread() -> pd.Series:
    """SOFR minus Effective Fed Funds Rate (bps).

    Measures repo market pressure relative to policy rate.
    Widening = collateral scarcity or funding stress.
    Narrowing = ample reserves.
    """
    sofr = Series("SOFR")
    effr = Series("EFFR")
    if effr.empty:
        effr = Series("DFF")  # FRED daily Fed Funds
    if sofr.empty or effr.empty:
        return pd.Series(dtype=float, name="SOFR-FFR Spread")
    s = ((sofr - effr) * 100).dropna()
    s.name = "SOFR-FFR Spread (bps)"
    return s


# ── Commercial Paper & Short-Term Credit ───────────────────────────────────


def commercial_paper_spread() -> pd.Series:
    """AA Financial Commercial Paper - Treasury Bill spread (bps).

    Short-term credit stress indicator. Widens during funding crises.
    2008 blowout was early GFC warning. Normally 10-30bps.
    """
    cp = Series("DCPF3M")
    tbill = Series("DTB3")
    if cp.empty or tbill.empty:
        return pd.Series(dtype=float, name="CP-TBill Spread")
    s = ((cp - tbill) * 100).dropna()
    s.name = "CP-TBill Spread (bps)"
    return s


def commercial_paper_spread_zscore(window: int = 252) -> pd.Series:
    """Z-scored CP-TBill spread for regime detection.

    > 2σ = funding stress. < -1σ = extremely easy conditions.
    """
    spread = commercial_paper_spread()
    if spread.empty:
        return pd.Series(dtype=float, name="CP Spread Z-Score")
    s = StandardScalar(spread, window)
    s.name = "CP Spread Z-Score"
    return s.dropna()


# ── Money Market Funds ─────────────────────────────────────────────────────


def money_market_fund_assets(freq: str = "ME") -> pd.Series:
    """Total Money Market Fund Assets ($B).

    Cash on the sidelines. Record MMF assets = potential equity fuel.
    Sharp outflows from MMFs often coincide with risk-on rallies.
    """
    s = Series("MMMFFAQ027S", freq=freq)
    if not s.empty:
        s = s / 1000  # Convert to $T for consistency
    s.name = "MMF Assets ($T)"
    return s.dropna()


def money_market_fund_yoy(freq: str = "ME") -> pd.Series:
    """MMF Assets YoY growth (%).

    Rapid growth = risk aversion / flight to safety.
    Declining = money moving back to risk assets.
    """
    mmf = Series("MMMFFAQ027S", freq=freq)
    if mmf.empty:
        return pd.Series(dtype=float)
    s = mmf.pct_change(12) * 100
    s.name = "MMF Assets YoY"
    return s.dropna()


def money_market_vs_equities() -> pd.Series:
    """MMF Assets / S&P 500 Market Cap ratio (proxy).

    Sideline cash relative to equity valuations.
    High ratio = potential fuel for rally. Low ratio = fully invested.
    Uses Wilshire 5000 as equity market cap proxy.
    """
    mmf = Series("MMMFFAQ027S")
    wilshire = Series("WILL5000IND")
    if mmf.empty or wilshire.empty:
        return pd.Series(dtype=float, name="MMF/Equity Ratio")
    # Normalize Wilshire to approximate $T market cap
    s = (mmf / (wilshire * 1e9 / 1e12)).dropna()
    s.name = "MMF/Equity Ratio"
    return s


# ── Reverse Repo ───────────────────────────────────────────────────────────


def reverse_repo_usage(freq: str = "D") -> pd.Series:
    """Fed Reverse Repo Facility Usage ($T).

    Measures excess liquidity in the system. Declining RRP = liquidity
    draining into T-bills (net positive for risk assets if TGA stable).
    Already used in net liquidity calc but useful standalone.
    """
    s = Series("RRPONTSYD", freq=freq)
    if not s.empty:
        s = s / 1e9  # Convert to $T
    s.name = "Reverse Repo ($T)"
    return s.dropna()


def reverse_repo_momentum(window: int = 13) -> pd.Series:
    """Reverse repo weekly change ($T).

    Rapidly declining RRP = liquidity injection into markets.
    Rising RRP = liquidity absorption.
    """
    rrp = reverse_repo_usage(freq="W")
    s = rrp.diff(window).dropna()
    s.name = "RRP Momentum"
    return s


# ── Composite ──────────────────────────────────────────────────────────────


def funding_stress_index(window: int = 252) -> pd.Series:
    """Composite funding stress index from money market signals.

    Combines CP spread, SOFR-FFR spread into a single z-scored signal.
    Positive = funding stress. Negative = easy funding conditions.
    """
    components = {}

    cp_spread = commercial_paper_spread()
    if not cp_spread.empty:
        components["CP"] = StandardScalar(cp_spread, window)

    sofr_spread = sofr_fed_funds_spread()
    if not sofr_spread.empty:
        components["SOFR"] = StandardScalar(sofr_spread, window)

    if not components:
        return pd.Series(dtype=float, name="Funding Stress Index")

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Funding Stress Index"
    return s


# ── Backward-Compatible Aliases ───────────────────────────────────────────


def excess_liquidity() -> pd.Series:
    """Fed excess liquidity: total reserves ($B).

    Since March 2020, reserve requirements are zero, so total reserves
    (TOTRESNS) equals excess reserves. This is the liquidity buffer
    that flows into risk assets. Rising = more liquidity chasing assets.
    Falling = drain.

    Source: Federal Reserve (TOTRESNS)
    """
    total_reserves = Series("TOTRESNS:PX_LAST")  # Bil USD
    if total_reserves.empty:
        return pd.Series(dtype=float)
    s = total_reserves
    s.name = "Excess Liquidity ($B)"
    return s.dropna()


class FedNetLiquidity:
    @staticmethod
    def calculate() -> pd.Series:
        return fed_net_liquidity()


class M2:
    """Backward-compatible wrapper for M2 functions."""

    def __init__(self, freq: str = "ME", currency: str = "USD") -> None:
        self.freq = freq

    @property
    def US(self) -> pd.Series:
        return m2_us(self.freq)

    @property
    def EU(self) -> pd.Series:
        return m2_eu(self.freq)

    @property
    def UK(self) -> pd.Series:
        return m2_uk(self.freq)

    @property
    def CN(self) -> pd.Series:
        return m2_cn(self.freq)

    @property
    def JP(self) -> pd.Series:
        return m2_jp(self.freq)

    @property
    def KR(self) -> pd.Series:
        return m2_kr(self.freq)

    @property
    def CH(self) -> pd.Series:
        return m2_ch(self.freq)

    @property
    def CA(self) -> pd.Series:
        return m2_ca(self.freq)

    @property
    def World(self) -> pd.DataFrame:
        return m2_world(self.freq)

    @property
    def WorldTotal(self) -> pd.Series:
        return m2_world_total(self.freq)

    @property
    def WorldTotalYoY(self) -> pd.Series:
        return m2_world_total_yoy(self.freq)

    @property
    def WorldContribution(self) -> pd.DataFrame:
        return m2_world_contribution(self.freq)
