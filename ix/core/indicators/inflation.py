from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series, MultiSeries
from ix.core.transforms import StandardScalar, Offset


def inflation_momentum() -> pd.DataFrame:
    """CPI and PPI short-term annualized rates (%).

    3-month and 6-month annualized rates capture turning points
    much faster than year-over-year. A 3m rate rolling over while
    YoY is still rising signals peak inflation ahead.
    """
    cpi = Series("USPR1980783:PX_LAST", freq="ME").ffill()
    ppi = Series("USPR7664543:PX_LAST", freq="ME").ffill()
    if cpi.empty or ppi.empty:
        return pd.DataFrame()

    return MultiSeries(
        **{
            "CPI 3m Ann": cpi.pct_change(3).mul(4).mul(100),
            "CPI 6m Ann": cpi.pct_change(6).mul(2).mul(100),
            "CPI YoY": cpi.pct_change(12).mul(100),
            "PPI 3m Ann": ppi.pct_change(3).mul(4).mul(100),
            "PPI 6m Ann": ppi.pct_change(6).mul(2).mul(100),
            "PPI YoY": ppi.pct_change(12).mul(100),
        }
    )


def inflation_surprise() -> pd.Series:
    """CPI YoY deviation from its own 12-month moving average (pp).

    When CPI YoY overshoots its trailing average, inflation is
    accelerating beyond recent expectations. Positive = hawkish risk.
    Negative = disinflationary surprise.
    """
    cpi = Series("USPR1980783:PX_LAST", freq="ME").ffill()
    if cpi.empty:
        return pd.Series(dtype=float)
    yoy = cpi.pct_change(12).mul(100)
    trend = yoy.rolling(12).mean()
    s = (yoy - trend).dropna()
    s.name = "CPI YoY Surprise"
    return s


def breakeven_momentum(window: int = 20) -> pd.Series:
    """Rate of change in 10Y breakeven inflation expectations (pp).

    Rapidly rising breakevens signal inflation re-pricing.
    Rapidly falling signals disinflation expectations.
    """
    nominal = Series("FRNTRSYLD100")
    tips = Series("FRNTIPYLD010")
    if nominal.empty or tips.empty:
        return pd.Series(dtype=float)
    bei = (nominal - tips).dropna()
    s = bei.diff(window)
    s.name = "Breakeven Momentum"
    return s.dropna()


def oil_leading_cpi(lead_months: int = 6) -> pd.DataFrame:
    """Oil YoY vs CPI YoY, with oil time-shifted forward by lead_months.

    Crude oil leads headline CPI by ~6 months. Useful for
    forecasting where CPI is headed.
    """
    cpi = Series("USPR1980783:PX_LAST", freq="ME").ffill()
    cpi_yoy = cpi.pct_change(12).mul(100)
    cpi_yoy.name = "CPI YoY"

    oil = Series("CL1 Comdty:PX_LAST", freq="ME")
    if cpi.empty or oil.empty:
        return pd.DataFrame()
    oil_yoy = oil.pct_change(12).mul(100)
    oil_yoy_lead = Offset(oil_yoy, months=lead_months)
    oil_yoy_lead.name = f"Oil YoY ({lead_months}M Lead)"

    return MultiSeries(**{cpi_yoy.name: cpi_yoy, oil_yoy_lead.name: oil_yoy_lead}).dropna()


def wage_price_spiral() -> pd.Series:
    """Wage-price spiral indicator: wage growth minus core services inflation.

    Uses Average Hourly Earnings (production workers) YoY minus Core CPI YoY.
    Positive = wages outpacing inflation (spiral risk).
    Negative = real wages falling (disinflation).
    Near zero = equilibrium.

    Source: BLS (AHETPI, CPILFESL)
    """
    wages = Series("AHETPI:PX_LAST")
    cpi = Series("CPILFESL")
    if wages.empty or cpi.empty:
        return pd.Series(dtype=float)
    wages_yoy = wages.pct_change(12) * 100
    cpi_yoy = cpi.pct_change(12) * 100
    gap = wages_yoy - cpi_yoy
    gap.name = "Wage-Price Spiral"
    return gap.dropna()


def commodity_inflation_pressure(window: int = 160) -> pd.Series:
    """Composite commodity inflation pressure index.

    Average z-score of oil, copper, and broad commodity YoY changes.
    Rising = inflationary pressure building.
    Falling = disinflationary.
    """
    oil_yoy = Series("CL1 Comdty:PX_LAST", freq="ME").pct_change(12).mul(100)
    copper_yoy = Series("COPPER CURNCY:PX_LAST", freq="ME").pct_change(12).mul(100)
    crb_yoy = Series("BCOM-CME:PX_LAST", freq="ME").pct_change(12).mul(100)
    if oil_yoy.empty or copper_yoy.empty or crb_yoy.empty:
        return pd.Series(dtype=float)

    z_oil = StandardScalar(oil_yoy.dropna(), window)
    z_copper = StandardScalar(copper_yoy.dropna(), window)
    z_crb = StandardScalar(crb_yoy.dropna(), window)

    s = pd.concat([z_oil, z_copper, z_crb], axis=1).mean(axis=1).dropna()
    s.name = "Commodity Inflation Pressure"
    return s
