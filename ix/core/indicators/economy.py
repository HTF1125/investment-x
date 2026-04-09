from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series, MultiSeries
from ix.common.data.transforms import StandardScalar


# ══════════════════════════════════════════════════════════════════════════════
# ── Nowcasting ───────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════


# ── GDPNow & Real-Time GDP Tracking ────────────────────────────────────────


def gdpnow() -> pd.Series:
    """Atlanta Fed GDPNow real-time GDP estimate.

    Updated ~weekly. Most accurate real-time GDP tracker available.
    Converges to actual GDP print as quarter progresses.
    """
    s = Series("GDPNOW")
    if s.empty:
        # Fallback: construct GDP proxy from ISM + employment
        s = _gdp_proxy()
    s.name = "GDPNow"
    return s.dropna()


def _gdp_proxy() -> pd.Series:
    """GDP growth proxy from ISM Manufacturing + Nonfarm Payrolls."""
    ism = Series("NAPM")  # ISM Manufacturing PMI
    nfp = Series("PAYEMS")  # Nonfarm Payrolls
    if ism.empty and nfp.empty:
        return pd.Series(dtype=float)
    components = {}
    if not ism.empty:
        components["ISM"] = StandardScalar(ism.dropna(), 120)
    if not nfp.empty:
        nfp_mom = nfp.pct_change(12) * 100
        components["NFP"] = StandardScalar(nfp_mom.dropna(), 120)
    return pd.DataFrame(components).mean(axis=1).dropna()


# ── Weekly Economic Index ───────────────────────────────────────────────────


def weekly_economic_index() -> pd.Series:
    """NY Fed Weekly Economic Index (WEI).

    High-frequency GDP proxy using 10 weekly/daily indicators.
    Scaled to 4-quarter GDP growth units. Updated weekly.
    """
    s = Series("WEI")
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "Weekly Economic Index"
    return s.dropna()


def wei_momentum(window: int = 13) -> pd.Series:
    """WEI momentum: change over ~1 quarter.

    Positive = economic activity accelerating.
    Negative = decelerating.
    """
    wei = weekly_economic_index()
    s = wei.diff(window).dropna()
    s.name = "WEI Momentum"
    return s


# ── ADS Business Conditions ─────────────────────────────────────────────────


def ads_business_conditions() -> pd.Series:
    """Aruoba-Diebold-Scotti Business Conditions Index (daily).

    Mean zero = average growth. Positive = above-trend. Negative = below-trend.
    Based on jobless claims, payrolls, industrial production, real GDP,
    real income, real manufacturing sales.
    """
    s = Series("ADSCI")
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "ADS Business Conditions"
    return s.dropna()


# ── High-Frequency Activity Proxies ─────────────────────────────────────────


def initial_claims(freq: str = "W") -> pd.Series:
    """Initial jobless claims — highest-frequency labor market indicator.

    Rising claims = labor market weakening (leading indicator).
    4-week MA smooths weekly noise.
    """
    s = Series("ICSA", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "Initial Claims"
    return s.dropna()


def initial_claims_4wma() -> pd.Series:
    """4-week moving average of initial claims (smoothed)."""
    s = Series("IC4WSA")
    if s.empty:
        s = initial_claims().rolling(4).mean()
    s.name = "Initial Claims 4WMA"
    return s.dropna()


def continued_claims(freq: str = "W") -> pd.Series:
    """Continued (insured) unemployment claims."""
    s = Series("CCSA", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "Continued Claims"
    return s.dropna()


def claims_ratio() -> pd.Series:
    """Continued / Initial claims ratio — duration of unemployment.

    Rising = unemployed staying jobless longer (structural weakness).
    Falling = quick reabsorption (healthy labor market).
    """
    initial = initial_claims()
    cont = continued_claims()
    df = pd.concat([initial, cont], axis=1).dropna()
    if df.empty or df.shape[1] < 2:
        return pd.Series(dtype=float, name="Claims Ratio")
    s = (df.iloc[:, 1] / df.iloc[:, 0]).dropna()
    s.name = "Claims Ratio"
    return s


# ── Industrial Production ───────────────────────────────────────────────────


def industrial_production_yoy(freq: str = "ME") -> pd.Series:
    """US Industrial Production YoY growth (%).

    Key coincident indicator of manufacturing activity.
    """
    ip = Series("INDPRO", freq=freq)
    if ip.empty:
        return pd.Series(dtype=float)
    s = ip.pct_change(12) * 100
    s.name = "Industrial Production YoY"
    return s.dropna()


def capacity_utilization(freq: str = "ME") -> pd.Series:
    """Capacity Utilization Rate (%).

    Above 80% = inflationary pressure. Below 75% = slack.
    """
    s = Series("TCU", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "Capacity Utilization"
    return s.dropna()


# ── Recession Probability ──────────────────────────────────────────────────


def recession_probability() -> pd.Series:
    """Chauvet-Piger Smoothed US Recession Probabilities (0-100%).

    Dynamic-factor Markov-switching model applied to four coincident
    variables: nonfarm payrolls, industrial production, real personal
    income (ex-transfers), and real manufacturing & trade sales.

    0-5% = expansion.  >50% = recession highly likely.
    Published with ~2-month lag using revised data (smoothed, not
    real-time — avoids noisy false alarms but confirms late).

    Use alongside Sahm Rule (labor_market.sahm_rule) for triangulation:
    Sahm triggers real-time ~3 months in; this confirms with higher
    confidence after revisions.

    Source: Chauvet & Piger, FRED RECPROUSM156N.
    """
    s = Series("RECPROUSM156N")
    if s.empty:
        return pd.Series(dtype=float, name="Recession Probability")
    s.name = "Recession Probability"
    return s.dropna()


def recession_probability_signal(threshold: float = 50.0) -> pd.Series:
    """Binary recession flag from Chauvet-Piger model.

    Returns 1 when smoothed probability >= threshold (default 50%),
    0 otherwise.  At 50% threshold, near-perfect historical accuracy
    since 1967 with no false positives.

    Source: Chauvet & Piger, FRED RECPROUSM156N.
    """
    prob = recession_probability()
    if prob.empty:
        return pd.Series(dtype=float, name="Recession Signal (Chauvet-Piger)")
    s = (prob >= threshold).astype(int)
    s.name = "Recession Signal (Chauvet-Piger)"
    return s.dropna()


# ── Conference Board LEI ───────────────────────────────────────────────────


def conference_board_lei() -> pd.Series:
    """Conference Board Leading Economic Index (2016=100).

    10-component composite: ISM new orders, building permits, stock prices,
    credit index, consumer expectations, weekly hours, initial claims,
    yield spread, capital goods orders, and leading credit index.

    Monthly, ~3-week publication lag.  603 pts from 1975.

    Source: The Conference Board, FactSet US.LEI.
    """
    s = Series("US.LEI")
    if s.empty:
        return pd.Series(dtype=float, name="Conference Board LEI")
    s.name = "Conference Board LEI"
    return s.dropna()


def lei_yoy() -> pd.Series:
    """Conference Board LEI year-over-year change (%).

    YoY below -4% has preceded every recession since 1975.
    More robust than the MoM print (which is noisy).

    Source: Computed from US.LEI.
    """
    lei = Series("US.LEI")
    if lei.empty:
        return pd.Series(dtype=float, name="LEI YoY %")
    s = lei.pct_change(12) * 100
    s.name = "LEI YoY %"
    return s.dropna()


def lei_recession_signal() -> pd.Series:
    """Conference Board '3Ds' recession signal (binary).

    Signals recession when BOTH:
    1. Six-month annualized growth rate of LEI < -4.3%
    2. Six-month diffusion index <= 50

    This dual-threshold approach has near-perfect accuracy since 1975.
    Returns 1 = recession signal, 0 = no signal.

    Source: The Conference Board 3Ds methodology.
    """
    # 6-month annualized growth
    lei = Series("US.LEI")
    diffusion_6m = Series("D6M950")
    if lei.empty or diffusion_6m.empty:
        return pd.Series(dtype=float, name="LEI Recession Signal")

    growth_6m = lei.pct_change(6) * 2 * 100  # annualized 6M change
    df = pd.DataFrame({
        "growth": growth_6m,
        "diffusion": diffusion_6m,
    }).dropna()

    if df.empty:
        return pd.Series(dtype=float, name="LEI Recession Signal")

    s = ((df["growth"] < -4.3) & (df["diffusion"] <= 50)).astype(int)
    s.name = "LEI Recession Signal"
    return s.dropna()


def coincident_lagging_ratio() -> pd.Series:
    """Conference Board Coincident-to-Lagging Index ratio (2004=100).

    One of the oldest and most reliable leading indicators — despite
    being a ratio of TWO lagging series.  The logic: when coincident
    indicators start rising faster than lagging ones, the economy is
    accelerating (and vice versa).

    Sustained declines below the 12-month moving average have preceded
    every recession since 1975.  The ratio typically peaks ~10-14
    months before recession onset.

    Source: The Conference Board (G0M940).
    """
    s = Series("G0M940")
    if s.empty:
        return pd.Series(dtype=float, name="Coincident/Lagging Ratio")
    s.name = "Coincident/Lagging Ratio"
    return s.dropna()


def coincident_lagging_ratio_yoy() -> pd.Series:
    """Coincident-to-Lagging ratio year-over-year change (%).

    Negative YoY = economy decelerating faster than lagging data
    can confirm.  Persistent negative readings (-3% or worse) are
    a recession early-warning.

    Source: Computed from Conference Board G0M940.
    """
    s = Series("G0M940")
    if s.empty:
        return pd.Series(dtype=float, name="Coincident/Lagging YoY %")
    yoy = s.pct_change(12) * 100
    yoy.name = "Coincident/Lagging YoY %"
    return yoy.dropna()


# ── Composite Nowcast ───────────────────────────────────────────────────────


def nowcast_composite(window: int = 120) -> pd.Series:
    """Composite nowcasting index from available high-frequency data.

    Combines all available nowcasting signals into a single z-score.
    Positive = above-trend growth. Negative = below-trend.
    """
    components = {}

    wei = weekly_economic_index()
    if not wei.empty:
        components["WEI"] = StandardScalar(wei, window)

    ads = ads_business_conditions()
    if not ads.empty:
        components["ADS"] = StandardScalar(ads, window)

    claims = initial_claims()
    if not claims.empty:
        # Invert — lower claims = better
        components["Claims"] = -StandardScalar(claims, window)

    ip = Series("INDPRO")
    if not ip.empty:
        ip_yoy = ip.pct_change(12).dropna()
        components["IP"] = StandardScalar(ip_yoy, window)

    if not components:
        return pd.Series(dtype=float, name="Nowcast Composite")

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Nowcast Composite"
    return s


# ── Recession Risk Composite ──────────────────────────────────────────────


def recession_risk_composite(window: int = 120) -> pd.Series:
    """Multi-signal recession risk composite (z-score).

    Aggregates 7 recession-relevant indicators into a single z-scored
    signal.  Higher = more recession risk.  Components:

    1. Sahm Rule (higher = more risk)
    2. Chauvet-Piger Recession Probability (higher = more risk)
    3. STLFSI financial stress (higher = more risk)
    4. SLOOS C&I lending standards (higher = tighter = more risk)
    5. LEI YoY change (INVERTED — lower = more risk)
    6. Coincident/Lagging YoY (INVERTED — lower = more risk)
    7. Initial claims 4WMA (higher = more risk)

    Each component is z-scored over a rolling window before averaging.
    The composite is robust to missing components — works with whatever
    data is available.

    Interpretation:
    - z > +1.5: elevated recession risk
    - z > +2.0: high recession risk (historically = recession underway)
    - z < 0: below-average risk (expansion)

    Source: Composite of FRED/FactSet indicators.
    """
    components = {}

    # Sahm Rule (higher = more risk)
    sahm = Series("SAHMCURRENT")
    if not sahm.empty:
        components["Sahm"] = StandardScalar(sahm.dropna(), window)

    # Chauvet-Piger recession probability (higher = more risk)
    rp = Series("RECPROUSM156N")
    if not rp.empty:
        components["RecProb"] = StandardScalar(rp.dropna(), window)

    # STLFSI financial stress (higher = more stress)
    stl = Series("STLFSI4")
    if not stl.empty:
        components["STLFSI"] = StandardScalar(stl.dropna(), window)

    # SLOOS C&I lending (higher = tighter = more risk)
    sloos = Series("DRTSCILM")
    if not sloos.empty:
        components["SLOOS"] = StandardScalar(sloos.dropna(), window)

    # LEI YoY — INVERTED (lower LEI = more risk)
    lei = Series("US.LEI")
    if not lei.empty:
        lei_yoy_s = lei.pct_change(12).dropna()
        components["LEI"] = -StandardScalar(lei_yoy_s, window)

    # Coincident/Lagging ratio YoY — INVERTED (lower = more risk)
    cl = Series("G0M940")
    if not cl.empty:
        cl_yoy = cl.pct_change(12).dropna()
        components["CL Ratio"] = -StandardScalar(cl_yoy, window)

    # Initial claims (higher = more risk)
    claims = Series("ICSA")
    if not claims.empty:
        components["Claims"] = StandardScalar(claims.dropna(), window)

    if not components:
        return pd.Series(dtype=float, name="Recession Risk Composite")

    raw = pd.DataFrame(components).mean(axis=1).dropna()
    # EMA smooth to reduce mixed-frequency noise (halflife ~4 weeks)
    s = raw.ewm(halflife=20).mean()
    s.name = "Recession Risk Composite"
    return s.dropna()


# ══════════════════════════════════════════════════════════════════════════════
# ── Labor Market ─────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════


# ── JOLTS ──────────────────────────────────────────────────────────────────


def jolts_job_openings(freq: str = "ME") -> pd.Series:
    """JOLTS Job Openings (thousands).

    Demand-side labor signal. Leads wage inflation by 6-12 months.
    Peak openings precede labor market tightening.
    """
    s = Series("JTSJOL", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "JOLTS Job Openings"
    return s.dropna()


def jolts_quits_rate(freq: str = "ME") -> pd.Series:
    """JOLTS Quits Rate (%).

    Worker confidence proxy — high quits = workers confident
    they can find better jobs. Leads wage growth.
    Above 2.5% = tight market. Below 1.5% = weak market.
    """
    s = Series("JTSQUR", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "JOLTS Quits Rate"
    return s.dropna()


def jolts_hires_rate(freq: str = "ME") -> pd.Series:
    """JOLTS Hires Rate (%).

    Employer willingness to hire. Falling hires rate while
    openings stay high = skills mismatch or structural issue.
    """
    s = Series("JTSHIR", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
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
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "Employment Cost Index"
    return s.dropna()


def employment_cost_index_yoy(freq: str = "QE") -> pd.Series:
    """Employment Cost Index — Year-over-Year (%)."""
    eci = Series("ECIALLCIV", freq=freq)
    if eci.empty:
        return pd.Series(dtype=float)
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
    if ulc.empty:
        return pd.Series(dtype=float)
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
    if prod.empty:
        return pd.Series(dtype=float)
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
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "U6 Unemployment"
    return s.dropna()


def temp_employment(freq: str = "ME") -> pd.Series:
    """Temporary Help Services Employment (thousands).

    Classic leading indicator. Temps are hired first into
    recovery and fired first before recession. Leads payrolls
    by 3-6 months.
    """
    s = Series("TEMPHELPS", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "Temp Employment"
    return s.dropna()


def temp_employment_yoy(freq: str = "ME") -> pd.Series:
    """Temp employment YoY change (%). Negative = recession warning."""
    temp = Series("TEMPHELPS", freq=freq)
    if temp.empty:
        return pd.Series(dtype=float)
    s = temp.pct_change(12) * 100
    s.name = "Temp Employment YoY"
    return s.dropna()


# ── Sahm Rule ─────────────────────────────────────────────────────────────


def sahm_rule() -> pd.Series:
    """Sahm Rule Recession Indicator (percentage points).

    The three-month moving average of the U3 unemployment rate minus
    its 12-month trailing low.  When >= 0.50 pp, every post-1950
    recession has already begun (avg trigger ~3 months in).

    Not predictive — it's a real-time *diagnostic* that confirms a
    recession is underway before NBER or GDP data can.

    Limitations:
    - Can produce false positives when labor-force expansion (not
      demand weakness) lifts unemployment.
    - Claudia Sahm herself warned about structural distortions in
      the post-COVID economy.

    Source: Claudia Sahm (2019), FRED SAHMCURRENT.
    """
    s = Series("SAHMCURRENT")
    if s.empty:
        return pd.Series(dtype=float, name="Sahm Rule")
    s.name = "Sahm Rule"
    return s.dropna()


def sahm_rule_signal(threshold: float = 0.50) -> pd.Series:
    """Binary recession signal from the Sahm Rule.

    Returns 1 when the Sahm indicator >= threshold (default 0.50 pp),
    0 otherwise.  Historical hit rate: 11/11 recessions since 1950.

    Source: Claudia Sahm (2019), FRED SAHMCURRENT.
    """
    sahm = sahm_rule()
    if sahm.empty:
        return pd.Series(dtype=float, name="Sahm Signal")
    s = (sahm >= threshold).astype(int)
    s.name = "Sahm Signal"
    return s.dropna()


# ── Labor Market Composite ────────────────────────────────────────────────


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


# ══════════════════════════════════════════════════════════════════════════════
# ── Consumer ─────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════


# ── Consumer Sentiment ─────────────────────────────────────────────────────


def michigan_sentiment(freq: str = "ME") -> pd.Series:
    """University of Michigan Consumer Sentiment Index.

    Expectations component leads consumer spending by 2-3 quarters.
    Below 60 = recession-level pessimism. Above 90 = strong confidence.
    """
    s = Series("UMCSENT", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
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
    if sent.empty:
        return pd.Series(dtype=float)
    s = sent.diff(window).dropna()
    s.name = "Sentiment Momentum"
    return s


def conference_board_confidence(freq: str = "ME") -> pd.Series:
    """Conference Board Consumer Confidence Index.

    Present Situation component is best coincident indicator.
    Expectations component leads by 6-9 months.
    """
    s = Series("CSCICP03USM665S", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
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
    if s.empty:
        return pd.Series(dtype=float)
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
    if s.empty:
        return pd.Series(dtype=float)
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


# ── Consumer Health Composite ─────────────────────────────────────────────


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


# ── Business Confidence ──────────────────────────────────────────────────────


def business_confidence_us() -> pd.Series:
    """OECD Business Confidence Indicator for the United States.

    Amplitude-adjusted, centered on 100. Based on manufacturing/industrial
    surveys. Above 100 = above long-term average confidence. Below 100 =
    below average. Leads GDP turning points by 2-4 quarters.

    Used as a proxy for CEO confidence (Conference Board CEO Confidence
    index is not available via FRED). Closely correlated with ISM
    Manufacturing PMI direction.

    Source: OECD Business Confidence Index (USA.BSCICP03.IXNSA)
    """
    s = Series("USA.BSCICP03.IXNSA:PX_LAST")
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "US Business Confidence (OECD)"
    return s.dropna()


# ── NAAIM Exposure Index ───────────────────────────────────────────────────


def naaim_exposure() -> pd.Series:
    """NAAIM Exposure Index: active manager equity exposure (0-200%).

    Contrarian signal — extremes tend to reverse.
    > 100 = leveraged long. < 0 = net short.
    Source: naaim.org (collected via NAAIMExposureCollector).
    """
    s = Series("NAAIM_EXPOSURE")
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "NAAIM Exposure Index"
    return s.dropna()


def naaim_exposure_zscore(window: int = 78) -> pd.Series:
    """Z-scored NAAIM Exposure for extreme detection.

    |z| > 1.5 flags contrarian opportunities.
    Source: Derived from NAAIM Exposure Index.
    """
    exp = naaim_exposure()
    if exp.empty:
        return pd.Series(dtype=float)
    z = StandardScalar(exp, window)
    z.name = "NAAIM Exposure Z-Score"
    return z.dropna()


# ── Big Four Recession Indicators ──────────────────────────────────────────


def _percent_off_peak(s: pd.Series) -> pd.Series:
    """Compute percent-off-peak (expanding max) for a monthly series.

    Zeros and negative values are treated as missing to avoid
    spurious -100% readings from data errors.
    """
    s = s.where(s > 0)
    peak = s.expanding().max()
    return ((s / peak) - 1) * 100


def big_four_nonfarm() -> pd.Series:
    """Nonfarm payrolls — percent off all-time peak.

    Source: BLS via FRED (PAYEMS). Monthly, ~1 week lag.
    One of the NBER's four key coincident indicators.
    """
    s = Series("PAYEMS", freq="ME")
    if s.empty:
        return pd.Series(dtype=float, name="NFP % Off Peak")
    result = _percent_off_peak(s.dropna())
    result.name = "NFP % Off Peak"
    return result.dropna()


def big_four_industrial_production() -> pd.Series:
    """Industrial production index — percent off all-time peak.

    Source: Federal Reserve via FRED (INDPRO). Monthly, ~2 week lag.
    One of the NBER's four key coincident indicators.
    """
    s = Series("INDPRO", freq="ME")
    if s.empty:
        return pd.Series(dtype=float, name="IP % Off Peak")
    result = _percent_off_peak(s.dropna())
    result.name = "IP % Off Peak"
    return result.dropna()


def big_four_real_income() -> pd.Series:
    """Real personal income excluding transfers — percent off all-time peak.

    Source: BEA via FRED (BEANIPAW875RX1@US). Monthly, ~3 week lag.
    One of the NBER's four key coincident indicators.
    """
    s = Series("BEANIPAW875RX1@US", freq="ME")
    if s.empty:
        s = Series("W875RX1A020NBEA", freq="ME")
    if s.empty:
        return pd.Series(dtype=float, name="Real Income ex Transfers % Off Peak")
    result = _percent_off_peak(s.dropna())
    result.name = "Real Income ex Transfers % Off Peak"
    return result.dropna()


def big_four_real_sales() -> pd.Series:
    """Real retail & food services sales — percent off all-time peak.

    Source: Census/StL Fed via FRED (USSA0590478). Monthly, ~2 week lag.
    Proxy for real manufacturing & trade sales (CMRMTSPL), which is
    discontinued on FRED — retail sales is the most-watched substitute.
    """
    s = Series("USSA0590478", freq="ME")
    if s.empty:
        return pd.Series(dtype=float, name="Real Sales % Off Peak")
    result = _percent_off_peak(s.dropna())
    result.name = "Real Sales % Off Peak"
    return result.dropna()


def big_four_composite() -> pd.DataFrame:
    """NBER Big Four recession indicators — all four percent-off-peak series.

    Returns a DataFrame with columns for each indicator plus the average.
    When the average drops significantly below zero, the economy is likely
    in recession. In all post-1960 recessions, the composite dropped
    below -1% before the NBER officially dated the recession start.

    Source: Advisor Perspectives / Doug Short methodology.
    Components: Nonfarm Payrolls, Industrial Production,
    Real Personal Income ex Transfers, Real Retail Sales.
    """
    components = {}

    nfp = big_four_nonfarm()
    if not nfp.empty:
        components["NFP"] = nfp

    ip = big_four_industrial_production()
    if not ip.empty:
        components["Industrial Prod"] = ip

    inc = big_four_real_income()
    if not inc.empty:
        components["Real Income"] = inc

    sales = big_four_real_sales()
    if not sales.empty:
        components["Real Sales"] = sales

    if not components:
        return pd.DataFrame()

    df = pd.DataFrame(components)
    df["Big Four Avg"] = df.mean(axis=1)
    return df.dropna(how="all")


def big_four_average() -> pd.Series:
    """Average of the Big Four recession indicators (percent off peak).

    Single series version of big_four_composite() for use in composites
    and chart expressions. Values near zero = expansion, deeply negative
    = recession. Historical threshold: < -1% strongly signals recession.

    Source: NBER coincident indicators via Advisor Perspectives methodology.
    """
    df = big_four_composite()
    if df.empty or "Big Four Avg" not in df.columns:
        return pd.Series(dtype=float, name="Big Four Avg % Off Peak")
    result = df["Big Four Avg"].dropna()
    result.name = "Big Four Avg % Off Peak"
    return result
