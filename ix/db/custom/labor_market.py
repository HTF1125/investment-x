from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series, MultiSeries
from ix.core.transforms import StandardScalar


# ── JOLTS ──────────────────────────────────────────────────────────────────


def jolts_job_openings(freq: str = "ME") -> pd.Series:
    """JOLTS Job Openings (thousands).

    Demand-side labor signal. Leads wage inflation by 6-12 months.
    Peak openings precede labor market tightening.
    """
    s = Series("JTSJOL", freq=freq)
    s.name = "JOLTS Job Openings"
    return s.dropna()


def jolts_quits_rate(freq: str = "ME") -> pd.Series:
    """JOLTS Quits Rate (%).

    Worker confidence proxy — high quits = workers confident
    they can find better jobs. Leads wage growth.
    Above 2.5% = tight market. Below 1.5% = weak market.
    """
    s = Series("JTSQUR", freq=freq)
    s.name = "JOLTS Quits Rate"
    return s.dropna()


def jolts_hires_rate(freq: str = "ME") -> pd.Series:
    """JOLTS Hires Rate (%).

    Employer willingness to hire. Falling hires rate while
    openings stay high = skills mismatch or structural issue.
    """
    s = Series("JTSHIR", freq=freq)
    s.name = "JOLTS Hires Rate"
    return s.dropna()


def jolts_openings_unemployed_ratio(freq: str = "ME") -> pd.Series:
    """JOLTS Job Openings / Unemployed Persons ratio.

    Fed's preferred labor tightness gauge (Beveridge Curve).
    > 1.5 = extremely tight (inflationary). < 0.5 = severe slack.
    ~1.0 = balanced. This ratio drove much of the 2022-2024 Fed hawkishness.
    """
    openings = Series("JTSJOL", freq=freq)
    unemployed = Series("UNEMPLOY", freq=freq)
    if openings.empty or unemployed.empty:
        return pd.Series(dtype=float, name="Openings/Unemployed")
    s = (openings / unemployed).dropna()
    s.name = "Openings/Unemployed"
    return s


# ── Wages & Labor Cost ─────────────────────────────────────────────────────


def atlanta_fed_wage_tracker(freq: str = "ME") -> pd.Series:
    """Atlanta Fed Wage Growth Tracker (% YoY, median).

    Cleaner than Average Hourly Earnings because it controls for
    composition effects (job switching, industry mix).
    Above 4% = inflationary. Below 3% = benign.
    """
    s = Series("FRBATLWGT12MOVPONSA", freq=freq)
    if s.empty:
        # Fallback: use Average Hourly Earnings YoY
        ahe = Series("CES0500000003", freq=freq)
        if ahe.empty:
            return pd.Series(dtype=float, name="Wage Tracker")
        s = ahe.pct_change(12) * 100
    s.name = "Wage Tracker"
    return s.dropna()


def employment_cost_index(freq: str = "QE") -> pd.Series:
    """Employment Cost Index — Total Compensation (% QoQ, SA).

    Most comprehensive labor cost measure. Includes wages + benefits.
    Fed watches this closely for wage-price spiral risk.
    """
    s = Series("ECIALLCIV", freq=freq)
    s.name = "Employment Cost Index"
    return s.dropna()


def employment_cost_index_yoy(freq: str = "QE") -> pd.Series:
    """Employment Cost Index — Year-over-Year (%)."""
    eci = Series("ECIALLCIV", freq=freq)
    s = eci.pct_change(4) * 100
    s.name = "ECI YoY"
    return s.dropna()


def unit_labor_costs_yoy(freq: str = "QE") -> pd.Series:
    """Unit Labor Costs YoY (%).

    Core inflation driver. When ULC rises faster than productivity,
    firms must raise prices or compress margins.
    Above 4% = inflationary pressure. Below 2% = benign.
    """
    ulc = Series("ULCNFB", freq=freq)
    s = ulc.pct_change(4) * 100
    s.name = "Unit Labor Costs YoY"
    return s.dropna()


def nonfarm_productivity_yoy(freq: str = "QE") -> pd.Series:
    """Nonfarm Business Sector Productivity YoY (%).

    High productivity growth offsets wage inflation.
    When productivity > wage growth = non-inflationary expansion.
    When productivity < wage growth = margin/inflation pressure.
    """
    prod = Series("OPHNFB", freq=freq)
    s = prod.pct_change(4) * 100
    s.name = "Nonfarm Productivity YoY"
    return s.dropna()


# ── Broader Labor ──────────────────────────────────────────────────────────


def u6_unemployment(freq: str = "ME") -> pd.Series:
    """U6 Unemployment Rate (%).

    Broadest measure: includes marginally attached + part-time
    for economic reasons. Captures hidden slack missed by U3.
    """
    s = Series("U6RATE", freq=freq)
    s.name = "U6 Unemployment"
    return s.dropna()


def temp_employment(freq: str = "ME") -> pd.Series:
    """Temporary Help Services Employment (thousands).

    Classic leading indicator. Temps are hired first into
    recovery and fired first before recession. Leads payrolls
    by 3-6 months.
    """
    s = Series("TEMPHELPS", freq=freq)
    s.name = "Temp Employment"
    return s.dropna()


def temp_employment_yoy(freq: str = "ME") -> pd.Series:
    """Temp employment YoY change (%). Negative = recession warning."""
    temp = Series("TEMPHELPS", freq=freq)
    s = temp.pct_change(12) * 100
    s.name = "Temp Employment YoY"
    return s.dropna()


# ── Composite ──────────────────────────────────────────────────────────────


def labor_market_composite(window: int = 120) -> pd.Series:
    """Composite labor market health index.

    Combines JOLTS tightness, claims, temp employment,
    and wages into a single z-scored signal.
    Positive = tight market. Negative = loosening.
    """
    components = {}

    # Openings/unemployed ratio (higher = tighter)
    ratio = jolts_openings_unemployed_ratio()
    if not ratio.empty:
        components["Tightness"] = StandardScalar(ratio, window)

    # Claims (inverted — lower = better)
    claims = Series("ICSA")
    if not claims.empty:
        components["Claims"] = -StandardScalar(claims, window)

    # Temp employment momentum (positive = hiring)
    temp = Series("TEMPHELPS")
    if not temp.empty:
        temp_yoy = temp.pct_change(12).dropna()
        components["Temp"] = StandardScalar(temp_yoy, window)

    # Quits rate (higher = confident workers)
    quits = Series("JTSQUR")
    if not quits.empty:
        components["Quits"] = StandardScalar(quits, window)

    if not components:
        return pd.Series(dtype=float, name="Labor Market Composite")

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Labor Market Composite"
    return s
