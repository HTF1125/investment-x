from __future__ import annotations

import pandas as pd

from ix.db.query import Series


def fed_net_liquidity() -> pd.Series:
    """Fed Net Liquidity (Assets - Treasury General Account - Reverse Repo) in trillions USD."""
    asset = Series("WALCL").div(1_000_000)
    treasury = Series("WTREGEN").div(1_000_000)
    repo = Series("RRPONTSYD").div(1_000)

    df = pd.concat({"asset": asset, "treasury": treasury, "repo": repo}, axis=1)
    weekly = df.resample("W-WED").last().ffill()
    weekly["net_liquidity_T"] = weekly["asset"] - weekly["treasury"] - weekly["repo"]
    daily = weekly["net_liquidity_T"].resample("B").ffill()
    return daily.dropna()


def m2_us(freq: str = "ME") -> pd.Series:
    """US M2 money supply in USD trillions."""
    s = Series("US.MAM2", freq=freq) / 1000
    s.name = "US"
    return s


def m2_eu(freq: str = "ME") -> pd.Series:
    """EU M2 money supply in USD trillions."""
    fx = Series("EURUSD Curncy:PX_LAST", freq=freq)
    s = Series("EUZ.MAM2", freq=freq).mul(fx).div(1000_000)
    s.name = "EU"
    return s


def m2_uk(freq: str = "ME") -> pd.Series:
    """UK M2 money supply in USD trillions."""
    fx = Series("USDGBP Curncy:PX_LAST", freq=freq)
    s = Series("GB.MAM2", freq=freq).div(1000_000).div(fx)
    s.name = "UK"
    return s


def m2_cn(freq: str = "ME") -> pd.Series:
    """China M2 money supply in USD trillions."""
    fx = Series("USDCNY Curncy:PX_LAST", freq=freq)
    s = Series("CN.MAM2", freq=freq).div(10_000).div(fx)
    s.name = "CN"
    return s.dropna()


def m2_jp(freq: str = "ME") -> pd.Series:
    """Japan M2 money supply in USD trillions."""
    fx = Series("USDJPY Curncy:PX_LAST", freq=freq)
    s = Series("JP.MAM2", freq=freq).div(10_000).div(fx)
    s.name = "JP"
    return s.dropna()


def m2_kr(freq: str = "ME") -> pd.Series:
    """Korea M2 money supply in USD trillions."""
    fx = Series("USDKRW Curncy:PX_LAST", freq=freq)
    s = Series("KR.MAM2", freq=freq).div(1_000).div(fx)
    s.name = "KR"
    return s.dropna()


def m2_ch(freq: str = "ME") -> pd.Series:
    """Switzerland M2 money supply in USD trillions."""
    fx = Series("USDCHF Curncy:PX_LAST", freq=freq)
    s = Series("CH.MAM2", freq=freq).div(1_000_000).div(fx)
    s.name = "CH"
    return s.dropna()


def m2_ca(freq: str = "ME") -> pd.Series:
    """Canada M2 money supply in USD trillions."""
    fx = Series("USDCAD Curncy:PX_LAST", freq=freq).ffill()
    s = Series("CA.MAM2", freq=freq).div(1_000_000).div(fx)
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
    """
    credit = Series("TOTBKCR", freq=freq)
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


# Backward-compatible aliases
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
