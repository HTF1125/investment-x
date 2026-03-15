from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series, MultiSeries
from ix.core.transforms import StandardScalar


# ── Consumer Sentiment ─────────────────────────────────────────────────────


def michigan_sentiment(freq: str = "ME") -> pd.Series:
    """University of Michigan Consumer Sentiment Index.

    Expectations component leads consumer spending by 2-3 quarters.
    Below 60 = recession-level pessimism. Above 90 = strong confidence.
    """
    s = Series("UMCSENT", freq=freq)
    s.name = "Michigan Sentiment"
    return s.dropna()


def michigan_expectations(freq: str = "ME") -> pd.Series:
    """Michigan Consumer Expectations sub-index.

    More forward-looking than headline. Leads spending and
    is a component of the Leading Economic Index (LEI).
    """
    s = Series("MICH", freq=freq)
    if s.empty:
        s = Series("UMCSENT", freq=freq)  # Fallback to headline
    s.name = "Michigan Expectations"
    return s.dropna()


def michigan_sentiment_momentum(window: int = 3) -> pd.Series:
    """Michigan Sentiment month-over-month change.

    Rapid deterioration (> -10 in 3 months) is a recession warning.
    """
    sent = Series("UMCSENT")
    s = sent.diff(window).dropna()
    s.name = "Sentiment Momentum"
    return s


def conference_board_confidence(freq: str = "ME") -> pd.Series:
    """Conference Board Consumer Confidence Index.

    Present Situation component is best coincident indicator.
    Expectations component leads by 6-9 months.
    """
    s = Series("CSCICP03USM665S", freq=freq)
    s.name = "Consumer Confidence"
    return s.dropna()


def consumer_expectations_spread() -> pd.Series:
    """Spread between present situation and expectations.

    When present situation >> expectations = late cycle / topping.
    When expectations >> present situation = early recovery.
    Wide negative spread is a classic recession precursor.
    """
    present = Series("CSCICP03USM665S")
    expectations = Series("UMCSENT")
    if present.empty or expectations.empty:
        return pd.Series(dtype=float, name="Consumer Expectations Spread")
    # Z-score both to make comparable
    z_present = StandardScalar(present.dropna(), 120)
    z_expect = StandardScalar(expectations.dropna(), 120)
    s = (z_expect - z_present).dropna()
    s.name = "Consumer Expectations Spread"
    return s


# ── Consumer Spending ──────────────────────────────────────────────────────


def retail_sales_yoy(freq: str = "ME") -> pd.Series:
    """Retail Sales ex-Food Services YoY (%).

    Core consumer demand signal. Ex-food services removes
    volatile restaurant spending.
    """
    rs = Series("RSXFS", freq=freq)
    if rs.empty:
        rs = Series("RSAFS", freq=freq)  # Total retail sales fallback
    s = rs.pct_change(12) * 100
    s.name = "Retail Sales YoY"
    return s.dropna()


def real_personal_income_ex_transfers(freq: str = "ME") -> pd.Series:
    """Real Disposable Personal Income excluding Transfers YoY (%).

    Organic income growth stripped of government support.
    Sahm Rule adjacent — when this goes negative, recession is likely.
    """
    rpi = Series("W875RX1A020NBEA", freq=freq)
    if rpi.empty:
        rpi = Series("DSPIC96", freq=freq)  # Real disposable income fallback
    s = rpi.pct_change(12) * 100
    s.name = "Real Income ex-Transfers YoY"
    return s.dropna()


def personal_savings_rate(freq: str = "ME") -> pd.Series:
    """Personal Savings Rate (%).

    Spending sustainability gauge. Below 3% = consumers
    depleting savings (unsustainable). Above 10% = pent-up demand.
    """
    s = Series("PSAVERT", freq=freq)
    s.name = "Personal Savings Rate"
    return s.dropna()


# ── Consumer Credit Health ─────────────────────────────────────────────────


def consumer_delinquency_rate(freq: str = "QE") -> pd.Series:
    """Consumer Loan Delinquency Rate — 90+ days (%).

    Credit cycle turning point signal. Starts rising 2-4 quarters
    before recession. Watch for inflection from trough.
    """
    s = Series("DRCCLACBS", freq=freq)
    if s.empty:
        s = Series("DRCLACBS", freq=freq)  # Alternative code
    s.name = "Consumer Delinquency Rate"
    return s.dropna()


def household_debt_service_ratio(freq: str = "QE") -> pd.Series:
    """Household Debt Service Ratio (% of disposable income).

    Consumer stress indicator. Above 13% = historically stressed.
    Below 10% = ample capacity for spending.
    """
    s = Series("TDSP", freq=freq)
    s.name = "Household Debt Service"
    return s.dropna()


def consumer_credit_delinquency_momentum() -> pd.Series:
    """Change in delinquency rate (pp) — acceleration of consumer stress.

    Rising rate of change = deterioration accelerating.
    """
    dq = Series("DRCCLACBS")
    if dq.empty:
        dq = Series("DRCLACBS")
    s = dq.diff(4).dropna()  # QoQ change in delinquency rate
    s.name = "Delinquency Momentum"
    return s


# ── Composite ──────────────────────────────────────────────────────────────


def consumer_health_composite(window: int = 120) -> pd.Series:
    """Consumer health composite index.

    Combines sentiment, spending, income, and credit health
    into a single z-scored signal.
    Positive = healthy consumer. Negative = consumer stress.
    """
    components = {}

    sent = Series("UMCSENT")
    if not sent.empty:
        components["Sentiment"] = StandardScalar(sent.dropna(), window)

    rs = Series("RSXFS")
    if rs.empty:
        rs = Series("RSAFS")
    if not rs.empty:
        rs_yoy = rs.pct_change(12).dropna()
        components["Spending"] = StandardScalar(rs_yoy, window)

    savings = Series("PSAVERT")
    if not savings.empty:
        components["Savings"] = StandardScalar(savings.dropna(), window)

    dq = Series("DRCCLACBS")
    if dq.empty:
        dq = Series("DRCLACBS")
    if not dq.empty:
        # Inverted — lower delinquency = healthier
        components["Credit"] = -StandardScalar(dq.dropna(), window)

    if not components:
        return pd.Series(dtype=float, name="Consumer Health Composite")

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Consumer Health Composite"
    return s
