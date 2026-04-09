from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series
from ix.common.data.transforms import StandardScalar


# ── Fed Balance Sheet ───────────────────────────────────────────────────────


def fed_total_assets(freq: str = "W") -> pd.Series:
    """Federal Reserve Total Assets (trillions USD).

    WALCL — most important liquidity variable for risk assets.
    Rising = QE / liquidity injection. Falling = QT / liquidity drain.
    """
    s = Series("WALCL", freq=freq) / 1_000_000
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "Fed Total Assets ($T)"
    return s.dropna()


def fed_assets_yoy() -> pd.Series:
    """Fed total assets year-over-year change (%).

    QE periods: +30-100% YoY. QT periods: -5 to -15% YoY.
    One of the strongest correlates with equity multiples.
    """
    assets = fed_total_assets()
    s = assets.pct_change(52) * 100
    s.name = "Fed Assets YoY"
    return s.dropna()


def fed_assets_momentum(window: int = 13) -> pd.Series:
    """Fed balance sheet quarterly momentum ($T change).

    Positive = balance sheet expanding. Negative = contracting.
    """
    assets = fed_total_assets()
    s = assets.diff(window).dropna()
    s.name = "Fed BS Momentum"
    return s


# ── G4 Central Bank Balance Sheets ──────────────────────────────────────────


def ecb_total_assets(freq: str = "W") -> pd.Series:
    """ECB Total Assets (trillions USD).

    Converted from EUR using EURUSD. ECB balance sheet is second largest
    after the Fed in terms of global liquidity impact.
    Uses Eurosystem consolidated financial statement (Mil EUR).
    """
    ecb_eur = Series("EUZ.CBASSET:PX_LAST", freq=freq)  # FactSet: Mil EUR
    if ecb_eur.empty:
        ecb_eur = Series("ECBASSETSW", freq=freq)  # FRED fallback
    if ecb_eur.empty:
        return pd.Series(dtype=float, name="ECB Total Assets ($T)")
    fx = Series("EURUSD Curncy:PX_LAST", freq=freq).ffill()
    s = (ecb_eur / 1_000_000 * fx).dropna()
    s.name = "ECB Total Assets ($T)"
    return s


def boj_total_assets(freq: str = "W") -> pd.Series:
    """Bank of Japan Total Assets (trillions USD).

    BOJ owns >50% of JGB market. Balance sheet changes affect
    global bond yields and yen carry trade dynamics.
    Uses FactSet series (Thous JPY) with FRED fallback (JPY 100M).
    """
    boj_jpy = Series("JP.CBASSET:PX_LAST", freq=freq)  # FactSet: Thous JPY
    fx = Series("USDJPY Curncy:PX_LAST", freq=freq).ffill()
    if not boj_jpy.empty:
        # Thous JPY -> trillions USD: * 1000 / fx / 1e12
        s = (boj_jpy * 1_000 / fx / 1e12).dropna()
        s.name = "BOJ Total Assets ($T)"
        return s
    boj_jpy = Series("JPNASSETS", freq=freq)  # FRED fallback: JPY 100M
    if boj_jpy.empty:
        return pd.Series(dtype=float, name="BOJ Total Assets ($T)")
    s = (boj_jpy / 10_000 / fx).dropna()
    s.name = "BOJ Total Assets ($T)"
    return s


def pboc_total_assets(freq: str = "W") -> pd.Series:
    """People's Bank of China Total Assets (trillions USD).

    PBOC balance sheet reflects China's monetary policy stance.
    Uses FactSet series (100 Mil CNY), converted via USDCNY.
    """
    pboc_cny = Series("CN.CBASSET:PX_LAST", freq=freq)  # FactSet: 100 Mil CNY
    if pboc_cny.empty:
        return pd.Series(dtype=float, name="PBOC Total Assets ($T)")
    fx = Series("USDCNY Curncy:PX_LAST", freq=freq).ffill()
    # 100 Mil CNY -> trillions USD: * 100 / fx / 1_000_000
    s = (pboc_cny * 100 / fx / 1_000_000).dropna()
    s.name = "PBOC Total Assets ($T)"
    return s


def g4_balance_sheet() -> pd.DataFrame:
    """G5 central bank balance sheets in USD trillions.

    Fed + ECB + BOJ + PBOC (+ BOE when available).
    Combined balance sheet drives global liquidity regime.
    """
    data = {}
    fed = fed_total_assets()
    if not fed.empty:
        data["Fed"] = fed
    ecb = ecb_total_assets()
    if not ecb.empty:
        data["ECB"] = ecb
    boj = boj_total_assets()
    if not boj.empty:
        data["BOJ"] = boj
    pboc = pboc_total_assets()
    if not pboc.empty:
        data["PBOC"] = pboc
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data).ffill().dropna(how="all")


def g4_balance_sheet_total() -> pd.Series:
    """G4 combined balance sheet total (trillions USD)."""
    df = g4_balance_sheet()
    if df.empty:
        return pd.Series(dtype=float, name="G4 Balance Sheet")
    s = df.sum(axis=1)
    s.name = "G4 Balance Sheet ($T)"
    return s.dropna()


def g4_balance_sheet_yoy() -> pd.Series:
    """G4 combined balance sheet YoY change (%).

    The single most important global liquidity indicator.
    Positive = net QE. Negative = net QT.
    """
    total = g4_balance_sheet_total()
    s = total.pct_change(52) * 100
    s.name = "G4 BS YoY"
    return s.dropna()


# ── Rate Expectations ───────────────────────────────────────────────────────


def fed_funds_implied(freq: str = "D") -> pd.Series:
    """Effective Federal Funds Rate.

    Tracks actual vs target rate. Sharp divergences from target
    signal liquidity stress in the banking system.
    """
    s = Series("EFFR", freq=freq)
    if s.empty:
        s = Series("DFF", freq=freq)  # Daily Fed Funds rate
    s.name = "Fed Funds Effective"
    return s.dropna()


def rate_cut_probability_proxy() -> pd.Series:
    """Rate cut probability proxy from 2Y yield vs Fed Funds.

    2Y yield below Fed Funds = market pricing cuts.
    Magnitude of gap approximates number of expected cuts.
    Each 25bp gap ≈ 1 expected cut within 12 months.
    """
    y2 = Series("TRYUS2Y:PX_YTM")
    ffr = Series("EFFR")
    if ffr.empty:
        ffr = Series("DFF")
    if y2.empty or ffr.empty:
        return pd.Series(dtype=float, name="Rate Cut Proxy")
    s = (ffr - y2).dropna()
    s.name = "Rate Cut Proxy (bp)"
    return s


def global_rate_divergence() -> pd.Series:
    """G4 rate divergence: std dev of major central bank policy rates.

    High divergence = carry trade opportunities but also instability risk.
    Low divergence = synchronized policy (often at cycle turning points).
    """
    rates = {}
    us = Series("EFFR")
    if not us.empty:
        rates["US"] = us
    ecb_rate = Series("ECBDFR")  # ECB deposit facility rate
    if not ecb_rate.empty:
        rates["ECB"] = ecb_rate
    boj_rate = Series("JPONBR")  # BOJ overnight rate
    if not boj_rate.empty:
        rates["BOJ"] = boj_rate

    if len(rates) < 2:
        return pd.Series(dtype=float, name="Rate Divergence")

    df = pd.DataFrame(rates).ffill().dropna()
    s = df.std(axis=1)
    s.name = "G4 Rate Divergence"
    return s.dropna()


# ── Liquidity Composite ─────────────────────────────────────────────────────


def central_bank_liquidity_composite(window: int = 120) -> pd.Series:
    """Central bank liquidity composite index.

    Combines: Fed assets momentum, G4 BS YoY, net liquidity (Fed),
    and rate cut expectations. Z-scored and averaged.
    Positive = net liquidity injection. Negative = net drain.
    """
    from ix.core.indicators.liquidity import fed_net_liquidity

    components = {}

    fed_mom = fed_assets_momentum()
    if not fed_mom.empty:
        components["Fed Momentum"] = StandardScalar(fed_mom, window)

    g4_yoy = g4_balance_sheet_yoy()
    if not g4_yoy.empty:
        components["G4 YoY"] = StandardScalar(g4_yoy, window)

    net_liq = fed_net_liquidity()
    if not net_liq.empty:
        net_liq_mom = net_liq.diff(13)
        components["Net Liq"] = StandardScalar(net_liq_mom.dropna(), window)

    cut_proxy = rate_cut_probability_proxy()
    if not cut_proxy.empty:
        components["Rate Cuts"] = StandardScalar(cut_proxy, window)

    if not components:
        return pd.Series(dtype=float, name="CB Liquidity Composite")

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "CB Liquidity Composite"
    return s


# ── Global CB Rate Cutting/Hiking Breadth ─────────────────────────────────


def _fetch_bis_policy_rates() -> pd.DataFrame:
    """Download BIS central bank policy rates (49 countries).

    Returns DataFrame: index=monthly dates, columns=country names, values=rate (%).
    Excludes individual Eurozone members (keeps 'Euro area').
    """
    import requests
    import zipfile
    import io

    url = "https://data.bis.org/static/bulk/WS_CBPOL_csv_col.zip"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    df_raw = pd.read_csv(z.open(z.namelist()[0]))

    monthly = df_raw[df_raw["Frequency"] == "Monthly"].copy()
    date_cols = [c for c in df_raw.columns if len(c) == 7 and c[4] == "-"]
    rates = monthly.set_index("Reference area")[date_cols].T
    rates.index = pd.to_datetime(rates.index, format="%Y-%m")
    rates = rates.apply(pd.to_numeric, errors="coerce")

    # Remove individual Eurozone members (keep 'Euro area')
    ez = [
        "Austria", "Belgium", "France", "Germany", "Greece",
        "Italy", "Netherlands", "Portugal", "Spain", "Croatia",
    ]
    rates = rates.drop(columns=[c for c in ez if c in rates.columns], errors="ignore")

    # Drop countries with <30% data coverage
    valid_pct = rates.notna().sum() / len(rates)
    return rates[valid_pct[valid_pct > 0.3].index]


def global_cb_rate_breadth(lookback: int = 6, threshold: float = 0.1) -> pd.DataFrame:
    """Global central bank rate cutting/hiking breadth.

    Downloads BIS policy rates for ~34 central banks.
    Computes 6-month rate change, counts cutting (<-10bp) and hiking (>+10bp).

    Returns DataFrame with columns:
        - Cutting: number of CBs cutting
        - Hiking: number of CBs hiking
        - Net Cutting %: (cutting - hiking) / total * 100

    Leads global PMI by 9-12 months (r≈0.50 at 12M lead).
    Leads equity returns (SPX YoY) by 6 months (r≈0.29).
    """
    rates = _fetch_bis_policy_rates()
    chg = rates.diff(lookback)
    cutting = (chg < -threshold).sum(axis=1)
    hiking = (chg > threshold).sum(axis=1)
    valid = chg.notna().sum(axis=1)

    result = pd.DataFrame({
        "Cutting": cutting,
        "Hiking": -hiking,  # Negative for stacked bar display
        "Net Cutting %": ((cutting - hiking) / valid * 100).round(1),
    }).dropna()
    result.index = result.index + pd.offsets.MonthEnd(0)
    return result
