"""
Liquidity Factor Indicator Research
====================================
Streamlit app to discover which macro indicators best predict/explain
the liquidity factor.  Tests indicators from every macro category
(central bank, credit, monetary policy, flows, sentiment, etc.)
against multiple liquidity proxies using IC analysis, lead-lag
correlation, regression, and Granger causality.

Run with:  streamlit run liquidity_indicator_research.py
"""

from __future__ import annotations

import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats as sp_stats
import streamlit as st

warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------------------
# Must be first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Liquidity Factor Research",
    page_icon="$",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Load .env for database connection
# ---------------------------------------------------------------------------
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Theming
# ---------------------------------------------------------------------------
CARD_BG = "#161b22"
ACCENT = "#58a6ff"
GREEN = "#3fb950"
RED = "#f85149"
YELLOW = "#d29922"
MUTED = "#8b949e"

PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", size=12, color="#c9d1d9"),
    margin=dict(l=50, r=30, t=50, b=40),
    legend=dict(
        bgcolor="rgba(22,27,34,0.8)",
        bordercolor="rgba(48,54,61,0.6)",
        borderwidth=1,
    ),
    xaxis=dict(gridcolor="rgba(48,54,61,0.4)", zerolinecolor="rgba(48,54,61,0.6)"),
    yaxis=dict(gridcolor="rgba(48,54,61,0.4)", zerolinecolor="rgba(48,54,61,0.6)"),
)

st.markdown(
    """
    <style>
    .block-container {padding-top:1.5rem; padding-bottom:1rem;}
    .stTabs [data-baseweb="tab-list"] {gap:0;}
    .stTabs [data-baseweb="tab"] {padding:8px 20px; font-weight:500;}
    div[data-testid="stMetric"] {background:#161b22; border:1px solid #30363d;
        border-radius:8px; padding:12px 16px;}
    div[data-testid="stMetric"] label {color:#8b949e; font-size:0.78rem;}
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color:#c9d1d9; font-size:1.35rem; font-weight:600;}
    </style>
    """,
    unsafe_allow_html=True,
)


def _apply_layout(fig: go.Figure, title: str = "", subtitle: str = "", height: int = 450):
    """Apply dark-theme layout to a Plotly figure."""
    title_text = f"<b>{title}</b>"
    if subtitle:
        title_text += f"<br><span style='font-size:11px;color:{MUTED}'>{subtitle}</span>"
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text=title_text, x=0.02, y=0.97, font_size=14),
        height=height,
    )
    return fig


# ===========================================================================
# DATA LOADING
# ===========================================================================

# Indicator registry: (display_name, callable, category, description, invert)
# "invert" means the raw series is negatively related to liquidity
# (e.g. higher real yields = tighter liquidity, so invert=True)

def _build_indicator_registry() -> list[tuple[str, Callable, str, str, bool]]:
    """Build the full list of candidate indicators to test against the
    liquidity factor.  Organized by economic category."""

    from ix.db.custom import (
        # Core liquidity
        fed_net_liquidity,
        tga_drawdown,
        treasury_net_issuance,
        m2_world_total_yoy,
        credit_impulse,
        global_liquidity_yoy,
        fci_us,
        fci_stress,
        # Rates & curves
        us_2s10s,
        us_3m10y,
        us_10y_real,
        us_10y_breakeven,
        hy_spread,
        ig_spread,
        hy_ig_ratio,
        risk_appetite,
        # Monetary policy
        rate_cut_expectations,
        rate_expectations_momentum,
        term_premium_proxy,
        policy_rate_level,
        # Central bank
        fed_total_assets,
        fed_assets_yoy,
        fed_assets_momentum,
        g4_balance_sheet_yoy,
        central_bank_liquidity_composite,
        rate_cut_probability_proxy,
        # Credit deep
        credit_stress_index,
        hy_spread_momentum,
        hy_spread_velocity,
        credit_cycle_phase,
        ig_hy_compression,
        financial_conditions_credit,
        # Fund flows / leverage
        margin_debt_yoy,
        bank_credit_impulse,
        consumer_credit_growth,
        equity_bond_flow_ratio,
        risk_rotation_index,
        # Volatility
        vix,
        vix_term_spread,
        vol_risk_premium,
        # Cross-asset
        dollar_index,
        copper_gold_ratio,
        commodities_crb,
        # Sentiment / positioning
        put_call_zscore,
        risk_on_off_breadth,
        cesi_breadth,
        # Intermarket
        small_large_cap_ratio,
        cyclical_defensive_ratio,
        credit_equity_divergence,
        # Growth proxies
        ism_new_orders,
        ism_new_orders_minus_inventories,
    )

    return [
        # -- Central Bank / Balance Sheet --
        ("Fed Net Liquidity", fed_net_liquidity, "Central Bank",
         "Fed assets minus TGA minus RRP. Core US liquidity measure.", False),
        ("Fed Assets YoY", fed_assets_yoy, "Central Bank",
         "Fed total assets year-over-year change. QE/QT cycle.", False),
        ("Fed BS Momentum", fed_assets_momentum, "Central Bank",
         "13-week change in Fed balance sheet ($T).", False),
        ("G4 BS YoY", g4_balance_sheet_yoy, "Central Bank",
         "Combined Fed+ECB+BOJ balance sheet YoY change.", False),
        ("CB Liquidity Composite", central_bank_liquidity_composite, "Central Bank",
         "Z-score composite of Fed momentum, G4 YoY, net liquidity, rate cuts.", False),

        # -- Fiscal / Treasury --
        ("TGA Drawdown", tga_drawdown, "Fiscal",
         "13-week TGA balance change. Drawdown injects liquidity.", True),
        ("Treasury Net Issuance", treasury_net_issuance, "Fiscal",
         "Net Treasury supply pressure. Rising = drains liquidity.", True),

        # -- Money Supply --
        ("Global M2 YoY", m2_world_total_yoy, "Money Supply",
         "Global M2 money supply year-over-year growth.", False),
        ("Global Liquidity YoY", global_liquidity_yoy, "Money Supply",
         "Central bank liquidity proxy YoY.", False),
        ("Credit Impulse", credit_impulse, "Money Supply",
         "2nd derivative of bank credit. Leads GDP by 6-9 months.", False),

        # -- Financial Conditions --
        ("FCI US", fci_us, "Financial Conditions",
         "US Financial Conditions Index. Negative = tight.", False),
        ("FCI Stress", fci_stress, "Financial Conditions",
         "Financial stress index (VIX + MOVE + spreads).", True),
        ("Credit Conditions", financial_conditions_credit, "Financial Conditions",
         "Credit component of financial conditions.", False),

        # -- Monetary Policy --
        ("Rate Cut Expectations", rate_cut_expectations, "Monetary Policy",
         "Expected rate change over 12 months (bps). Positive = cuts.", False),
        ("Rate Expect Momentum", rate_expectations_momentum, "Monetary Policy",
         "Velocity of repricing in rate expectations.", False),
        ("Term Premium", term_premium_proxy, "Monetary Policy",
         "10Y yield minus implied 12M policy rate.", True),
        ("Policy Rate Level", policy_rate_level, "Monetary Policy",
         "Implied current Fed Funds rate. Higher = tighter.", True),
        ("Rate Cut Probability", rate_cut_probability_proxy, "Monetary Policy",
         "2Y yield vs Fed Funds gap. Positive = pricing cuts.", False),

        # -- Yield Curve --
        ("US 2s10s", us_2s10s, "Yield Curve",
         "10Y minus 2Y spread. Steep = accommodative expectations.", False),
        ("US 3m10y", us_3m10y, "Yield Curve",
         "10Y minus 3M spread. Classic recession predictor.", False),
        ("US 10Y Real", us_10y_real, "Yield Curve",
         "10Y TIPS real yield. Higher = tighter real conditions.", True),
        ("US 10Y Breakeven", us_10y_breakeven, "Yield Curve",
         "Market inflation expectations. Rising = reflationary.", False),

        # -- Credit Spreads --
        ("HY Spread", hy_spread, "Credit Spreads",
         "ICE BofA HY OAS. Wider = tighter liquidity.", True),
        ("IG Spread", ig_spread, "Credit Spreads",
         "ICE BofA IG OAS. Wider = tighter liquidity.", True),
        ("HY/IG Ratio", hy_ig_ratio, "Credit Spreads",
         "HY/IG spread ratio. Rising = credit stress.", True),
        ("Credit Stress Index", credit_stress_index, "Credit Spreads",
         "Composite stress from spreads, VIX, curve.", True),
        ("HY Spread Momentum", hy_spread_momentum, "Credit Spreads",
         "60-day HY spread change. Positive = widening.", True),
        ("HY Spread Velocity", hy_spread_velocity, "Credit Spreads",
         "Rate of change of HY spread movement.", True),
        ("Credit Cycle Phase", credit_cycle_phase, "Credit Spreads",
         "Spread level + momentum composite.", False),
        ("IG/HY Compression", ig_hy_compression, "Credit Spreads",
         "IG/HY ratio. Rising = risk appetite, tightening.", False),

        # -- Risk Appetite --
        ("Risk Appetite", risk_appetite, "Risk Appetite",
         "Inverted z-score of vol + spreads. Higher = more appetite.", False),

        # -- Leverage / Flows --
        ("Margin Debt YoY", margin_debt_yoy, "Leverage & Flows",
         "Leverage growth. >30% = frothy. <-20% = deleveraging.", False),
        ("Bank Credit Impulse", bank_credit_impulse, "Leverage & Flows",
         "Acceleration of total bank credit growth.", False),
        ("Consumer Credit YoY", consumer_credit_growth, "Leverage & Flows",
         "Consumer credit outstanding YoY growth.", False),
        ("Equity/Bond Flow", equity_bond_flow_ratio, "Leverage & Flows",
         "SPY/TLT momentum as equity-bond rotation proxy.", False),
        ("Risk Rotation", risk_rotation_index, "Leverage & Flows",
         "Composite risk rotation from equity, credit, size.", False),

        # -- Volatility --
        ("VIX", lambda: vix(freq="D"), "Volatility",
         "CBOE VIX. High vol = tight liquidity environment.", True),
        ("VIX Term Spread", vix_term_spread, "Volatility",
         "VIX3M minus VIX. Negative = backwardation (stress).", False),
        ("Vol Risk Premium", vol_risk_premium, "Volatility",
         "VIX / Realized Vol. High = fear premium.", True),

        # -- Cross-Asset --
        ("Dollar Index", lambda: dollar_index(freq="D"), "Cross-Asset",
         "DXY. Strong dollar = tight global liquidity.", True),
        ("Copper/Gold", lambda: copper_gold_ratio(freq="D"), "Cross-Asset",
         "Growth/risk proxy. Rising = risk-on.", False),
        ("CRB Commodities", lambda: commodities_crb(freq="D"), "Cross-Asset",
         "Broad commodity index. Reflects global demand.", False),

        # -- Sentiment --
        ("Put/Call Z-Score", put_call_zscore, "Sentiment",
         "Equity put/call ratio z-score.", False),
        ("Risk On/Off Breadth", risk_on_off_breadth, "Sentiment",
         "% of cross-asset signals in risk-on.", False),
        ("CESI Breadth", cesi_breadth, "Sentiment",
         "% of regions with positive Citi surprise.", False),

        # -- Intermarket --
        ("Small/Large Cap", lambda: small_large_cap_ratio(freq="D"), "Intermarket",
         "Russell 2000 / SPX. Small caps need liquidity.", False),
        ("Cyclical/Defensive", lambda: cyclical_defensive_ratio(freq="D"), "Intermarket",
         "SPY/XLP sector ratio. Cyclicals need liquidity.", False),
        ("Credit-Equity Div", credit_equity_divergence, "Intermarket",
         "SPX vs HY divergence. Negative = credit leading.", True),

        # -- Growth Proxies --
        ("ISM New Orders", ism_new_orders, "Growth",
         "ISM Mfg New Orders. Leading indicator.", False),
        ("ISM NO-Inv Spread", ism_new_orders_minus_inventories, "Growth",
         "New Orders minus Inventories. Demand vs supply.", False),
    ]


@st.cache_data(ttl=7200, show_spinner="Loading indicator data...")
def load_all_indicators() -> dict[str, pd.Series]:
    """Load all candidate indicator series in parallel."""
    registry = _build_indicator_registry()
    results = {}

    def _load(name: str, fn: Callable):
        try:
            s = fn()
            if isinstance(s, pd.DataFrame):
                if s.shape[1] == 1:
                    s = s.iloc[:, 0]
                else:
                    return name, None
            if s is not None and not s.empty and len(s.dropna()) > 50:
                s = s.dropna()
                s.name = name
                return name, s
        except Exception:
            pass
        return name, None

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {
            pool.submit(_load, name, fn): name
            for name, fn, _cat, _desc, _inv in registry
        }
        for future in as_completed(futures):
            name, series = future.result()
            if series is not None:
                results[name] = series

    return results


def get_indicator_metadata() -> dict[str, dict]:
    """Return metadata for each indicator."""
    registry = _build_indicator_registry()
    return {
        name: {"category": cat, "description": desc, "invert": inv}
        for name, _fn, cat, desc, inv in registry
    }


# ===========================================================================
# LIQUIDITY FACTOR DEFINITIONS
# ===========================================================================

LIQUIDITY_FACTOR_DEFINITIONS = {
    "HY OAS (inverted)": {
        "description": (
            "ICE BofA US High Yield OAS (inverted). The single most-watched "
            "market-based liquidity proxy. Tight spreads = ample liquidity. "
            "We invert so positive = loose liquidity."
        ),
        "loader": "hy_spread",
        "invert": True,
    },
    "FCI US": {
        "description": (
            "US Financial Conditions Index composite. Incorporates DXY, yields, "
            "equities, mortgage rates, IG spreads, oil. Positive = easy conditions."
        ),
        "loader": "fci_us",
        "invert": False,
    },
    "Fed Net Liquidity": {
        "description": (
            "Fed balance sheet net of TGA and reverse repo. "
            "The plumbing measure of dollar liquidity available to markets."
        ),
        "loader": "fed_net_liquidity",
        "invert": False,
    },
    "CB Liquidity Composite": {
        "description": (
            "Z-score composite of Fed momentum, G4 balance sheet YoY, "
            "net liquidity change, and rate cut expectations."
        ),
        "loader": "central_bank_liquidity_composite",
        "invert": False,
    },
    "Credit Conditions": {
        "description": (
            "Credit component of financial conditions from BBB spread, "
            "HY spread, and bank credit growth. Negative = tight."
        ),
        "loader": "financial_conditions_credit",
        "invert": False,
    },
}


@st.cache_data(ttl=7200, show_spinner="Loading liquidity factors...")
def load_liquidity_factors() -> dict[str, pd.Series]:
    """Load all liquidity factor target series."""
    from ix.db.custom import (
        hy_spread,
        fci_us,
        fed_net_liquidity,
        central_bank_liquidity_composite,
        financial_conditions_credit,
    )

    loaders = {
        "HY OAS (inverted)": (hy_spread, True),
        "FCI US": (fci_us, False),
        "Fed Net Liquidity": (fed_net_liquidity, False),
        "CB Liquidity Composite": (central_bank_liquidity_composite, False),
        "Credit Conditions": (financial_conditions_credit, False),
    }

    results = {}
    for name, (fn, invert) in loaders.items():
        try:
            s = fn()
            if s is not None and not s.empty:
                s = s.dropna()
                if invert:
                    s = -s
                s.name = name
                results[name] = s
        except Exception:
            pass

    return results


# ===========================================================================
# ANALYSIS FUNCTIONS
# ===========================================================================

def zscore_rolling(s: pd.Series, window: int = 252) -> pd.Series:
    """Rolling z-score using mean and std."""
    mu = s.rolling(window, min_periods=max(window // 2, 30)).mean()
    sigma = s.rolling(window, min_periods=max(window // 2, 30)).std()
    z = (s - mu) / sigma.replace(0, np.nan)
    return z.replace([np.inf, -np.inf], np.nan).dropna()


def compute_ic(
    indicator: pd.Series,
    target: pd.Series,
    method: str = "spearman",
) -> float:
    """Full-sample rank information coefficient."""
    df = pd.concat([indicator, target], axis=1).dropna()
    if len(df) < 30:
        return np.nan
    if method == "spearman":
        corr, _ = sp_stats.spearmanr(df.iloc[:, 0], df.iloc[:, 1])
    else:
        corr, _ = sp_stats.pearsonr(df.iloc[:, 0], df.iloc[:, 1])
    return corr


def compute_rolling_ic(
    indicator: pd.Series,
    target: pd.Series,
    window: int = 104,
    method: str = "spearman",
) -> pd.Series:
    """Rolling rank IC over a window."""
    df = pd.concat(
        [indicator.rename("ind"), target.rename("tgt")], axis=1
    ).dropna()
    if len(df) < window:
        return pd.Series(dtype=float)

    rolling_ic = []
    for i in range(window, len(df)):
        chunk = df.iloc[i - window : i]
        if method == "spearman":
            c, _ = sp_stats.spearmanr(chunk["ind"], chunk["tgt"])
        else:
            c, _ = sp_stats.pearsonr(chunk["ind"], chunk["tgt"])
        rolling_ic.append((df.index[i], c))

    if not rolling_ic:
        return pd.Series(dtype=float)
    return pd.Series(
        dict(rolling_ic), name=f"IC ({indicator.name})"
    )


def compute_lagged_correlations(
    indicator: pd.Series,
    target: pd.Series,
    max_lag: int = 52,
    step: int = 1,
    method: str = "spearman",
) -> pd.Series:
    """Compute correlation at various lags.
    Positive lag = indicator leads target by N periods.
    """
    results = {}
    for lag in range(-max_lag, max_lag + 1, step):
        shifted = indicator.shift(lag) if lag >= 0 else target.shift(-lag)
        ref = target if lag >= 0 else indicator
        df = pd.concat([shifted, ref], axis=1).dropna()
        if len(df) < 50:
            continue
        if method == "spearman":
            c, _ = sp_stats.spearmanr(df.iloc[:, 0], df.iloc[:, 1])
        else:
            c, _ = sp_stats.pearsonr(df.iloc[:, 0], df.iloc[:, 1])
        results[lag] = c
    return pd.Series(results, name=indicator.name)


def compute_quintile_analysis(
    indicator: pd.Series,
    target: pd.Series,
    n_quantiles: int = 5,
) -> pd.DataFrame:
    """Quintile sort: mean target value by indicator quintile."""
    df = pd.concat(
        [indicator.rename("ind"), target.rename("tgt")], axis=1
    ).dropna()
    if len(df) < n_quantiles * 10:
        return pd.DataFrame()

    try:
        df["q"] = pd.qcut(df["ind"], n_quantiles, labels=False, duplicates="drop")
    except ValueError:
        return pd.DataFrame()

    stats = df.groupby("q")["tgt"].agg(["mean", "median", "std", "count"])
    stats.index = [f"Q{i+1}" for i in range(len(stats))]
    stats.index.name = "Quintile"
    return stats


def granger_causality_test(
    indicator: pd.Series,
    target: pd.Series,
    max_lag: int = 12,
) -> dict:
    """Granger causality: does indicator Granger-cause target?
    Returns dict with best lag and its p-value."""
    try:
        from statsmodels.tsa.stattools import grangercausalitytests
    except ImportError:
        return {"best_lag": np.nan, "p_value": np.nan}

    df = pd.concat(
        [target.rename("target"), indicator.rename("indicator")], axis=1
    ).dropna()
    if len(df) < max_lag * 3 + 10:
        return {"best_lag": np.nan, "p_value": np.nan}

    # Difference to achieve stationarity
    df_diff = df.diff().dropna()

    try:
        results = grangercausalitytests(df_diff[["target", "indicator"]], maxlag=max_lag, verbose=False)
        best_lag = 1
        best_p = 1.0
        for lag, res in results.items():
            p = res[0]["ssr_ftest"][1]
            if p < best_p:
                best_p = p
                best_lag = lag
        return {"best_lag": best_lag, "p_value": best_p}
    except Exception:
        return {"best_lag": np.nan, "p_value": np.nan}


def univariate_regression(
    indicator: pd.Series,
    target: pd.Series,
) -> dict:
    """OLS regression: target ~ indicator. Returns R-squared, beta, t-stat, p-value."""
    df = pd.concat(
        [indicator.rename("x"), target.rename("y")], axis=1
    ).dropna()
    if len(df) < 30:
        return {"r_squared": np.nan, "beta": np.nan, "t_stat": np.nan, "p_value": np.nan}

    x = df["x"].values
    y = df["y"].values
    slope, intercept, r_value, p_value, std_err = sp_stats.linregress(x, y)
    t_stat = slope / std_err if std_err > 0 else 0

    return {
        "r_squared": r_value ** 2,
        "beta": slope,
        "t_stat": t_stat,
        "p_value": p_value,
    }


# ===========================================================================
# MAIN ANALYSIS PIPELINE
# ===========================================================================

@st.cache_data(ttl=3600, show_spinner="Running full analysis pipeline...")
def run_analysis_pipeline(
    factor_name: str,
    _factor_series: pd.Series,
    _indicators: dict[str, pd.Series],
    _metadata: dict[str, dict],
    zscore_window: int,
    ic_window: int,
    max_lag: int,
    resample_freq: str,
) -> dict:
    """Run the complete analysis pipeline for all indicators against
    a single liquidity factor.

    Returns a dict with all results for rendering.
    """
    # Z-score the factor and indicators for comparability
    factor_z = zscore_rolling(_factor_series, zscore_window)
    if resample_freq != "D":
        factor_z = factor_z.resample(resample_freq).last().dropna()

    results_rows = []
    rolling_ics = {}
    lag_profiles = {}
    quintile_results = {}

    for name, raw in _indicators.items():
        if name == factor_name:
            continue

        meta = _metadata.get(name, {})
        invert_for_liquidity = meta.get("invert", False)

        # Z-score the indicator
        ind_z = zscore_rolling(raw, zscore_window)
        if resample_freq != "D":
            ind_z = ind_z.resample(resample_freq).last().dropna()

        if invert_for_liquidity:
            ind_z = -ind_z

        # --- Full-sample IC ---
        ic_spearman = compute_ic(ind_z, factor_z, method="spearman")
        ic_pearson = compute_ic(ind_z, factor_z, method="pearson")

        # --- Rolling IC ---
        ric = compute_rolling_ic(ind_z, factor_z, window=ic_window)
        if not ric.empty:
            rolling_ics[name] = ric

        # --- Lag profile ---
        lag_step = max(1, max_lag // 26)
        lag_prof = compute_lagged_correlations(
            ind_z, factor_z, max_lag=max_lag, step=lag_step
        )
        if not lag_prof.empty:
            lag_profiles[name] = lag_prof

        # --- Quintile analysis ---
        qr = compute_quintile_analysis(ind_z, factor_z, n_quantiles=5)
        if not qr.empty:
            quintile_results[name] = qr

        # --- Granger causality ---
        gc = granger_causality_test(ind_z, factor_z, max_lag=min(12, max_lag))

        # --- Regression ---
        reg = univariate_regression(ind_z, factor_z)

        # Compute overlap and date range
        overlap = pd.concat([ind_z, factor_z], axis=1).dropna()

        # IC stability: fraction of rolling IC that is same sign as full-sample IC
        ic_stability = np.nan
        if name in rolling_ics and not rolling_ics[name].empty and not np.isnan(ic_spearman):
            sign_match = (rolling_ics[name] * np.sign(ic_spearman)) > 0
            ic_stability = sign_match.mean()

        # Best lag (peak absolute correlation)
        best_lag_val = np.nan
        best_lag_corr = np.nan
        if not lag_prof.empty:
            abs_prof = lag_prof.abs()
            best_lag_val = abs_prof.idxmax()
            best_lag_corr = lag_prof.loc[best_lag_val]

        results_rows.append({
            "Indicator": name,
            "Category": meta.get("category", "Other"),
            "IC (Spearman)": ic_spearman,
            "IC (Pearson)": ic_pearson,
            "|IC|": abs(ic_spearman) if not np.isnan(ic_spearman) else 0,
            "IC Stability": ic_stability,
            "R-squared": reg["r_squared"],
            "Beta": reg["beta"],
            "t-stat": reg["t_stat"],
            "Reg p-value": reg["p_value"],
            "Granger p-value": gc["p_value"],
            "Granger Lag": gc["best_lag"],
            "Best Lag": best_lag_val,
            "Corr at Best Lag": best_lag_corr,
            "Observations": len(overlap),
            "Start": overlap.index.min().strftime("%Y-%m-%d") if len(overlap) > 0 else "",
            "End": overlap.index.max().strftime("%Y-%m-%d") if len(overlap) > 0 else "",
            "Inverted": invert_for_liquidity,
        })

    results_df = pd.DataFrame(results_rows)
    if not results_df.empty:
        results_df = results_df.sort_values("|IC|", ascending=False).reset_index(drop=True)

    return {
        "results_df": results_df,
        "rolling_ics": rolling_ics,
        "lag_profiles": lag_profiles,
        "quintile_results": quintile_results,
        "factor_z": factor_z,
    }


# ===========================================================================
# PLOTTING HELPERS
# ===========================================================================

def plot_ic_heatmap(results_df: pd.DataFrame) -> go.Figure:
    """Heatmap of IC values by indicator and category."""
    if results_df.empty:
        return go.Figure()

    df = results_df.sort_values("IC (Spearman)", ascending=True).head(40)

    colors = []
    for v in df["IC (Spearman)"]:
        if v > 0.15:
            colors.append(GREEN)
        elif v > 0.05:
            colors.append("#2ea043")
        elif v < -0.15:
            colors.append(RED)
        elif v < -0.05:
            colors.append("#da3633")
        else:
            colors.append(MUTED)

    fig = go.Figure(go.Bar(
        x=df["IC (Spearman)"],
        y=df["Indicator"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:.3f}" for v in df["IC (Spearman)"]],
        textposition="outside",
        textfont=dict(size=10),
    ))
    _apply_layout(fig, "Spearman IC with Liquidity Factor",
                  "Sorted by IC. Green = positive, Red = negative.", height=max(400, len(df) * 22))
    fig.update_layout(
        xaxis_title="Spearman IC",
        yaxis=dict(tickfont=dict(size=10)),
    )
    return fig


def plot_rolling_ic(rolling_ics: dict, top_n: int = 8, results_df: pd.DataFrame = None) -> go.Figure:
    """Rolling IC time series for top indicators."""
    if not rolling_ics:
        return go.Figure()

    # Pick top N by |IC|
    if results_df is not None and not results_df.empty:
        top_names = results_df.head(top_n)["Indicator"].tolist()
    else:
        top_names = list(rolling_ics.keys())[:top_n]

    colors = [ACCENT, GREEN, RED, YELLOW, "#bc8cff", "#f0883e", "#3fb9a0", "#d2a8ff"]

    fig = go.Figure()
    for i, name in enumerate(top_names):
        if name not in rolling_ics:
            continue
        ric = rolling_ics[name]
        color = colors[i % len(colors)]
        fig.add_trace(go.Scatter(
            x=ric.index, y=ric.values,
            name=name, mode="lines",
            line=dict(width=1.5, color=color),
        ))

    fig.add_hline(y=0, line_dash="dash", line_color=MUTED, opacity=0.5)
    _apply_layout(fig, "Rolling Information Coefficient",
                  f"Top {top_n} indicators, rolling window", height=400)
    fig.update_layout(yaxis_title="Spearman IC")
    return fig


def plot_lag_profile(lag_profiles: dict, names: list[str]) -> go.Figure:
    """Lead-lag correlation profile for selected indicators."""
    if not lag_profiles or not names:
        return go.Figure()

    colors = [ACCENT, GREEN, RED, YELLOW, "#bc8cff", "#f0883e"]
    fig = go.Figure()
    for i, name in enumerate(names):
        if name not in lag_profiles:
            continue
        prof = lag_profiles[name]
        fig.add_trace(go.Scatter(
            x=prof.index, y=prof.values,
            name=name, mode="lines+markers",
            line=dict(width=1.5, color=colors[i % len(colors)]),
            marker=dict(size=3),
        ))

    fig.add_hline(y=0, line_dash="dash", line_color=MUTED, opacity=0.5)
    fig.add_vline(x=0, line_dash="dash", line_color=MUTED, opacity=0.5)
    _apply_layout(fig, "Lead-Lag Correlation Profile",
                  "Positive lag = indicator leads the liquidity factor", height=400)
    fig.update_layout(
        xaxis_title="Lag (periods, positive = indicator leads)",
        yaxis_title="Spearman Correlation",
    )
    return fig


def plot_quintile_bars(quintile_results: dict, name: str) -> go.Figure:
    """Bar chart of mean target value by indicator quintile."""
    if name not in quintile_results:
        return go.Figure()

    qr = quintile_results[name]
    colors_q = [RED, "#da3633", MUTED, "#2ea043", GREEN]
    if len(qr) < len(colors_q):
        colors_q = colors_q[:len(qr)]

    fig = go.Figure(go.Bar(
        x=qr.index, y=qr["mean"],
        marker_color=colors_q,
        text=[f"{v:.3f}" for v in qr["mean"]],
        textposition="outside",
        textfont=dict(size=11),
    ))
    fig.add_trace(go.Scatter(
        x=qr.index, y=qr["mean"],
        mode="lines+markers",
        line=dict(color=ACCENT, width=2, dash="dot"),
        marker=dict(size=6),
        name="Mean",
        showlegend=False,
    ))
    _apply_layout(fig, f"Quintile Analysis: {name}",
                  "Mean liquidity factor z-score by indicator quintile (Q1=lowest)", height=350)
    fig.update_layout(
        xaxis_title="Indicator Quintile",
        yaxis_title="Mean Liquidity Factor Z-Score",
    )
    return fig


def plot_timeseries_comparison(
    factor_z: pd.Series,
    indicator: pd.Series,
    name: str,
    zscore_window: int,
    invert: bool,
) -> go.Figure:
    """Dual-axis time series of indicator vs liquidity factor."""
    ind_z = zscore_rolling(indicator, zscore_window)
    if invert:
        ind_z = -ind_z

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=factor_z.index, y=factor_z.values,
            name="Liquidity Factor", mode="lines",
            line=dict(color=ACCENT, width=2),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=ind_z.index, y=ind_z.values,
            name=f"{name} {'(inv)' if invert else ''}",
            mode="lines",
            line=dict(color=GREEN, width=1.5),
        ),
        secondary_y=True,
    )
    _apply_layout(fig, f"{name} vs Liquidity Factor",
                  "Both z-scored for comparability", height=380)
    fig.update_yaxes(title_text="Liquidity Factor Z", secondary_y=False)
    fig.update_yaxes(title_text=f"{name} Z", secondary_y=True)
    return fig


def plot_scatter(
    factor_z: pd.Series,
    indicator: pd.Series,
    name: str,
    zscore_window: int,
    invert: bool,
) -> go.Figure:
    """Scatter plot with regression line."""
    ind_z = zscore_rolling(indicator, zscore_window)
    if invert:
        ind_z = -ind_z

    df = pd.concat([ind_z.rename("x"), factor_z.rename("y")], axis=1).dropna()
    if len(df) < 30:
        return go.Figure()

    slope, intercept, r, p, se = sp_stats.linregress(df["x"], df["y"])
    x_line = np.linspace(df["x"].min(), df["x"].max(), 100)
    y_line = slope * x_line + intercept

    fig = go.Figure()
    fig.add_trace(go.Scattergl(
        x=df["x"], y=df["y"],
        mode="markers",
        marker=dict(color=ACCENT, size=3, opacity=0.4),
        name="Observations",
    ))
    fig.add_trace(go.Scatter(
        x=x_line, y=y_line,
        mode="lines",
        line=dict(color=RED, width=2),
        name=f"OLS (R2={r**2:.3f}, p={p:.1e})",
    ))
    _apply_layout(fig, f"Scatter: {name} vs Liquidity Factor",
                  f"beta={slope:.3f}, R2={r**2:.3f}", height=380)
    fig.update_layout(
        xaxis_title=f"{name} Z-Score",
        yaxis_title="Liquidity Factor Z-Score",
    )
    return fig


def plot_category_summary(results_df: pd.DataFrame) -> go.Figure:
    """Box plot of |IC| by category."""
    if results_df.empty:
        return go.Figure()

    fig = go.Figure()
    cats = results_df.groupby("Category")["|IC|"].median().sort_values(ascending=False).index
    colors = [ACCENT, GREEN, RED, YELLOW, "#bc8cff", "#f0883e", "#3fb9a0", "#d2a8ff",
              "#8b949e", "#7ee787", "#ffa657", "#ff7b72"]
    for i, cat in enumerate(cats):
        sub = results_df[results_df["Category"] == cat]
        fig.add_trace(go.Box(
            y=sub["|IC|"],
            name=cat,
            marker_color=colors[i % len(colors)],
            boxpoints="all",
            jitter=0.3,
            pointpos=-1.8,
            text=sub["Indicator"],
        ))
    _apply_layout(fig, "|IC| Distribution by Category",
                  "Which category has the most predictive indicators?", height=420)
    fig.update_layout(yaxis_title="|IC|", showlegend=False)
    return fig


# ===========================================================================
# STREAMLIT APP
# ===========================================================================

def main():
    st.title("Liquidity Factor Indicator Research")
    st.markdown(
        f"<p style='color:{MUTED};margin-top:-10px;'>"
        "Systematic testing of macro indicators against liquidity proxies. "
        "Discover which indicators best predict/explain liquidity conditions."
        "</p>",
        unsafe_allow_html=True,
    )

    # ---- Sidebar ----
    st.sidebar.header("Configuration")

    factor_name = st.sidebar.selectbox(
        "Liquidity Factor (Target)",
        list(LIQUIDITY_FACTOR_DEFINITIONS.keys()),
        index=0,
        help="The liquidity proxy to explain/predict.",
    )

    st.sidebar.markdown(
        f"<div style='background:{CARD_BG};border:1px solid #30363d;border-radius:6px;"
        f"padding:10px;font-size:0.82rem;color:{MUTED};'>"
        f"{LIQUIDITY_FACTOR_DEFINITIONS[factor_name]['description']}"
        f"</div>",
        unsafe_allow_html=True,
    )

    resample_freq = st.sidebar.selectbox(
        "Resample Frequency",
        ["W", "2W", "ME"],
        index=0,
        help="Frequency for analysis. Weekly avoids noise; monthly reduces sample size.",
    )

    zscore_window = st.sidebar.slider(
        "Z-Score Window",
        min_value=52, max_value=520, value=252, step=26,
        help="Lookback for rolling z-score normalization (in business days).",
    )

    ic_window = st.sidebar.slider(
        "Rolling IC Window",
        min_value=26, max_value=260, value=104, step=13,
        help="Window for rolling IC computation (in resampled periods).",
    )

    max_lag = st.sidebar.slider(
        "Max Lag (periods)",
        min_value=4, max_value=52, value=26, step=2,
        help="Maximum lag for lead-lag correlation analysis.",
    )

    # ---- Load data ----
    with st.spinner("Loading data from database..."):
        all_indicators = load_all_indicators()
        liquidity_factors = load_liquidity_factors()
        metadata = get_indicator_metadata()

    if factor_name not in liquidity_factors:
        st.error(f"Could not load liquidity factor: {factor_name}")
        return

    factor_series = liquidity_factors[factor_name]

    st.sidebar.markdown("---")
    st.sidebar.metric("Indicators Loaded", len(all_indicators))
    st.sidebar.metric("Factor Observations", len(factor_series))
    st.sidebar.metric(
        "Factor Range",
        f"{factor_series.index.min():%Y-%m} to {factor_series.index.max():%Y-%m}",
    )

    # ---- Run analysis ----
    pipeline = run_analysis_pipeline(
        factor_name=factor_name,
        _factor_series=factor_series,
        _indicators=all_indicators,
        _metadata=metadata,
        zscore_window=zscore_window,
        ic_window=ic_window,
        max_lag=max_lag,
        resample_freq=resample_freq,
    )

    results_df = pipeline["results_df"]
    rolling_ics = pipeline["rolling_ics"]
    lag_profiles = pipeline["lag_profiles"]
    quintile_results = pipeline["quintile_results"]
    factor_z = pipeline["factor_z"]

    if results_df.empty:
        st.warning("No analysis results. Check data availability.")
        return

    # ---- Tabs ----
    tabs = st.tabs([
        "Overview & Rankings",
        "IC Analysis",
        "Lead-Lag Structure",
        "Indicator Deep Dive",
        "Regression & Causality",
        "Methodology",
    ])

    # =======================================================================
    # TAB 0: OVERVIEW & RANKINGS
    # =======================================================================
    with tabs[0]:
        st.subheader("Indicator Ranking Summary")

        # Key metrics
        top = results_df.head(5)
        cols = st.columns(5)
        for i, (_, row) in enumerate(top.iterrows()):
            with cols[i]:
                st.metric(
                    row["Indicator"],
                    f"{row['IC (Spearman)']:.3f}",
                    delta=f"R2={row['R-squared']:.3f}" if not np.isnan(row['R-squared']) else "",
                )

        st.markdown("---")

        # IC heatmap
        st.plotly_chart(plot_ic_heatmap(results_df), use_container_width=True)

        # Category summary
        st.plotly_chart(plot_category_summary(results_df), use_container_width=True)

        # Full ranking table
        st.subheader("Full Ranking Table")
        display_cols = [
            "Indicator", "Category", "IC (Spearman)", "IC (Pearson)",
            "IC Stability", "R-squared", "t-stat", "Reg p-value",
            "Granger p-value", "Best Lag", "Corr at Best Lag",
            "Observations", "Start", "End", "Inverted",
        ]
        available_cols = [c for c in display_cols if c in results_df.columns]
        styled = results_df[available_cols].copy()

        # Format numeric columns
        for col in ["IC (Spearman)", "IC (Pearson)", "IC Stability", "R-squared",
                     "Corr at Best Lag"]:
            if col in styled.columns:
                styled[col] = styled[col].map(lambda x: f"{x:.4f}" if not pd.isna(x) else "")
        for col in ["t-stat"]:
            if col in styled.columns:
                styled[col] = styled[col].map(lambda x: f"{x:.2f}" if not pd.isna(x) else "")
        for col in ["Reg p-value", "Granger p-value"]:
            if col in styled.columns:
                styled[col] = styled[col].map(lambda x: f"{x:.1e}" if not pd.isna(x) else "")

        st.dataframe(styled, use_container_width=True, height=600)

    # =======================================================================
    # TAB 1: IC ANALYSIS
    # =======================================================================
    with tabs[1]:
        st.subheader("Information Coefficient Analysis")

        st.markdown(
            f"""
            <div style='background:{CARD_BG};border:1px solid #30363d;border-radius:8px;
            padding:16px;margin-bottom:16px;color:{MUTED};font-size:0.9rem;'>
            <b style='color:#c9d1d9;'>What is the Information Coefficient?</b><br>
            The IC is the Spearman rank correlation between an indicator's current value
            and the liquidity factor. A high |IC| means the indicator reliably sorts
            periods by liquidity conditions. Values above 0.10 are meaningful;
            above 0.20 is strong for macro data. IC stability measures how
            consistently the rolling IC maintains the same sign as the full-sample IC.
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Rolling IC plot
        n_top = st.slider("Show top N indicators", 3, 15, 8, key="ic_top_n")
        st.plotly_chart(
            plot_rolling_ic(rolling_ics, top_n=n_top, results_df=results_df),
            use_container_width=True,
        )

        # IC stability scatter
        st.subheader("IC Magnitude vs Stability")
        stable_df = results_df[results_df["IC Stability"].notna()].copy()
        if not stable_df.empty:
            fig = go.Figure()
            cats = stable_df["Category"].unique()
            cat_colors = {c: [ACCENT, GREEN, RED, YELLOW, "#bc8cff", "#f0883e",
                              "#3fb9a0", "#d2a8ff", "#8b949e", "#7ee787",
                              "#ffa657", "#ff7b72"][i % 12]
                          for i, c in enumerate(sorted(cats))}

            for cat in sorted(cats):
                sub = stable_df[stable_df["Category"] == cat]
                fig.add_trace(go.Scatter(
                    x=sub["|IC|"], y=sub["IC Stability"],
                    mode="markers+text",
                    marker=dict(size=8, color=cat_colors[cat]),
                    text=sub["Indicator"],
                    textposition="top center",
                    textfont=dict(size=8, color=MUTED),
                    name=cat,
                ))

            fig.add_hline(y=0.5, line_dash="dash", line_color=MUTED, opacity=0.5,
                          annotation_text="50% consistency")
            fig.add_vline(x=0.10, line_dash="dash", line_color=MUTED, opacity=0.5,
                          annotation_text="|IC|=0.10")
            _apply_layout(fig, "IC Magnitude vs Stability",
                          "Top-right quadrant = strong and consistent signal", height=500)
            fig.update_layout(xaxis_title="|IC|", yaxis_title="IC Stability (same-sign %)")
            st.plotly_chart(fig, use_container_width=True)

        # IC by category table
        st.subheader("Average IC by Category")
        cat_stats = results_df.groupby("Category").agg({
            "|IC|": ["mean", "median", "max", "count"],
            "IC Stability": "mean",
        }).round(4)
        cat_stats.columns = ["Mean |IC|", "Median |IC|", "Max |IC|", "Count", "Avg IC Stability"]
        cat_stats = cat_stats.sort_values("Mean |IC|", ascending=False)
        st.dataframe(cat_stats, use_container_width=True)

    # =======================================================================
    # TAB 2: LEAD-LAG STRUCTURE
    # =======================================================================
    with tabs[2]:
        st.subheader("Lead-Lag Correlation Analysis")

        st.markdown(
            f"""
            <div style='background:{CARD_BG};border:1px solid #30363d;border-radius:8px;
            padding:16px;margin-bottom:16px;color:{MUTED};font-size:0.9rem;'>
            <b style='color:#c9d1d9;'>Interpreting lead-lag profiles</b><br>
            A positive lag means the indicator <b>leads</b> the liquidity factor.
            If peak correlation occurs at lag +4, the indicator predicts liquidity
            changes about 4 periods ahead. Symmetric profiles around lag 0 suggest
            contemporaneous co-movement rather than true prediction.
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Select indicators for lag analysis
        available_lag = [n for n in results_df.head(20)["Indicator"] if n in lag_profiles]
        selected_lag = st.multiselect(
            "Select indicators for lag analysis",
            available_lag,
            default=available_lag[:5] if len(available_lag) >= 5 else available_lag,
            key="lag_select",
        )

        if selected_lag:
            st.plotly_chart(
                plot_lag_profile(lag_profiles, selected_lag),
                use_container_width=True,
            )

        # Best lag summary
        st.subheader("Best Lag Summary")
        lag_summary = results_df[results_df["Best Lag"].notna()][
            ["Indicator", "Category", "Best Lag", "Corr at Best Lag", "IC (Spearman)"]
        ].copy()
        lag_summary = lag_summary.sort_values("Best Lag", ascending=True)

        # Indicators that genuinely lead
        leaders = lag_summary[lag_summary["Best Lag"] > 0].copy()
        if not leaders.empty:
            st.markdown("**Indicators that LEAD the liquidity factor:**")
            st.dataframe(
                leaders.style.format({
                    "Best Lag": "{:.0f}",
                    "Corr at Best Lag": "{:.4f}",
                    "IC (Spearman)": "{:.4f}",
                }),
                use_container_width=True,
                height=min(400, len(leaders) * 40 + 40),
            )

        laggers = lag_summary[lag_summary["Best Lag"] < 0].copy()
        if not laggers.empty:
            st.markdown("**Indicators that LAG the liquidity factor (may be effects, not causes):**")
            st.dataframe(
                laggers.style.format({
                    "Best Lag": "{:.0f}",
                    "Corr at Best Lag": "{:.4f}",
                    "IC (Spearman)": "{:.4f}",
                }),
                use_container_width=True,
                height=min(400, len(laggers) * 40 + 40),
            )

    # =======================================================================
    # TAB 3: INDICATOR DEEP DIVE
    # =======================================================================
    with tabs[3]:
        st.subheader("Single Indicator Deep Dive")

        indicator_choice = st.selectbox(
            "Select indicator to analyze",
            results_df["Indicator"].tolist(),
            index=0,
            key="deep_dive_select",
        )

        if indicator_choice and indicator_choice in all_indicators:
            meta = metadata.get(indicator_choice, {})
            inv = meta.get("invert", False)
            ind_series = all_indicators[indicator_choice]

            # Description
            st.markdown(
                f"""
                <div style='background:{CARD_BG};border:1px solid #30363d;border-radius:8px;
                padding:14px;margin-bottom:14px;'>
                <b style='color:#c9d1d9;'>{indicator_choice}</b>
                <span style='color:{ACCENT};font-size:0.8rem;'> | {meta.get("category", "Other")}</span>
                <br><span style='color:{MUTED};font-size:0.88rem;'>{meta.get("description", "")}</span>
                <br><span style='color:{YELLOW};font-size:0.82rem;'>
                {"Inverted for liquidity analysis (raw indicator is negatively related to liquidity)" if inv else "Not inverted"}
                </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Metrics row
            row = results_df[results_df["Indicator"] == indicator_choice].iloc[0]
            m_cols = st.columns(6)
            with m_cols[0]:
                st.metric("Spearman IC", f"{row['IC (Spearman)']:.4f}")
            with m_cols[1]:
                st.metric("Pearson IC", f"{row['IC (Pearson)']:.4f}")
            with m_cols[2]:
                v = row["IC Stability"]
                st.metric("IC Stability", f"{v:.1%}" if not np.isnan(v) else "N/A")
            with m_cols[3]:
                st.metric("R-squared", f"{row['R-squared']:.4f}")
            with m_cols[4]:
                v = row["Granger p-value"]
                st.metric("Granger p", f"{v:.1e}" if not np.isnan(v) else "N/A")
            with m_cols[5]:
                v = row["Best Lag"]
                st.metric("Best Lag", f"{v:.0f}" if not np.isnan(v) else "N/A")

            # Charts
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(
                    plot_timeseries_comparison(factor_z, ind_series, indicator_choice, zscore_window, inv),
                    use_container_width=True,
                )
            with col2:
                st.plotly_chart(
                    plot_scatter(factor_z, ind_series, indicator_choice, zscore_window, inv),
                    use_container_width=True,
                )

            col3, col4 = st.columns(2)
            with col3:
                if indicator_choice in quintile_results:
                    st.plotly_chart(
                        plot_quintile_bars(quintile_results, indicator_choice),
                        use_container_width=True,
                    )
                else:
                    st.info("Insufficient data for quintile analysis.")
            with col4:
                if indicator_choice in lag_profiles:
                    st.plotly_chart(
                        plot_lag_profile(lag_profiles, [indicator_choice]),
                        use_container_width=True,
                    )
                else:
                    st.info("Insufficient data for lag analysis.")

            # Rolling IC for this indicator
            if indicator_choice in rolling_ics:
                ric = rolling_ics[indicator_choice]
                fig_ric = go.Figure()
                fig_ric.add_trace(go.Scatter(
                    x=ric.index, y=ric.values,
                    mode="lines", line=dict(color=ACCENT, width=1.5),
                    name="Rolling IC",
                ))
                fig_ric.add_hline(y=0, line_dash="dash", line_color=MUTED, opacity=0.5)
                fig_ric.add_hline(y=ric.mean(), line_dash="dot", line_color=GREEN, opacity=0.7,
                                  annotation_text=f"Mean: {ric.mean():.3f}")
                _apply_layout(fig_ric, f"Rolling IC: {indicator_choice}",
                              f"Window={ic_window} periods. Stability={row['IC Stability']:.1%}" if not np.isnan(row['IC Stability']) else f"Window={ic_window} periods",
                              height=300)
                fig_ric.update_layout(yaxis_title="Spearman IC")
                st.plotly_chart(fig_ric, use_container_width=True)

    # =======================================================================
    # TAB 4: REGRESSION & GRANGER CAUSALITY
    # =======================================================================
    with tabs[4]:
        st.subheader("Regression & Granger Causality Results")

        st.markdown(
            f"""
            <div style='background:{CARD_BG};border:1px solid #30363d;border-radius:8px;
            padding:16px;margin-bottom:16px;color:{MUTED};font-size:0.9rem;'>
            <b style='color:#c9d1d9;'>Interpreting the results</b><br>
            <b>R-squared</b>: fraction of liquidity factor variance explained by the indicator.
            Values above 0.05 are meaningful for single macro indicators.<br>
            <b>t-stat</b>: significance of the regression coefficient.
            |t| > 2 is statistically significant at the 5% level.<br>
            <b>Granger p-value</b>: p-value of the F-test for Granger causality.
            p < 0.05 means the indicator has statistically significant
            predictive power for the liquidity factor beyond its own history.
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Regression results sorted by R-squared
        reg_df = results_df[
            ["Indicator", "Category", "R-squared", "Beta", "t-stat", "Reg p-value",
             "Granger p-value", "Granger Lag"]
        ].copy()
        reg_df = reg_df.sort_values("R-squared", ascending=False)

        # Highlight significant results
        st.subheader("Top Indicators by R-squared")
        st.dataframe(
            reg_df.head(20).style.format({
                "R-squared": "{:.4f}",
                "Beta": "{:.4f}",
                "t-stat": "{:.2f}",
                "Reg p-value": "{:.1e}",
                "Granger p-value": "{:.1e}",
                "Granger Lag": "{:.0f}",
            }),
            use_container_width=True,
        )

        # Granger causality scatter
        gc_df = results_df[results_df["Granger p-value"].notna()].copy()
        if not gc_df.empty:
            st.subheader("Granger Causality vs IC")
            fig_gc = go.Figure()
            fig_gc.add_trace(go.Scatter(
                x=gc_df["|IC|"],
                y=-np.log10(gc_df["Granger p-value"].clip(lower=1e-20)),
                mode="markers+text",
                marker=dict(
                    size=8,
                    color=gc_df["|IC|"],
                    colorscale="Viridis",
                    showscale=True,
                    colorbar=dict(title="|IC|"),
                ),
                text=gc_df["Indicator"],
                textposition="top center",
                textfont=dict(size=8, color=MUTED),
            ))
            fig_gc.add_hline(
                y=-np.log10(0.05), line_dash="dash", line_color=RED,
                annotation_text="p=0.05 threshold",
            )
            _apply_layout(fig_gc, "Granger Causality vs IC",
                          "Above the red line = statistically significant Granger cause", height=500)
            fig_gc.update_layout(
                xaxis_title="|IC| (Spearman)",
                yaxis_title="-log10(Granger p-value)",
            )
            st.plotly_chart(fig_gc, use_container_width=True)

        # Multivariate regression preview
        st.subheader("Multivariate Regression (Top Indicators)")
        st.markdown(
            f"<span style='color:{MUTED};font-size:0.88rem;'>"
            "OLS with top 5 indicators by |IC|. This is in-sample only -- "
            "interpret R-squared with caution (overfitting risk with many regressors)."
            "</span>",
            unsafe_allow_html=True,
        )
        top5 = results_df.head(5)["Indicator"].tolist()
        X_frames = []
        for name in top5:
            if name in all_indicators:
                meta_i = metadata.get(name, {})
                inv_i = meta_i.get("invert", False)
                z = zscore_rolling(all_indicators[name], zscore_window)
                if resample_freq != "D":
                    z = z.resample(resample_freq).last().dropna()
                if inv_i:
                    z = -z
                X_frames.append(z.rename(name))

        if X_frames and not factor_z.empty:
            X_all = pd.concat(X_frames, axis=1)
            combined = pd.concat([X_all, factor_z.rename("target")], axis=1).dropna()
            if len(combined) > 30:
                try:
                    from sklearn.linear_model import LinearRegression
                    X = combined[top5].values
                    y = combined["target"].values
                    model = LinearRegression().fit(X, y)
                    r2 = model.score(X, y)
                    coefs = pd.DataFrame({
                        "Indicator": top5,
                        "Coefficient": model.coef_,
                        "|Coefficient|": np.abs(model.coef_),
                    }).sort_values("|Coefficient|", ascending=False)

                    m_cols = st.columns(3)
                    with m_cols[0]:
                        st.metric("Multivariate R-squared", f"{r2:.4f}")
                    with m_cols[1]:
                        st.metric("Observations", len(combined))
                    with m_cols[2]:
                        # Marginal R2 improvement over best single
                        best_single_r2 = results_df.iloc[0]["R-squared"]
                        improvement = r2 - best_single_r2 if not np.isnan(best_single_r2) else r2
                        st.metric("R2 Improvement vs Best Single", f"+{improvement:.4f}")

                    st.dataframe(
                        coefs.style.format({"Coefficient": "{:.4f}", "|Coefficient|": "{:.4f}"}),
                        use_container_width=True,
                    )
                except Exception as e:
                    st.warning(f"Multivariate regression failed: {e}")

    # =======================================================================
    # TAB 5: METHODOLOGY
    # =======================================================================
    with tabs[5]:
        st.subheader("Methodology & Interpretation Guide")

        st.markdown(
            f"""
            ### Purpose

            This tool tests which macro indicators are most informative about
            the current state and near-term direction of financial market
            liquidity. The goal is to answer two questions:

            1. **Which indicators contemporaneously co-move with liquidity?**
               These are useful for real-time liquidity monitoring.
            2. **Which indicators lead liquidity?**
               These are useful for predicting liquidity regime changes.

            ### Liquidity Factor Definitions

            We test against multiple liquidity proxies because "liquidity" is a
            multi-dimensional concept:

            - **HY OAS (inverted)**: Market-based credit liquidity. The most
              responsive real-time signal, but can be driven by credit-specific
              events (e.g. a single large default).
            - **FCI US**: Broad financial conditions incorporating rates,
              equities, dollar, mortgages, and credit. Slower-moving but more
              comprehensive.
            - **Fed Net Liquidity**: Plumbing-based measure (Fed assets - TGA - RRP).
              Captures the actual quantity of reserves in the system.
            - **CB Liquidity Composite**: Multi-factor composite including
              central bank momentum and rate expectations.
            - **Credit Conditions**: Focused on the credit channel specifically.

            ### Statistical Methods

            **Information Coefficient (IC)**: Spearman rank correlation between
            indicator value and liquidity factor at the same point in time.
            Rank correlation is more robust to outliers than Pearson.

            **Rolling IC**: IC computed over a rolling window to assess signal
            stability. A high full-sample IC that is unstable over time may
            reflect regime dependence.

            **IC Stability**: Fraction of rolling IC observations that match
            the sign of the full-sample IC. Values above 60% indicate reliable
            directional information.

            **Lead-Lag Analysis**: Cross-correlation at various lags. Positive
            lag = indicator leads. This identifies potential predictive
            relationships.

            **Granger Causality**: F-test on whether lagged indicator values
            improve prediction of the liquidity factor beyond its own
            autoregressive structure. Performed on differenced data to ensure
            stationarity.

            **Quintile Analysis**: Sorts observations by indicator value and
            computes mean liquidity factor in each quintile. Monotonic pattern
            (Q1 to Q5) indicates a reliable linear relationship.

            ### Z-Score Normalization

            All indicators are z-scored using a rolling window before analysis.
            This ensures comparability across indicators with different units
            and scales. The z-score uses mean/std (not median/MAD as in the
            production model) for simplicity.

            ### Inversion Logic

            Some indicators are inversely related to liquidity by construction.
            For example, credit spreads widen when liquidity tightens. These
            are inverted before analysis so that positive values always mean
            "more liquidity." The "Inverted" column in the ranking table
            indicates which indicators were flipped.

            ### Caveats

            - **In-sample analysis**: Full-sample IC and regression are in-sample.
              Rolling IC provides some out-of-sample discipline.
            - **Multiple testing**: Testing 40+ indicators inflates the chance
              of spurious discoveries. Focus on indicators with economic
              rationale, not just statistical significance.
            - **Regime dependence**: Relationships may vary across monetary
              policy regimes. The rolling IC chart helps identify this.
            - **Multicollinearity**: Many macro indicators are correlated with
              each other. High multivariate R-squared does not necessarily mean
              independent information.
            """,
        )


if __name__ == "__main__":
    main()
