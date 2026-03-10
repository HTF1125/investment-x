"""
Liquidity -> Forward Equity Return Predictor
=============================================
Which liquidity indicators best predict forward equity index returns?

Tests a comprehensive set of liquidity-related indicators (central bank
balance sheets, M2, credit impulse, spreads, financial conditions, etc.)
against forward 1m/3m/6m/12m returns for a user-selected equity index
using IC analysis, quintile decomposition, rolling IC stability, and regression.

Run with:  streamlit run liquidity_market_predictor.py
"""

from __future__ import annotations

import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats as sp_stats
from sklearn.decomposition import PCA
import streamlit as st

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

# ---------------------------------------------------------------------------
# Must be first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Liquidity -> Equity Return Predictor",  # static; set_page_config must be first call
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
PURPLE = "#bc8cff"

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

# Consistent color palette for quintile charts and categories
QUINTILE_COLORS = ["#f85149", "#d29922", "#8b949e", "#58a6ff", "#3fb950"]
CATEGORY_COLORS = {
    "Central Bank": "#58a6ff",
    "Money Supply": "#bc8cff",
    "Credit": "#d29922",
    "Spreads": "#f85149",
    "Financial Conditions": "#3fb950",
    "Monetary Policy": "#f0883e",
    "Flows & Leverage": "#a5d6ff",
    "China/EM Liquidity": "#ff7b72",
    "Sentiment": "#e3b341",
    "Nowcasting": "#56d364",
    "OECD Leading": "#79c0ff",
    "Correlation/Regime": "#d2a8ff",
    "Factors": "#ffa657",
    "Alt Data": "#7ee787",
}

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
# INDICATOR REGISTRY
# ===========================================================================
# Each entry: (display_name, callable, category, description, invert)
# "invert" means the raw series is inversely related to liquidity easing
# (e.g., higher real yields = tighter, so we negate before computing IC).
# NOTE: we do NOT invert for the IC computation -- invert is used only
# so that the *sign* interpretation is consistent in the narrative.
# The IC is always raw Spearman(indicator, forward_return).

def _build_indicator_registry() -> List[Tuple[str, Callable, str, str, bool]]:
    """Build the full registry of liquidity-related indicators."""
    from ix.db.custom import (
        # Core liquidity (ix/db/custom/liquidity.py)
        fed_net_liquidity,
        tga_drawdown,
        treasury_net_issuance,
        m2_us,
        m2_world_total_yoy,
        credit_impulse,
        global_liquidity_yoy,
        # Financial conditions (ix/db/custom/fci.py)
        fci_us,
        fci_stress,
        # Rates & spreads (ix/db/custom/rates.py)
        us_2s10s,
        us_3m10y,
        us_10y_real,
        us_10y_breakeven,
        hy_spread,
        ig_spread,
        bbb_spread,
        hy_ig_ratio,
        risk_appetite,
        # Credit deep (ix/db/custom/credit_deep.py)
        credit_stress_index,
        hy_spread_momentum,
        hy_spread_velocity,
        leveraged_loan_spread,
        credit_cycle_phase,
        ig_hy_compression,
        financial_conditions_credit,
        # Central bank (ix/db/custom/central_bank.py)
        fed_total_assets,
        fed_assets_yoy,
        fed_assets_momentum,
        g4_balance_sheet_total,
        g4_balance_sheet_yoy,
        rate_cut_probability_proxy,
        global_rate_divergence,
        central_bank_liquidity_composite,
        # Monetary policy (ix/db/custom/monetary_policy.py)
        rate_cut_expectations,
        rate_expectations_momentum,
        term_premium_proxy,
        policy_rate_level,
        # Fund flows & leverage (ix/db/custom/fund_flows.py)
        margin_debt_yoy,
        equity_bond_flow_ratio,
        bank_credit_impulse,
        consumer_credit_growth,
        # China/EM liquidity (ix/db/custom/china_em.py)
        china_credit_impulse,
        china_m2_yoy,
        china_m2_momentum,
        pboc_easing_proxy,
        em_sovereign_spread,
        # Cross-asset proxies
        dollar_index,
    )
    from ix.db.custom.sentiment import cesi_breadth, cesi_momentum
    from ix.db.custom.nowcasting import (
        weekly_economic_index,
        wei_momentum,
        initial_claims,
        nowcast_composite,
    )
    from ix.db.custom.oecd import (
        oecd_cli_diffusion_world,
        oecd_cli_diffusion_developed,
        oecd_cli_diffusion_emerging,
    )
    from ix.db.custom.correlation_regime import (
        equity_bond_corr_zscore,
        safe_haven_demand,
        tail_risk_index,
    )
    from ix.db.custom.factors import momentum_breadth, momentum_composite
    from ix.db.custom.alt_data import sox_momentum, baltic_dry_momentum

    registry = [
        # --- Central Bank ---
        ("Fed Total Assets", fed_total_assets, "Central Bank",
         "Federal Reserve balance sheet size ($T). QE = rising = bullish.", False),
        ("Fed Assets YoY", fed_assets_yoy, "Central Bank",
         "Fed balance sheet year-over-year change (%). QE vs QT regime.", False),
        ("Fed BS Momentum", fed_assets_momentum, "Central Bank",
         "Fed balance sheet 13-week change ($T). Direction of flow.", False),
        ("Fed Net Liquidity", fed_net_liquidity, "Central Bank",
         "Fed assets minus TGA minus RRP ($T). Net liquidity available.", False),
        ("G4 Balance Sheet", g4_balance_sheet_total, "Central Bank",
         "Fed + ECB + BOJ combined balance sheet ($T).", False),
        ("G4 BS YoY", g4_balance_sheet_yoy, "Central Bank",
         "G4 combined balance sheet YoY change (%). Net global QE/QT.", False),
        ("CB Liquidity Composite", central_bank_liquidity_composite, "Central Bank",
         "Composite of Fed momentum, G4 YoY, net liquidity, rate cuts.", False),

        # --- Money Supply ---
        ("US M2", lambda: m2_us(), "Money Supply",
         "US M2 money supply level ($T).", False),
        ("Global M2 YoY", lambda: m2_world_total_yoy(), "Money Supply",
         "Global M2 aggregate YoY growth (%). Broad money creation.", False),
        ("Global Liquidity YoY", lambda: global_liquidity_yoy(), "Money Supply",
         "Central bank liquidity proxy YoY (simplified M2-based).", False),
        ("China M2 YoY", lambda: china_m2_yoy(), "China/EM Liquidity",
         "China M2 growth (%). PBoC easing/tightening.", False),
        ("China M2 Momentum", lambda: china_m2_momentum(), "China/EM Liquidity",
         "3-month change in China M2 growth. Credit acceleration.", False),

        # --- Credit ---
        ("Credit Impulse", lambda: credit_impulse(), "Credit",
         "US bank credit 2nd derivative. Leads GDP by 6-9 months.", False),
        ("Bank Credit Impulse", lambda: bank_credit_impulse(), "Credit",
         "Bank credit growth acceleration.", False),
        ("Consumer Credit YoY", lambda: consumer_credit_growth(), "Credit",
         "Consumer credit outstanding YoY growth (%).", False),
        ("China Credit Impulse", lambda: china_credit_impulse(), "China/EM Liquidity",
         "China M2 growth acceleration. Leads global growth 6-12mo.", False),
        ("Credit Cycle Phase", credit_cycle_phase, "Credit",
         "Composite of spread level and momentum. Positive = improving.", False),
        ("Credit Conditions", financial_conditions_credit, "Credit",
         "Credit component of financial conditions (BBB + HY + bank credit).", False),

        # --- Spreads ---
        ("HY Spread", hy_spread, "Spreads",
         "ICE BofA US High Yield OAS. Wider = stress.", True),
        ("IG Spread", ig_spread, "Spreads",
         "ICE BofA US Investment Grade OAS.", True),
        ("BBB Spread", bbb_spread, "Spreads",
         "ICE BofA BBB US Corporate OAS.", True),
        ("HY/IG Ratio", hy_ig_ratio, "Spreads",
         "HY-to-IG spread ratio. Rises in stress.", True),
        ("HY Spread Momentum", lambda: hy_spread_momentum(), "Spreads",
         "HY spread 60-day change (bps). Positive = widening.", True),
        ("HY Spread Velocity", lambda: hy_spread_velocity(), "Spreads",
         "Rate of change of HY spread movement. Accelerating stress.", True),
        ("Leveraged Loan Spread", leveraged_loan_spread, "Spreads",
         "HY-IG differential proxy for leveraged loans.", True),
        ("IG/HY Compression", ig_hy_compression, "Spreads",
         "IG/HY ratio. Rising = spread compression (risk appetite).", False),
        ("Credit Stress Index", lambda: credit_stress_index(), "Spreads",
         "Composite of HY, IG, VIX, curve stress. Higher = worse.", True),
        ("EM Sovereign Spread", em_sovereign_spread, "Spreads",
         "EM sovereign spread proxy. Rising = EM stress.", True),

        # --- Financial Conditions ---
        ("FCI US", fci_us, "Financial Conditions",
         "US Financial Conditions composite. Lower = tighter.", False),
        ("FCI Stress", fci_stress, "Financial Conditions",
         "Financial stress (VIX + MOVE + spreads). Higher = stress.", True),
        ("Risk Appetite", lambda: risk_appetite(), "Financial Conditions",
         "Inverted avg z-score of vol + spreads. Higher = more appetite.", False),

        # --- Monetary Policy ---
        ("Policy Rate", policy_rate_level, "Monetary Policy",
         "Implied Fed Funds rate from FF1. Higher = tighter.", True),
        ("Rate Cut Expectations", rate_cut_expectations, "Monetary Policy",
         "Market-implied rate change next 12mo (bps). Positive = cuts.", False),
        ("Rate Expect Momentum", rate_expectations_momentum, "Monetary Policy",
         "Velocity of repricing in rate expectations.", False),
        ("Rate Cut Proxy", rate_cut_probability_proxy, "Monetary Policy",
         "Fed Funds minus 2Y yield. Positive = pricing cuts.", False),
        ("Term Premium", term_premium_proxy, "Monetary Policy",
         "10Y yield minus implied 12M rate. Compensation for duration.", True),
        ("G4 Rate Divergence", global_rate_divergence, "Monetary Policy",
         "Std dev of G4 policy rates. High = instability risk.", True),

        # --- Yield Curve ---
        ("US 2s10s", us_2s10s, "Monetary Policy",
         "10Y minus 2Y yield spread. Negative = inverted = recession risk.", False),
        ("US 3m10y", us_3m10y, "Monetary Policy",
         "10Y minus 3M yield spread. Classic recession predictor.", False),

        # --- TGA / Fiscal ---
        ("TGA Drawdown", tga_drawdown, "Central Bank",
         "TGA 13-week change. Drawdown (negative) = liquidity injection.", True),
        ("Treasury Net Issuance", treasury_net_issuance, "Central Bank",
         "Net Treasury supply pressure. Rising = bearish for liquidity.", True),

        # --- Flows & Leverage ---
        ("Margin Debt YoY", margin_debt_yoy, "Flows & Leverage",
         "FINRA margin debt YoY growth (%). Leverage cycle proxy.", False),
        ("Equity/Bond Flow Proxy", lambda: equity_bond_flow_ratio(), "Flows & Leverage",
         "SPY/TLT relative momentum as flow rotation proxy.", False),

        # --- China/EM ---
        ("PBoC Easing Proxy", lambda: pboc_easing_proxy(), "China/EM Liquidity",
         "China M2 growth minus IP growth. Rising = excess liquidity.", False),

        # --- Cross-Asset Liquidity Proxies ---
        ("Dollar Index", lambda: dollar_index(), "Financial Conditions",
         "DXY. Strong dollar = tighter global liquidity conditions.", True),
        ("US 10Y Real Yield", us_10y_real, "Monetary Policy",
         "TIPS real yield. Higher = tighter real conditions.", True),
        ("10Y Breakeven", us_10y_breakeven, "Monetary Policy",
         "Market inflation expectations. Reflation signal.", False),

        # --- Sentiment ---
        ("CESI Breadth", cesi_breadth, "Sentiment",
         "% of regions with positive Citi Economic Surprise. High = broad upside surprise.", False),
        ("CESI Momentum", cesi_momentum, "Sentiment",
         "% of regions with improving economic surprise readings.", False),

        # --- Nowcasting ---
        ("Weekly Economic Index", weekly_economic_index, "Nowcasting",
         "NY Fed Weekly Economic Index. Real-time activity proxy.", False),
        ("WEI Momentum", wei_momentum, "Nowcasting",
         "4-week change in Weekly Economic Index. Acceleration signal.", False),
        ("Initial Claims", initial_claims, "Nowcasting",
         "Weekly initial jobless claims (inverted: high claims = bearish).", True),
        ("Nowcast Composite", nowcast_composite, "Nowcasting",
         "Composite of WEI, claims, IP. Real-time growth proxy.", False),

        # --- OECD Leading ---
        ("OECD CLI World", oecd_cli_diffusion_world, "OECD Leading",
         "% of countries with rising OECD Composite Leading Indicator.", False),
        ("OECD CLI Developed", oecd_cli_diffusion_developed, "OECD Leading",
         "% of developed markets with rising OECD CLI.", False),
        ("OECD CLI Emerging", oecd_cli_diffusion_emerging, "OECD Leading",
         "% of emerging markets with rising OECD CLI.", False),

        # --- Correlation / Regime ---
        ("Eq/Bond Corr Z", equity_bond_corr_zscore, "Correlation/Regime",
         "Equity-bond correlation z-score. Positive = positive correlation regime.", False),
        ("Safe Haven Demand", safe_haven_demand, "Correlation/Regime",
         "Gold + Treasury relative strength. Rising = risk-off flows.", True),
        ("Tail Risk Index", tail_risk_index, "Correlation/Regime",
         "Composite tail risk measure (VIX + skew + spreads). Higher = more risk.", True),

        # --- Factors ---
        ("Momentum Breadth", momentum_breadth, "Factors",
         "% of assets with positive momentum across asset classes.", False),
        ("Momentum Composite", momentum_composite, "Factors",
         "Multi-asset momentum score (equities, bonds, commodities, FX).", False),

        # --- Alt Data ---
        ("SOX Momentum", sox_momentum, "Alt Data",
         "Semiconductor index momentum. Leads cyclical equities.", False),
        ("Baltic Dry Momentum", baltic_dry_momentum, "Alt Data",
         "Baltic Dry Index momentum. Global trade activity proxy.", False),
    ]
    return registry


# ===========================================================================
# DATA LOADING
# ===========================================================================

HORIZON_MAP = {"1m": 4, "3m": 13, "6m": 26, "12m": 52}
FREQ_MAP = {"Weekly": "W-WED", "Biweekly": "2W-WED", "Monthly": "ME"}

INDEX_MAP = {
    "ACWI": "ACWI US EQUITY:PX_LAST",
    "S&P 500": "SPX Index:PX_LAST",
    "DAX": "DAX Index:PX_LAST",
    "Nikkei 225": "NKY Index:PX_LAST",
    "KOSPI": "KOSPI Index:PX_LAST",
    "Nifty 50": "NIFTY Index:PX_LAST",
    "Hang Seng": "HSI Index:PX_LAST",
    "Shanghai Comp": "SHCOMP Index:PX_LAST",
    "Stoxx 50": "SX5E Index:PX_LAST",
    "FTSE 100": "UKX Index:PX_LAST",
}

YF_FALLBACK = {
    "ACWI": "ACWI",
    "S&P 500": "^GSPC",
    "DAX": "^GDAXI",
    "Nikkei 225": "^N225",
    "KOSPI": "^KS11",
    "Nifty 50": "^NSEI",
    "Hang Seng": "^HSI",
    "Shanghai Comp": "000001.SS",
    "Stoxx 50": "^STOXX50E",
    "FTSE 100": "^FTSE",
}


@st.cache_data(ttl=3600, show_spinner="Loading index data...")
def load_index(index_name: str) -> pd.Series:
    """Load an equity index price series from the database with yfinance fallback."""
    from ix.db.query import Series as DBSeries
    db_code = INDEX_MAP.get(index_name, "ACWI US EQUITY:PX_LAST")
    s = DBSeries(db_code)
    if s.empty:
        yf_ticker = YF_FALLBACK.get(index_name, "ACWI")
        st.warning(f"{index_name} not found in DB. Trying yfinance ({yf_ticker})...")
        try:
            import yfinance as yf
            df = yf.download(yf_ticker, period="max", auto_adjust=True)
            s = df["Close"].squeeze()
            s.name = index_name
        except Exception:
            st.error(f"Could not load {index_name} from DB or yfinance.")
            return pd.Series(dtype=float)
    s.name = index_name
    return s.dropna()


@st.cache_data(ttl=3600, show_spinner="Loading liquidity indicators...")
def load_all_indicators() -> Dict[str, Tuple[pd.Series, str, str, bool]]:
    """Load all indicators in parallel. Returns {name: (series, category, desc, invert)}."""
    registry = _build_indicator_registry()
    results = {}

    def _load_one(name: str, fn: Callable) -> Tuple[str, pd.Series | None]:
        try:
            raw = fn()
            if isinstance(raw, pd.DataFrame):
                # Some functions return DataFrames; take first column or sum
                if raw.shape[1] == 1:
                    raw = raw.iloc[:, 0]
                else:
                    raw = raw.sum(axis=1)
            if raw is None or (isinstance(raw, pd.Series) and raw.empty):
                return name, None
            return name, raw.dropna()
        except Exception:
            return name, None

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {}
        meta = {}
        for name, fn, cat, desc, inv in registry:
            futures[executor.submit(_load_one, name, fn)] = name
            meta[name] = (cat, desc, inv)

        for future in as_completed(futures):
            name, series = future.result()
            if series is not None and len(series) > 52:
                cat, desc, inv = meta[name]
                results[name] = (series, cat, desc, inv)

    return results


def resample_to_freq(s: pd.Series, freq: str) -> pd.Series:
    """Resample a series to the target frequency using last observation.

    Forward-fills gaps so that lower-frequency data (e.g. monthly M2)
    carries forward to every higher-frequency bucket (e.g. weekly).
    This prevents NaN alignment issues when combining indicators of
    mixed native frequencies in the composite model.
    """
    if s.empty:
        return s
    try:
        return s.resample(freq).last().ffill().dropna()
    except Exception:
        return s


def compute_forward_returns(price: pd.Series, periods: int) -> pd.Series:
    """Compute forward N-period simple returns: price[t+N]/price[t] - 1."""
    fwd = price.shift(-periods) / price - 1
    fwd.name = f"Fwd {periods}w Return"
    return fwd.dropna()


def rolling_zscore(s: pd.Series, window: int) -> pd.Series:
    """Rolling z-score normalization."""
    roll = s.rolling(window, min_periods=max(window // 2, 10))
    z = (s - roll.mean()) / roll.std().replace(0, np.nan)
    return z.replace([np.inf, -np.inf], np.nan).dropna()


# ===========================================================================
# ANALYSIS FUNCTIONS
# ===========================================================================


def compute_ic(indicator: pd.Series, fwd_ret: pd.Series) -> Tuple[float, float]:
    """Spearman rank IC between indicator and forward returns.
    Returns (IC, p-value)."""
    df = pd.concat([indicator, fwd_ret], axis=1).dropna()
    if len(df) < 30:
        return np.nan, np.nan
    corr, pval = sp_stats.spearmanr(df.iloc[:, 0], df.iloc[:, 1])
    return corr, pval


def compute_rolling_ic(
    indicator: pd.Series, fwd_ret: pd.Series, window: int = 52
) -> pd.Series:
    """Rolling Spearman IC over a window.

    pandas Rolling.corr() does not support method='spearman', so we
    rank-transform both series first and then compute rolling Pearson
    correlation on the ranks, which is equivalent to Spearman.
    """
    df = pd.concat({"ind": indicator, "ret": fwd_ret}, axis=1).dropna()
    if len(df) < window:
        return pd.Series(dtype=float)

    # Rolling rank within each window, then Pearson on ranks = Spearman
    ind_rank = df["ind"].rolling(window).rank()
    ret_rank = df["ret"].rolling(window).rank()
    rolling_ic = ind_rank.rolling(window).corr(ret_rank)
    rolling_ic.name = "Rolling IC"
    return rolling_ic.dropna()


def compute_ic_stability(rolling_ic: pd.Series, full_ic: float) -> float:
    """Fraction of rolling windows where IC sign matches full-sample IC sign."""
    if rolling_ic.empty or np.isnan(full_ic) or full_ic == 0:
        return np.nan
    sign_match = (np.sign(rolling_ic) == np.sign(full_ic)).mean()
    return sign_match


def compute_quintile_returns(
    indicator: pd.Series, fwd_ret: pd.Series, n_quantiles: int = 5
) -> pd.DataFrame:
    """Sort by indicator quintile, compute mean forward return per quintile."""
    df = pd.concat({"ind": indicator, "ret": fwd_ret}, axis=1).dropna()
    if len(df) < n_quantiles * 10:
        return pd.DataFrame()
    try:
        df["quintile"] = pd.qcut(df["ind"], n_quantiles, labels=False, duplicates="drop")
    except ValueError:
        return pd.DataFrame()

    stats = df.groupby("quintile")["ret"].agg(["mean", "count", "std"]).reset_index()
    stats.columns = ["Quintile", "Mean Return", "Count", "Std"]
    stats["Quintile"] = stats["Quintile"].astype(int) + 1
    return stats


def compute_monotonicity(quintile_df: pd.DataFrame) -> float:
    """Monotonicity score: Spearman correlation between quintile rank and mean return.
    +1 = perfect monotonic increasing, -1 = perfect decreasing."""
    if quintile_df.empty or len(quintile_df) < 3:
        return np.nan
    corr, _ = sp_stats.spearmanr(quintile_df["Quintile"], quintile_df["Mean Return"])
    return corr


def compute_hit_rate(indicator: pd.Series, fwd_ret: pd.Series) -> float:
    """Fraction of times indicator direction matches forward return direction.
    Uses sign of z-scored indicator vs sign of forward return."""
    df = pd.concat({"ind": indicator, "ret": fwd_ret}, axis=1).dropna()
    if len(df) < 30:
        return np.nan
    hits = (np.sign(df["ind"]) == np.sign(df["ret"])).mean()
    return hits


def compute_regression(indicator: pd.Series, fwd_ret: pd.Series) -> Dict:
    """Univariate OLS regression: fwd_return = alpha + beta * indicator."""
    df = pd.concat({"x": indicator, "y": fwd_ret}, axis=1).dropna()
    if len(df) < 30:
        return {"r2": np.nan, "beta": np.nan, "t_stat": np.nan, "p_value": np.nan}
    slope, intercept, r_value, p_value, std_err = sp_stats.linregress(df["x"], df["y"])
    t_stat = slope / std_err if std_err > 0 else np.nan
    return {
        "r2": r_value**2,
        "beta": slope,
        "t_stat": t_stat,
        "p_value": p_value,
    }


def compute_composite_score(ic: float, stability: float, hit_rate: float) -> float:
    """Weighted composite ranking score: 50% |IC|, 30% stability, 20% hit rate."""
    parts = []
    weights = []
    if not np.isnan(ic):
        parts.append(abs(ic))
        weights.append(0.50)
    if not np.isnan(stability):
        parts.append(stability)
        weights.append(0.30)
    if not np.isnan(hit_rate):
        parts.append(hit_rate)
        weights.append(0.20)
    if not parts:
        return np.nan
    total_w = sum(weights)
    return sum(p * w for p, w in zip(parts, weights)) / total_w


# ===========================================================================
# FULL ANALYSIS PIPELINE
# ===========================================================================


@st.cache_data(ttl=3600, show_spinner="Running full indicator analysis...")
def run_full_analysis(
    _acwi_prices: pd.Series,
    _indicators: Dict,
    freq: str,
    zscore_window: int,
    rolling_ic_window: int,
    index_name: str = "ACWI",
) -> Dict:
    """Run all analyses for all indicators across all horizons.

    Returns a nested dict: {horizon: {indicator_name: {metric: value}}}
    Also returns aligned data for plotting.
    """
    # Resample target index
    acwi = resample_to_freq(_acwi_prices, freq)

    # Compute forward returns for all horizons
    fwd_returns = {}
    for label, periods in HORIZON_MAP.items():
        fwd_returns[label] = compute_forward_returns(acwi, periods)

    results = {}
    indicator_series_aligned = {}

    for name, (raw_series, cat, desc, invert) in _indicators.items():
        # Resample indicator to same frequency
        ind_resampled = resample_to_freq(raw_series, freq)
        if ind_resampled.empty or len(ind_resampled) < 52:
            continue

        # Z-score normalize
        ind_z = rolling_zscore(ind_resampled, zscore_window)
        if ind_z.empty or len(ind_z) < 52:
            continue

        indicator_series_aligned[name] = ind_z

        for horizon_label, fwd in fwd_returns.items():
            key = (horizon_label, name)

            # Align
            df = pd.concat({"ind": ind_z, "ret": fwd}, axis=1).dropna()
            if len(df) < 60:
                continue

            # IC
            ic_val, ic_pval = compute_ic(df["ind"], df["ret"])

            # Rolling IC
            ric = compute_rolling_ic(df["ind"], df["ret"], rolling_ic_window)
            stability = compute_ic_stability(ric, ic_val)

            # Hit rate
            hr = compute_hit_rate(df["ind"], df["ret"])

            # Quintile analysis
            qdf = compute_quintile_returns(df["ind"], df["ret"])
            mono = compute_monotonicity(qdf)

            # Regression
            reg = compute_regression(df["ind"], df["ret"])

            # Composite score
            comp = compute_composite_score(ic_val, stability, hr)

            results[key] = {
                "category": cat,
                "description": desc,
                "invert": invert,
                "ic": ic_val,
                "ic_pval": ic_pval,
                "stability": stability,
                "hit_rate": hr,
                "monotonicity": mono,
                "r2": reg["r2"],
                "beta": reg["beta"],
                "t_stat": reg["t_stat"],
                "reg_pval": reg["p_value"],
                "composite_score": comp,
                "n_obs": len(df),
                "quintile_df": qdf,
                "rolling_ic": ric,
            }

    return {
        "results": results,
        "fwd_returns": fwd_returns,
        "indicator_series": indicator_series_aligned,
        "acwi_resampled": acwi,
    }


# ===========================================================================
# HELPER: Build ranking DataFrame for a given horizon
# ===========================================================================


def build_ranking_df(analysis: Dict, horizon: str) -> pd.DataFrame:
    """Build a DataFrame ranking all indicators for a given horizon."""
    rows = []
    results = analysis["results"]
    for (h, name), metrics in results.items():
        if h != horizon:
            continue
        rows.append({
            "Indicator": name,
            "Category": metrics["category"],
            "IC": metrics["ic"],
            "IC p-val": metrics["ic_pval"],
            "|IC|": abs(metrics["ic"]) if not np.isnan(metrics["ic"]) else np.nan,
            "Stability": metrics["stability"],
            "Hit Rate": metrics["hit_rate"],
            "Monotonicity": metrics["monotonicity"],
            "R2": metrics["r2"],
            "t-stat": metrics["t_stat"],
            "Composite": metrics["composite_score"],
            "N": metrics["n_obs"],
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values("Composite", ascending=False).reset_index(drop=True)


# ===========================================================================
# SIDEBAR
# ===========================================================================

target_index = st.sidebar.selectbox(
    "Target Index",
    list(INDEX_MAP.keys()),
    index=0,
    help="Equity index to predict forward returns for.",
)

st.sidebar.title(f"Liquidity -> {target_index} Returns")
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Target:** Forward {target_index} returns")
st.sidebar.markdown("**Indicators:** Liquidity-related")
st.sidebar.markdown("---")

horizon_choice = st.sidebar.selectbox(
    "Forward Return Horizon",
    list(HORIZON_MAP.keys()),
    index=1,
    help="Forward return period for IC computation.",
)

resample_freq = st.sidebar.selectbox(
    "Resample Frequency",
    list(FREQ_MAP.keys()),
    index=0,
    help="Frequency for aligning indicator and return data.",
)

zscore_win = st.sidebar.slider(
    "Z-Score Window (periods)",
    min_value=26,
    max_value=156,
    value=104,
    step=13,
    help="Rolling window for z-score normalization of indicators.",
)

rolling_ic_win = st.sidebar.slider(
    "Rolling IC Window (periods)",
    min_value=26,
    max_value=156,
    value=52,
    step=13,
    help="Rolling window for IC stability computation.",
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Composite Score = 50% |IC| + 30% Stability + 20% Hit Rate. "
    "All metrics use Spearman rank correlation to handle non-linearities."
)


# ===========================================================================
# LOAD DATA
# ===========================================================================

acwi_prices = load_index(target_index)
if acwi_prices.empty:
    st.error(f"Cannot proceed without {target_index} data. Check database connection.")
    st.stop()

indicators_raw = load_all_indicators()
if not indicators_raw:
    st.error("No indicators loaded. Check database connection and indicator functions.")
    st.stop()

freq_code = FREQ_MAP[resample_freq]

analysis = run_full_analysis(
    acwi_prices,
    indicators_raw,
    freq_code,
    zscore_win,
    rolling_ic_win,
    index_name=target_index,
)

ranking_df = build_ranking_df(analysis, horizon_choice)


# ===========================================================================
# TABS
# ===========================================================================

st.title(f"Liquidity Indicators vs Forward {target_index} Returns")
st.caption(
    f"Testing {len(indicators_raw)} liquidity indicators against forward "
    f"{horizon_choice} {target_index} returns | Resample: {resample_freq} | "
    f"Z-score window: {zscore_win} | Rolling IC window: {rolling_ic_win}"
)

tab_rank, tab_ic, tab_quint, tab_deep, tab_multi, tab_pca, tab_method = st.tabs([
    "Rankings",
    "IC Analysis",
    "Quintile Analysis",
    "Indicator Deep Dive",
    "Multi-Indicator Model",
    "PCA Factors",
    "Methodology",
])


# ===========================================================================
# TAB 1: RANKINGS
# ===========================================================================

with tab_rank:
    if ranking_df.empty:
        st.warning("No indicators had enough data for analysis.")
    else:
        st.subheader(f"Master Ranking -- Forward {horizon_choice} Returns")
        st.markdown(
            "Indicators ranked by composite score (50% |IC| + 30% Stability + 20% Hit Rate). "
            f"Higher composite = stronger, more reliable predictor of forward {target_index} returns."
        )

        # Top metrics
        top5 = ranking_df.head(5)
        cols = st.columns(5)
        for i, row in top5.iterrows():
            with cols[i]:
                ic_str = f"{row['IC']:+.3f}"
                st.metric(row["Indicator"], ic_str, f"Comp: {row['Composite']:.3f}")

        # Full table
        st.markdown("#### Full Ranking Table")
        fmt_df = ranking_df.copy()
        for c in ["IC", "|IC|", "Stability", "Hit Rate", "Monotonicity", "R2", "Composite"]:
            if c in fmt_df.columns:
                fmt_df[c] = fmt_df[c].map(lambda x: f"{x:.4f}" if pd.notna(x) else "-")
        for c in ["IC p-val", "t-stat"]:
            if c in fmt_df.columns:
                fmt_df[c] = fmt_df[c].map(lambda x: f"{x:.3f}" if pd.notna(x) else "-")
        fmt_df["N"] = fmt_df["N"].map(lambda x: f"{int(x)}" if pd.notna(x) else "-")

        st.dataframe(
            fmt_df,
            use_container_width=True,
            hide_index=True,
            height=min(35 * len(fmt_df) + 38, 800),
        )

        # --- IC Heatmap: All indicators x All horizons ---
        st.markdown("---")
        st.subheader("IC Heatmap: All Indicators x All Horizons")
        st.markdown(
            "Spearman IC of each indicator with forward returns across all four horizons. "
            "Blue = positive predictive relationship (higher indicator -> higher returns). "
            "Red = negative relationship."
        )

        # Build heatmap data
        all_horizons = list(HORIZON_MAP.keys())
        # Use ranking order from current horizon for row ordering
        indicator_order = ranking_df["Indicator"].tolist() if not ranking_df.empty else []

        heatmap_data = []
        for name in indicator_order:
            row_vals = []
            for h in all_horizons:
                key = (h, name)
                if key in analysis["results"]:
                    row_vals.append(analysis["results"][key]["ic"])
                else:
                    row_vals.append(np.nan)
            heatmap_data.append(row_vals)

        if heatmap_data:
            heatmap_arr = np.array(heatmap_data)
            fig_hm = go.Figure(data=go.Heatmap(
                z=heatmap_arr,
                x=all_horizons,
                y=indicator_order,
                colorscale="RdBu",
                zmid=0,
                zmin=-0.3,
                zmax=0.3,
                text=[[f"{v:.3f}" if not np.isnan(v) else "" for v in row] for row in heatmap_arr],
                texttemplate="%{text}",
                textfont=dict(size=10),
                hovertemplate="Indicator: %{y}<br>Horizon: %{x}<br>IC: %{z:.4f}<extra></extra>",
            ))
            _apply_layout(fig_hm, "Information Coefficient Heatmap",
                          "Spearman rank IC | Blue = positive, Red = negative",
                          height=max(400, len(indicator_order) * 22))
            fig_hm.update_layout(
                yaxis=dict(autorange="reversed"),
                xaxis=dict(side="top"),
            )
            st.plotly_chart(fig_hm, use_container_width=True)

        # --- Category breakdown ---
        st.markdown("---")
        st.subheader("Category Average IC")
        cat_ic = ranking_df.groupby("Category").agg(
            avg_ic=("IC", "mean"),
            avg_abs_ic=("|IC|", lambda x: pd.to_numeric(x, errors="coerce").mean()),
            count=("Indicator", "count"),
            avg_composite=("Composite", lambda x: pd.to_numeric(x, errors="coerce").mean()),
        ).sort_values("avg_abs_ic", ascending=False).reset_index()

        fig_cat = go.Figure()
        colors = [CATEGORY_COLORS.get(c, ACCENT) for c in cat_ic["Category"]]
        fig_cat.add_trace(go.Bar(
            x=cat_ic["Category"],
            y=cat_ic["avg_ic"],
            marker_color=colors,
            text=[f"{v:.3f}" for v in cat_ic["avg_ic"]],
            textposition="outside",
            hovertemplate="Category: %{x}<br>Avg IC: %{y:.4f}<extra></extra>",
        ))
        _apply_layout(fig_cat, f"Average IC by Category ({horizon_choice} fwd)",
                       "Mean Spearman IC across indicators in each category", 400)
        fig_cat.update_layout(yaxis_title="Average IC", showlegend=False)
        st.plotly_chart(fig_cat, use_container_width=True)


# ===========================================================================
# TAB 2: IC ANALYSIS
# ===========================================================================

with tab_ic:
    if ranking_df.empty:
        st.warning("No data available.")
    else:
        st.subheader(f"IC Analysis -- Forward {horizon_choice}")

        # IC vs Stability scatter
        st.markdown("#### IC vs Stability Scatter")
        st.markdown(
            "Top-right quadrant = high |IC| AND high stability = best predictors. "
            "Stability = fraction of rolling windows where IC sign matches full-sample IC."
        )

        numeric_rank = ranking_df.copy()
        for c in ["|IC|", "Stability", "Hit Rate", "Composite"]:
            numeric_rank[c] = pd.to_numeric(numeric_rank[c], errors="coerce")

        fig_scatter = go.Figure()
        for cat in numeric_rank["Category"].unique():
            mask = numeric_rank["Category"] == cat
            sub = numeric_rank[mask]
            fig_scatter.add_trace(go.Scatter(
                x=sub["|IC|"],
                y=sub["Stability"],
                mode="markers+text",
                name=cat,
                text=sub["Indicator"],
                textposition="top center",
                textfont=dict(size=8),
                marker=dict(
                    size=sub["Hit Rate"].fillna(0.5) * 20 + 5,
                    color=CATEGORY_COLORS.get(cat, ACCENT),
                    opacity=0.8,
                ),
                hovertemplate=(
                    "<b>%{text}</b><br>|IC|: %{x:.4f}<br>"
                    "Stability: %{y:.2%}<extra></extra>"
                ),
            ))
        _apply_layout(fig_scatter, "IC Magnitude vs IC Stability",
                       "Marker size proportional to hit rate | Top-right = best", 550)
        fig_scatter.update_layout(
            xaxis_title="|IC| (Spearman)",
            yaxis_title="IC Stability (sign consistency)",
        )
        # Add quadrant lines
        fig_scatter.add_hline(y=0.5, line_dash="dot", line_color="rgba(139,148,158,0.4)")
        fig_scatter.add_vline(x=0.05, line_dash="dot", line_color="rgba(139,148,158,0.4)")
        st.plotly_chart(fig_scatter, use_container_width=True)

        # Rolling IC for selected indicator
        st.markdown("---")
        st.markdown("#### Rolling IC Time Series")
        ind_choices = ranking_df["Indicator"].tolist()
        selected_ic = st.selectbox("Select indicator for rolling IC:", ind_choices, key="ic_select")

        key = (horizon_choice, selected_ic)
        if key in analysis["results"]:
            ric = analysis["results"][key]["rolling_ic"]
            if not ric.empty:
                fig_ric = go.Figure()
                fig_ric.add_trace(go.Scatter(
                    x=ric.index, y=ric.values,
                    mode="lines",
                    line=dict(color=ACCENT, width=1.5),
                    name="Rolling IC",
                    fill="tozeroy",
                    fillcolor="rgba(88,166,255,0.15)",
                ))
                fig_ric.add_hline(y=0, line_dash="solid", line_color="rgba(139,148,158,0.5)")
                full_ic = analysis["results"][key]["ic"]
                fig_ric.add_hline(
                    y=full_ic, line_dash="dash", line_color=GREEN,
                    annotation_text=f"Full-sample IC: {full_ic:.3f}",
                    annotation_position="top right",
                )
                _apply_layout(
                    fig_ric,
                    f"Rolling IC: {selected_ic}",
                    f"{rolling_ic_win}-period rolling Spearman IC with {horizon_choice} forward {target_index} returns",
                    400,
                )
                fig_ric.update_layout(yaxis_title="Spearman IC", showlegend=False)
                st.plotly_chart(fig_ric, use_container_width=True)

                # Summary stats
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Full-Sample IC", f"{full_ic:+.4f}")
                c2.metric("Stability", f"{analysis['results'][key]['stability']:.1%}")
                c3.metric("Mean Rolling IC", f"{ric.mean():+.4f}")
                c4.metric("Rolling IC Std", f"{ric.std():.4f}")
            else:
                st.info("Not enough data for rolling IC.")

        # Category average IC bar chart
        st.markdown("---")
        st.markdown("#### Category IC Comparison Across Horizons")
        cat_horizon_data = {}
        for h in HORIZON_MAP.keys():
            rdf = build_ranking_df(analysis, h)
            if not rdf.empty:
                cat_horizon_data[h] = rdf.groupby("Category")["IC"].mean()

        if cat_horizon_data:
            cat_df = pd.DataFrame(cat_horizon_data)
            fig_catbar = go.Figure()
            bar_colors = [ACCENT, GREEN, YELLOW, RED]
            for i, h in enumerate(cat_df.columns):
                fig_catbar.add_trace(go.Bar(
                    x=cat_df.index,
                    y=cat_df[h],
                    name=h,
                    marker_color=bar_colors[i % len(bar_colors)],
                    opacity=0.85,
                ))
            _apply_layout(fig_catbar, "Average IC by Category Across Horizons",
                           "Mean Spearman IC | Grouped by indicator category", 450)
            fig_catbar.update_layout(
                barmode="group",
                yaxis_title="Average IC",
                legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
            )
            st.plotly_chart(fig_catbar, use_container_width=True)


# ===========================================================================
# TAB 3: QUINTILE ANALYSIS
# ===========================================================================

with tab_quint:
    if ranking_df.empty:
        st.warning("No data available.")
    else:
        st.subheader(f"Quintile Analysis -- Forward {horizon_choice}")
        st.markdown(
            "Periods are sorted into quintiles by indicator level. Q1 = lowest indicator values, "
            "Q5 = highest. If the indicator is a valid predictor, we expect monotonically "
            "increasing (or decreasing) mean forward returns across quintiles."
        )

        ind_choices_q = ranking_df["Indicator"].tolist()
        selected_q = st.selectbox("Select indicator:", ind_choices_q, key="quint_select")

        key = (horizon_choice, selected_q)
        if key in analysis["results"]:
            qdf = analysis["results"][key]["quintile_df"]
            mono = analysis["results"][key]["monotonicity"]
            ic_val = analysis["results"][key]["ic"]
            inv = analysis["results"][key]["invert"]

            if not qdf.empty:
                fig_q = go.Figure()
                bar_colors = [
                    QUINTILE_COLORS[int(q) - 1] if int(q) <= len(QUINTILE_COLORS)
                    else ACCENT
                    for q in qdf["Quintile"]
                ]
                fig_q.add_trace(go.Bar(
                    x=[f"Q{int(q)}" for q in qdf["Quintile"]],
                    y=qdf["Mean Return"] * 100,
                    marker_color=bar_colors,
                    text=[f"{v*100:.2f}%" for v in qdf["Mean Return"]],
                    textposition="outside",
                    hovertemplate="Quintile %{x}<br>Mean Return: %{y:.2f}%<br>N: %{customdata}<extra></extra>",
                    customdata=qdf["Count"],
                ))
                inv_note = " (inverted: high values = tighter conditions)" if inv else ""
                _apply_layout(
                    fig_q,
                    f"Quintile Returns: {selected_q}",
                    f"Mean {horizon_choice} forward {target_index} return by indicator quintile{inv_note}",
                    400,
                )
                fig_q.update_layout(
                    yaxis_title=f"Mean Fwd Return ({horizon_choice}, %)",
                    showlegend=False,
                    xaxis_title="Indicator Quintile (Q1=lowest, Q5=highest)",
                )
                st.plotly_chart(fig_q, use_container_width=True)

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("IC", f"{ic_val:+.4f}")
                c2.metric("Monotonicity", f"{mono:+.3f}" if not np.isnan(mono) else "-")
                c3.metric("Q5-Q1 Spread", f"{(qdf.iloc[-1]['Mean Return'] - qdf.iloc[0]['Mean Return'])*100:.2f}%")
                c4.metric("Inverted?", "Yes" if inv else "No")

                st.markdown(
                    f"**Interpretation:** {'Higher' if not inv else 'Lower'} values of {selected_q} "
                    f"{'predict higher' if ic_val > 0 else 'predict lower'} forward {target_index} returns. "
                    f"Monotonicity score: {mono:+.3f} (1.0 = perfectly monotonic increasing, "
                    f"-1.0 = perfectly decreasing)."
                )
            else:
                st.info("Not enough data for quintile analysis.")

        # Multi-indicator quintile comparison
        st.markdown("---")
        st.markdown("#### Top 10 Indicators: Q5-Q1 Spread")
        spreads = []
        for _, row in ranking_df.head(15).iterrows():
            k = (horizon_choice, row["Indicator"])
            if k in analysis["results"]:
                qd = analysis["results"][k]["quintile_df"]
                if not qd.empty and len(qd) >= 2:
                    spread = (qd.iloc[-1]["Mean Return"] - qd.iloc[0]["Mean Return"]) * 100
                    spreads.append({"Indicator": row["Indicator"], "Q5-Q1 Spread (%)": spread})

        if spreads:
            spread_df = pd.DataFrame(spreads).sort_values("Q5-Q1 Spread (%)", ascending=True)
            fig_spread = go.Figure()
            colors = [GREEN if v > 0 else RED for v in spread_df["Q5-Q1 Spread (%)"]]
            fig_spread.add_trace(go.Bar(
                x=spread_df["Q5-Q1 Spread (%)"],
                y=spread_df["Indicator"],
                orientation="h",
                marker_color=colors,
                text=[f"{v:.2f}%" for v in spread_df["Q5-Q1 Spread (%)"]],
                textposition="outside",
            ))
            _apply_layout(fig_spread, "Q5-Q1 Return Spread by Indicator",
                           f"Difference in mean {horizon_choice} forward return between top and bottom quintile",
                           max(350, len(spread_df) * 30))
            fig_spread.update_layout(yaxis=dict(autorange="reversed"), showlegend=False)
            st.plotly_chart(fig_spread, use_container_width=True)


# ===========================================================================
# TAB 4: INDICATOR DEEP DIVE
# ===========================================================================

with tab_deep:
    if ranking_df.empty:
        st.warning("No data available.")
    else:
        st.subheader("Indicator Deep Dive")

        ind_choices_d = ranking_df["Indicator"].tolist()
        selected_deep = st.selectbox("Select indicator:", ind_choices_d, key="deep_select")

        key = (horizon_choice, selected_deep)
        if key not in analysis["results"]:
            st.warning("No analysis data for this indicator/horizon.")
        else:
            metrics = analysis["results"][key]
            ind_series = analysis["indicator_series"].get(selected_deep)
            acwi_resamp = analysis["acwi_resampled"]
            fwd = analysis["fwd_returns"].get(horizon_choice)

            # Description card
            st.markdown(f"**Category:** {metrics['category']}")
            st.markdown(f"**Description:** {metrics['description']}")
            if metrics["invert"]:
                st.markdown(
                    "*Note: This indicator is inversely related to liquidity conditions. "
                    "A negative IC means that when the indicator is HIGH (tighter conditions), "
                    "forward returns tend to be LOWER.*"
                )

            # Key metrics row
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("IC", f"{metrics['ic']:+.4f}")
            c2.metric("IC p-value", f"{metrics['ic_pval']:.4f}")
            c3.metric("Stability", f"{metrics['stability']:.1%}")
            c4.metric("Hit Rate", f"{metrics['hit_rate']:.1%}")
            c5.metric("R-squared", f"{metrics['r2']:.4f}")
            c6.metric("t-stat", f"{metrics['t_stat']:.2f}")

            if ind_series is not None and fwd is not None:
                # --- Time series overlay ---
                st.markdown("---")
                st.markdown(f"#### Indicator vs {target_index} (dual axis)")

                fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
                fig_dual.add_trace(
                    go.Scatter(
                        x=acwi_resamp.index, y=acwi_resamp.values,
                        name=target_index, line=dict(color=MUTED, width=1),
                        opacity=0.7,
                    ),
                    secondary_y=False,
                )
                fig_dual.add_trace(
                    go.Scatter(
                        x=ind_series.index, y=ind_series.values,
                        name=selected_deep,
                        line=dict(color=ACCENT, width=1.5),
                    ),
                    secondary_y=True,
                )
                _apply_layout(fig_dual, f"{selected_deep} vs {target_index}",
                               f"Indicator (z-scored) overlaid on {target_index} price", 420)
                fig_dual.update_yaxes(title_text=f"{target_index} Price", secondary_y=False)
                fig_dual.update_yaxes(title_text=f"{selected_deep} (z-score)", secondary_y=True)
                st.plotly_chart(fig_dual, use_container_width=True)

                # --- Scatter plot ---
                st.markdown("#### Scatter: Indicator vs Forward Return")
                df_scatter = pd.concat({"ind": ind_series, "ret": fwd}, axis=1).dropna()

                fig_sc = go.Figure()
                fig_sc.add_trace(go.Scatter(
                    x=df_scatter["ind"],
                    y=df_scatter["ret"] * 100,
                    mode="markers",
                    marker=dict(size=4, color=ACCENT, opacity=0.4),
                    hovertemplate="Indicator: %{x:.2f}<br>Fwd Return: %{y:.1f}%<extra></extra>",
                ))
                # Add regression line
                if len(df_scatter) > 10:
                    slope, intercept, _, _, _ = sp_stats.linregress(
                        df_scatter["ind"], df_scatter["ret"] * 100
                    )
                    x_range = np.linspace(df_scatter["ind"].min(), df_scatter["ind"].max(), 100)
                    fig_sc.add_trace(go.Scatter(
                        x=x_range,
                        y=intercept + slope * x_range,
                        mode="lines",
                        line=dict(color=RED, width=2, dash="dash"),
                        name="OLS fit",
                    ))
                _apply_layout(fig_sc, f"{selected_deep} vs {horizon_choice} Forward Return",
                               f"Each dot = one observation | R2={metrics['r2']:.4f}", 400)
                fig_sc.update_layout(
                    xaxis_title=f"{selected_deep} (z-score)",
                    yaxis_title=f"Forward {horizon_choice} Return (%)",
                    showlegend=False,
                )
                st.plotly_chart(fig_sc, use_container_width=True)

                # --- Rolling IC ---
                ric = metrics["rolling_ic"]
                if not ric.empty:
                    st.markdown("#### Rolling IC")
                    fig_ric2 = go.Figure()
                    pos_mask = ric >= 0
                    neg_mask = ric < 0
                    fig_ric2.add_trace(go.Bar(
                        x=ric.index[pos_mask],
                        y=ric.values[pos_mask],
                        marker_color="rgba(63,185,80,0.6)",
                        name="Positive IC",
                    ))
                    fig_ric2.add_trace(go.Bar(
                        x=ric.index[neg_mask],
                        y=ric.values[neg_mask],
                        marker_color="rgba(248,81,73,0.6)",
                        name="Negative IC",
                    ))
                    fig_ric2.add_hline(y=0, line_color="rgba(139,148,158,0.5)")
                    _apply_layout(fig_ric2, f"Rolling IC: {selected_deep}",
                                   f"{rolling_ic_win}-period rolling Spearman IC", 350)
                    fig_ric2.update_layout(showlegend=False, bargap=0)
                    st.plotly_chart(fig_ric2, use_container_width=True)

                # --- Quintile chart ---
                qdf = metrics["quintile_df"]
                if not qdf.empty:
                    st.markdown("#### Quintile Returns")
                    fig_q2 = go.Figure()
                    bar_colors = [
                        QUINTILE_COLORS[int(q) - 1] if int(q) <= len(QUINTILE_COLORS) else ACCENT
                        for q in qdf["Quintile"]
                    ]
                    fig_q2.add_trace(go.Bar(
                        x=[f"Q{int(q)}" for q in qdf["Quintile"]],
                        y=qdf["Mean Return"] * 100,
                        marker_color=bar_colors,
                        text=[f"{v*100:.2f}%" for v in qdf["Mean Return"]],
                        textposition="outside",
                    ))
                    _apply_layout(fig_q2, f"Quintile Returns: {selected_deep}",
                                   f"Mean {horizon_choice} forward return by quintile", 350)
                    fig_q2.update_layout(
                        yaxis_title="Mean Forward Return (%)",
                        showlegend=False,
                    )
                    st.plotly_chart(fig_q2, use_container_width=True)

            # Cross-horizon table
            st.markdown("---")
            st.markdown("#### Cross-Horizon Summary")
            cross_rows = []
            for h in HORIZON_MAP.keys():
                k = (h, selected_deep)
                if k in analysis["results"]:
                    m = analysis["results"][k]
                    cross_rows.append({
                        "Horizon": h,
                        "IC": f"{m['ic']:+.4f}",
                        "IC p-val": f"{m['ic_pval']:.4f}",
                        "Stability": f"{m['stability']:.1%}",
                        "Hit Rate": f"{m['hit_rate']:.1%}",
                        "R2": f"{m['r2']:.4f}",
                        "t-stat": f"{m['t_stat']:.2f}",
                        "N": m["n_obs"],
                    })
            if cross_rows:
                st.dataframe(pd.DataFrame(cross_rows), use_container_width=True, hide_index=True)


# ===========================================================================
# TAB 5: MULTI-INDICATOR MODEL
# ===========================================================================

with tab_multi:
    st.subheader("Multi-Indicator Composite Model")
    st.markdown(
        "Combine the top-N indicators into a single composite signal using either "
        "equal weights or IC-based weights. Then evaluate the composite's ability "
        f"to predict forward {target_index} returns and run a simple allocation backtest."
    )

    if ranking_df.empty:
        st.warning("No data available.")
    else:
        col_a, col_b, col_c, col_d = st.columns(4)
        top_n = col_a.slider("Top N indicators", 3, 15, 5, key="topn")
        weight_method = col_b.selectbox("Weighting", ["IC-Weighted", "Equal-Weighted"], key="wm")
        composite_horizon = col_c.selectbox(
            "Composite Horizon",
            list(HORIZON_MAP.keys()),
            index=list(HORIZON_MAP.keys()).index(horizon_choice),
            key="comp_h",
        )
        corr_threshold = col_d.slider(
            "Max Correlation",
            min_value=0.30,
            max_value=1.00,
            value=0.70,
            step=0.05,
            key="corr_thresh",
            help="Skip indicators whose absolute correlation with any already-selected indicator exceeds this threshold.",
        )

        # Build composite from top N indicators with collinearity filter
        rdf = build_ranking_df(analysis, composite_horizon)
        if rdf.empty:
            st.warning("No ranking data for selected horizon.")
        else:
            # Greedy forward selection: walk down the ranking, skip indicators
            # that are too correlated with any already-selected indicator.
            ind_data = analysis["indicator_series"]
            selected = []
            skipped = []
            for _, row in rdf.iterrows():
                name = row["Indicator"]
                if name not in ind_data:
                    continue
                if not selected:
                    selected.append(name)
                    continue
                # Check correlation with all already-selected indicators
                candidate = ind_data[name]
                too_correlated = False
                for sel_name in selected:
                    overlap = pd.concat(
                        {"a": candidate, "b": ind_data[sel_name]}, axis=1
                    ).dropna()
                    if len(overlap) < 30:
                        continue
                    rho = abs(overlap["a"].corr(overlap["b"]))
                    if rho > corr_threshold:
                        skipped.append((name, sel_name, rho))
                        too_correlated = True
                        break
                if not too_correlated:
                    selected.append(name)
                if len(selected) >= top_n:
                    break

            top_indicators = selected
            top_ics = {}
            for name in top_indicators:
                k = (composite_horizon, name)
                if k in analysis["results"]:
                    top_ics[name] = analysis["results"][k]["ic"]

            # Show selected indicators
            st.markdown("#### Selected Indicators")
            sel_df = rdf[rdf["Indicator"].isin(top_indicators)][
                ["Indicator", "Category", "IC", "Stability", "Hit Rate", "Composite"]
            ].reset_index(drop=True)
            st.dataframe(sel_df, use_container_width=True, hide_index=True)

            # Show skipped indicators due to collinearity
            if skipped:
                with st.expander(f"Skipped {len(skipped)} collinear indicators (corr > {corr_threshold:.0%})"):
                    skip_df = pd.DataFrame(
                        skipped, columns=["Skipped", "Correlated With", "Correlation"]
                    )
                    skip_df["Correlation"] = skip_df["Correlation"].map(lambda x: f"{x:.3f}")
                    st.dataframe(skip_df, use_container_width=True, hide_index=True)

            # Build composite signal
            ind_data = analysis["indicator_series"]
            composite_parts = {}
            weights = {}

            for name in top_indicators:
                if name in ind_data:
                    ic_val = top_ics.get(name, 0)
                    if weight_method == "IC-Weighted":
                        # Weight by signed IC so that negative-IC indicators are flipped
                        w = ic_val
                    else:
                        # Equal weight with IC sign for direction
                        w = np.sign(ic_val) if ic_val != 0 else 1.0
                    weights[name] = w
                    composite_parts[name] = ind_data[name] * np.sign(ic_val)

            if composite_parts:
                comp_df = pd.DataFrame(composite_parts).dropna()
                if not comp_df.empty:
                    if weight_method == "IC-Weighted":
                        abs_weights = {k: abs(v) for k, v in weights.items() if k in comp_df.columns}
                        total_w = sum(abs_weights.values())
                        if total_w > 0:
                            composite_signal = sum(
                                comp_df[k] * (abs_weights[k] / total_w)
                                for k in abs_weights
                            )
                        else:
                            composite_signal = comp_df.mean(axis=1)
                    else:
                        composite_signal = comp_df.mean(axis=1)

                    composite_signal.name = "Composite"

                    # Compute forward returns for the composite
                    fwd = analysis["fwd_returns"].get(composite_horizon)
                    if fwd is not None:
                        df_comp = pd.concat({"signal": composite_signal, "ret": fwd}, axis=1).dropna()

                        if len(df_comp) > 60:
                            comp_ic, comp_pval = sp_stats.spearmanr(
                                df_comp["signal"], df_comp["ret"]
                            )
                            comp_ric = compute_rolling_ic(
                                df_comp["signal"], df_comp["ret"], rolling_ic_win
                            )
                            comp_stability = compute_ic_stability(comp_ric, comp_ic)
                            comp_hr = compute_hit_rate(df_comp["signal"], df_comp["ret"])
                            comp_qdf = compute_quintile_returns(df_comp["signal"], df_comp["ret"])
                            comp_mono = compute_monotonicity(comp_qdf)

                            st.markdown("---")
                            st.markdown("#### Composite Signal Performance")
                            c1, c2, c3, c4, c5 = st.columns(5)
                            c1.metric("Composite IC", f"{comp_ic:+.4f}")
                            c2.metric("p-value", f"{comp_pval:.4f}")
                            c3.metric("Stability", f"{comp_stability:.1%}")
                            c4.metric("Hit Rate", f"{comp_hr:.1%}")
                            c5.metric("Monotonicity", f"{comp_mono:+.3f}")

                            # Compare composite vs best individual
                            best_ind_ic = float(rdf.iloc[0]["IC"]) if not rdf.empty else 0
                            improvement = abs(comp_ic) - abs(best_ind_ic)
                            st.markdown(
                                f"Composite |IC| = **{abs(comp_ic):.4f}** vs best individual |IC| = "
                                f"**{abs(best_ind_ic):.4f}** | "
                                f"{'Improvement' if improvement > 0 else 'No improvement'}: "
                                f"{improvement:+.4f}"
                            )

                            # Composite quintile chart
                            if not comp_qdf.empty:
                                fig_cq = go.Figure()
                                bar_colors = [
                                    QUINTILE_COLORS[int(q) - 1]
                                    if int(q) <= len(QUINTILE_COLORS) else ACCENT
                                    for q in comp_qdf["Quintile"]
                                ]
                                fig_cq.add_trace(go.Bar(
                                    x=[f"Q{int(q)}" for q in comp_qdf["Quintile"]],
                                    y=comp_qdf["Mean Return"] * 100,
                                    marker_color=bar_colors,
                                    text=[f"{v*100:.2f}%" for v in comp_qdf["Mean Return"]],
                                    textposition="outside",
                                ))
                                _apply_layout(
                                    fig_cq, "Composite Signal Quintile Returns",
                                    f"Mean {composite_horizon} forward {target_index} return by composite quintile",
                                    400,
                                )
                                fig_cq.update_layout(
                                    yaxis_title="Mean Forward Return (%)",
                                    showlegend=False,
                                )
                                st.plotly_chart(fig_cq, use_container_width=True)

                            # Rolling IC of composite
                            if not comp_ric.empty:
                                fig_cric = go.Figure()
                                fig_cric.add_trace(go.Scatter(
                                    x=comp_ric.index, y=comp_ric.values,
                                    mode="lines", fill="tozeroy",
                                    line=dict(color=PURPLE, width=1.5),
                                    fillcolor="rgba(188,140,255,0.15)",
                                ))
                                fig_cric.add_hline(y=0, line_color="rgba(139,148,158,0.5)")
                                fig_cric.add_hline(
                                    y=comp_ic, line_dash="dash", line_color=GREEN,
                                    annotation_text=f"Full IC: {comp_ic:.3f}",
                                )
                                _apply_layout(
                                    fig_cric, "Composite Rolling IC",
                                    f"{rolling_ic_win}-period rolling Spearman IC", 380,
                                )
                                fig_cric.update_layout(showlegend=False)
                                st.plotly_chart(fig_cric, use_container_width=True)

                            # --- Simple Allocation Backtest ---
                            st.markdown("---")
                            st.subheader("Allocation Backtest")
                            st.markdown(
                                "**Strategy:** Benchmark is 50% equity / 50% cash. The composite signal "
                                "adjusts the equity weight between 10% and 90%. When signal is strongly "
                                "bullish (top quintile), equity weight is 90%. When strongly bearish "
                                "(bottom quintile), equity weight is 10%."
                            )

                            # Build allocation weights using percentile rank of composite
                            acwi_weekly = analysis["acwi_resampled"]
                            acwi_ret = acwi_weekly.pct_change().dropna()

                            # Align composite signal with returns (lag by 1 period for no look-ahead)
                            signal_lagged = composite_signal.shift(1)
                            # Map signal to equity weight using percentile rank
                            signal_pctile = signal_lagged.rolling(
                                zscore_win, min_periods=zscore_win // 2
                            ).apply(lambda x: sp_stats.percentileofscore(x[:-1], x[-1]) / 100.0 if len(x) > 1 else 0.5, raw=True)

                            # Linear mapping: percentile 0 -> 10% equity, percentile 1 -> 90% equity
                            eq_weight = 0.10 + signal_pctile * 0.80
                            eq_weight = eq_weight.clip(0.10, 0.90)

                            # Align everything
                            bt_df = pd.concat({
                                "acwi_ret": acwi_ret,
                                "eq_weight": eq_weight,
                            }, axis=1).dropna()

                            if len(bt_df) > 52:
                                # Strategy return = equity_weight * acwi_return
                                bt_df["strategy_ret"] = bt_df["eq_weight"] * bt_df["acwi_ret"]
                                bt_df["benchmark_ret"] = 0.50 * bt_df["acwi_ret"]

                                # Cumulative returns
                                bt_df["strategy_cum"] = (1 + bt_df["strategy_ret"]).cumprod()
                                bt_df["benchmark_cum"] = (1 + bt_df["benchmark_ret"]).cumprod()
                                bt_df["acwi_cum"] = (1 + bt_df["acwi_ret"]).cumprod()

                                # Performance metrics
                                ann_factor = 52  # weekly
                                n_years = len(bt_df) / ann_factor

                                strat_ann_ret = bt_df["strategy_cum"].iloc[-1] ** (1 / n_years) - 1
                                bench_ann_ret = bt_df["benchmark_cum"].iloc[-1] ** (1 / n_years) - 1
                                acwi_ann_ret = bt_df["acwi_cum"].iloc[-1] ** (1 / n_years) - 1

                                strat_vol = bt_df["strategy_ret"].std() * np.sqrt(ann_factor)
                                bench_vol = bt_df["benchmark_ret"].std() * np.sqrt(ann_factor)

                                strat_sharpe = strat_ann_ret / strat_vol if strat_vol > 0 else 0
                                bench_sharpe = bench_ann_ret / bench_vol if bench_vol > 0 else 0

                                # Max drawdown
                                def max_drawdown(cum_series):
                                    peak = cum_series.expanding().max()
                                    dd = cum_series / peak - 1
                                    return dd.min()

                                strat_mdd = max_drawdown(bt_df["strategy_cum"])
                                bench_mdd = max_drawdown(bt_df["benchmark_cum"])

                                # Information ratio
                                excess = bt_df["strategy_ret"] - bt_df["benchmark_ret"]
                                te = excess.std() * np.sqrt(ann_factor)
                                ir = (strat_ann_ret - bench_ann_ret) / te if te > 0 else 0

                                # Hit rate (weekly)
                                bt_hit = (excess > 0).mean()

                                # Display metrics
                                st.markdown("#### Performance Summary")
                                mc1, mc2, mc3, mc4 = st.columns(4)
                                mc1.metric("Strategy Ann Return", f"{strat_ann_ret:.1%}",
                                           f"vs Bench {bench_ann_ret:.1%}")
                                mc2.metric("Strategy Sharpe", f"{strat_sharpe:.2f}",
                                           f"vs Bench {bench_sharpe:.2f}")
                                mc3.metric("Max Drawdown", f"{strat_mdd:.1%}",
                                           f"vs Bench {bench_mdd:.1%}")
                                mc4.metric("Information Ratio", f"{ir:.2f}")

                                mc5, mc6, mc7, mc8 = st.columns(4)
                                mc5.metric("Strategy Volatility", f"{strat_vol:.1%}")
                                mc6.metric("Tracking Error", f"{te:.1%}")
                                mc7.metric("Weekly Hit Rate", f"{bt_hit:.1%}")
                                mc8.metric("Avg Equity Weight", f"{bt_df['eq_weight'].mean():.0%}")

                                # Cumulative return chart
                                fig_bt = go.Figure()
                                fig_bt.add_trace(go.Scatter(
                                    x=bt_df.index, y=bt_df["strategy_cum"],
                                    name="Strategy", line=dict(color=GREEN, width=2),
                                ))
                                fig_bt.add_trace(go.Scatter(
                                    x=bt_df.index, y=bt_df["benchmark_cum"],
                                    name="50% Benchmark", line=dict(color=MUTED, width=1.5, dash="dash"),
                                ))
                                fig_bt.add_trace(go.Scatter(
                                    x=bt_df.index, y=bt_df["acwi_cum"],
                                    name=f"100% {target_index}", line=dict(color=ACCENT, width=1, dash="dot"),
                                    opacity=0.6,
                                ))
                                _apply_layout(fig_bt, "Cumulative Returns",
                                               f"Strategy vs 50% Benchmark vs 100% {target_index}", 450)
                                fig_bt.update_layout(yaxis_title="Growth of $1")
                                st.plotly_chart(fig_bt, use_container_width=True)

                                # Equity weight over time
                                fig_wt = go.Figure()
                                fig_wt.add_trace(go.Scatter(
                                    x=bt_df.index, y=bt_df["eq_weight"] * 100,
                                    mode="lines", fill="tozeroy",
                                    line=dict(color=ACCENT, width=1),
                                    fillcolor="rgba(88,166,255,0.2)",
                                ))
                                fig_wt.add_hline(
                                    y=50, line_dash="dash", line_color=MUTED,
                                    annotation_text="50% Benchmark",
                                )
                                _apply_layout(fig_wt, "Equity Weight Over Time",
                                               "Composite signal-driven allocation (10%-90% range)", 300)
                                fig_wt.update_layout(
                                    yaxis_title="Equity Weight (%)",
                                    yaxis_range=[0, 100],
                                    showlegend=False,
                                )
                                st.plotly_chart(fig_wt, use_container_width=True)

                                # Drawdown comparison
                                strat_dd = bt_df["strategy_cum"] / bt_df["strategy_cum"].expanding().max() - 1
                                bench_dd = bt_df["benchmark_cum"] / bt_df["benchmark_cum"].expanding().max() - 1
                                fig_dd = go.Figure()
                                fig_dd.add_trace(go.Scatter(
                                    x=strat_dd.index, y=strat_dd.values * 100,
                                    name="Strategy", fill="tozeroy",
                                    line=dict(color=RED, width=1),
                                    fillcolor="rgba(248,81,73,0.2)",
                                ))
                                fig_dd.add_trace(go.Scatter(
                                    x=bench_dd.index, y=bench_dd.values * 100,
                                    name="Benchmark", line=dict(color=MUTED, width=1, dash="dash"),
                                ))
                                _apply_layout(fig_dd, "Drawdown Comparison",
                                               "Strategy vs 50% benchmark drawdown", 350)
                                fig_dd.update_layout(yaxis_title="Drawdown (%)")
                                st.plotly_chart(fig_dd, use_container_width=True)

                                # Rolling 1-year excess return
                                rolling_excess = excess.rolling(52).sum()
                                if not rolling_excess.dropna().empty:
                                    fig_re = go.Figure()
                                    pos_mask = rolling_excess >= 0
                                    fig_re.add_trace(go.Scatter(
                                        x=rolling_excess.index,
                                        y=rolling_excess.values * 100,
                                        mode="lines",
                                        fill="tozeroy",
                                        line=dict(
                                            color=GREEN, width=1
                                        ),
                                        fillcolor="rgba(63,185,80,0.15)",
                                    ))
                                    fig_re.add_hline(y=0, line_color="rgba(139,148,158,0.5)")
                                    _apply_layout(
                                        fig_re, "Rolling 1-Year Excess Return",
                                        "Strategy minus 50% benchmark (trailing 52 weeks)", 350,
                                    )
                                    fig_re.update_layout(
                                        yaxis_title="Excess Return (%)",
                                        showlegend=False,
                                    )
                                    st.plotly_chart(fig_re, use_container_width=True)

                            else:
                                st.warning("Insufficient data for backtest (need >52 periods).")

                    else:
                        st.warning("Forward returns not available for composite evaluation.")
                else:
                    st.warning("Could not align composite data.")
            else:
                st.warning("No indicator series available for composite construction.")


# ===========================================================================
# TAB 6: PCA FACTORS
# ===========================================================================

with tab_pca:
    st.subheader("PCA Factor Analysis")
    st.markdown(
        "Extract orthogonal principal components from all indicator z-scores, "
        "then test each PC's ability to predict forward returns. PCs are "
        "**guaranteed uncorrelated** — eliminating collinearity entirely."
    )

    ind_data = analysis["indicator_series"]
    if len(ind_data) < 5:
        st.warning("Need at least 5 indicators with data for PCA.")
    else:
        # --- PCA Controls ---
        pca_c1, pca_c2, pca_c3 = st.columns(3)
        n_components = pca_c1.slider("Number of PCs", 3, 10, 5, key="n_pcs")
        pca_window = pca_c2.slider(
            "Rolling PCA Window (weeks)", 104, 260, 156, step=26, key="pca_win",
            help="Window for rolling PCA. 156 = 3 years.",
        )
        pca_horizon = pca_c3.selectbox(
            "Forward Horizon",
            list(HORIZON_MAP.keys()),
            index=list(HORIZON_MAP.keys()).index(horizon_choice),
            key="pca_h",
        )

        # --- Build aligned indicator matrix ---
        # Use all z-scored indicator series, align on common dates
        ind_df = pd.DataFrame(ind_data)
        # Drop indicators with >40% missing to keep reasonable coverage
        thresh = len(ind_df) * 0.6
        ind_df = ind_df.dropna(axis=1, thresh=int(thresh))
        # Forward-fill remaining gaps (small holes between observations)
        ind_df = ind_df.ffill().dropna()

        if ind_df.shape[1] < 5 or len(ind_df) < pca_window + 52:
            st.warning(
                f"Insufficient overlapping data for PCA. "
                f"Have {ind_df.shape[1]} indicators × {len(ind_df)} periods; "
                f"need at least 5 indicators × {pca_window + 52} periods."
            )
        else:
            indicator_names = ind_df.columns.tolist()
            n_pcs_actual = min(n_components, ind_df.shape[1])

            # --- Rolling PCA ---
            # At each time step t, fit PCA on [t - pca_window : t] and project
            # week t onto the components. This avoids look-ahead bias.
            pc_scores = {f"PC{i+1}": [] for i in range(n_pcs_actual)}
            pc_dates = []
            last_loadings = None
            last_explained = None

            # For sign consistency: flip PCs if their loading on the first
            # indicator changes sign relative to the previous window.
            prev_signs = None

            for t in range(pca_window, len(ind_df)):
                window_data = ind_df.iloc[t - pca_window : t].values
                # Standardize within window
                mu = window_data.mean(axis=0)
                sigma = window_data.std(axis=0)
                sigma[sigma == 0] = 1.0
                window_std = (window_data - mu) / sigma

                pca = PCA(n_components=n_pcs_actual)
                pca.fit(window_std)

                # Project current observation
                current = ind_df.iloc[t].values
                current_std = (current - mu) / sigma
                scores = pca.transform(current_std.reshape(1, -1))[0]

                # Sign consistency: flip PC if dominant loading changed sign
                loadings = pca.components_
                if prev_signs is not None:
                    for i in range(n_pcs_actual):
                        # Use the max-abs loading as reference
                        max_idx = np.argmax(np.abs(loadings[i]))
                        if np.sign(loadings[i, max_idx]) != prev_signs[i]:
                            scores[i] *= -1
                            loadings[i] *= -1

                # Store signs for next iteration
                prev_signs = []
                for i in range(n_pcs_actual):
                    max_idx = np.argmax(np.abs(loadings[i]))
                    prev_signs.append(np.sign(loadings[i, max_idx]))

                for i in range(n_pcs_actual):
                    pc_scores[f"PC{i+1}"].append(scores[i])
                pc_dates.append(ind_df.index[t])

                last_loadings = loadings
                last_explained = pca.explained_variance_ratio_

            pc_df = pd.DataFrame(pc_scores, index=pc_dates)

            # --- Variance Explained ---
            st.markdown("---")
            st.markdown("#### Variance Explained (latest window)")
            var_labels = [f"PC{i+1}" for i in range(n_pcs_actual)]
            cum_var = np.cumsum(last_explained) * 100

            fig_var = go.Figure()
            fig_var.add_trace(go.Bar(
                x=var_labels,
                y=last_explained * 100,
                marker_color=ACCENT,
                text=[f"{v:.1f}%" for v in last_explained * 100],
                textposition="outside",
                name="Individual",
            ))
            fig_var.add_trace(go.Scatter(
                x=var_labels,
                y=cum_var,
                mode="lines+markers",
                line=dict(color=GREEN, width=2),
                marker=dict(size=8),
                name="Cumulative",
            ))
            _apply_layout(fig_var, "Variance Explained by Principal Component",
                           f"Total explained: {cum_var[-1]:.1f}% | {ind_df.shape[1]} indicators", 380)
            fig_var.update_layout(
                yaxis_title="Variance Explained (%)",
                yaxis_range=[0, max(100, cum_var[-1] + 5)],
                legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
            )
            st.plotly_chart(fig_var, use_container_width=True)

            # --- Factor Loadings Heatmap ---
            st.markdown("#### Factor Loadings (latest window)")
            st.caption(
                "Each cell shows how much an indicator contributes to a PC. "
                "Large absolute values = strong influence. Sign determines direction."
            )

            loadings_df = pd.DataFrame(
                last_loadings,
                index=var_labels,
                columns=indicator_names,
            )
            # Sort columns by max absolute loading on PC1 for readability
            col_order = loadings_df.loc["PC1"].abs().sort_values(ascending=False).index.tolist()
            loadings_df = loadings_df[col_order]

            # Show top 20 indicators by max loading across any PC
            max_load_per_ind = loadings_df.abs().max(axis=0).sort_values(ascending=False)
            top_inds = max_load_per_ind.head(20).index.tolist()
            loadings_show = loadings_df[top_inds]

            fig_heat = go.Figure(data=go.Heatmap(
                z=loadings_show.values,
                x=loadings_show.columns.tolist(),
                y=loadings_show.index.tolist(),
                colorscale="RdBu_r",
                zmid=0,
                text=[[f"{v:.2f}" for v in row] for row in loadings_show.values],
                texttemplate="%{text}",
                textfont=dict(size=9),
                hovertemplate="PC: %{y}<br>Indicator: %{x}<br>Loading: %{z:.3f}<extra></extra>",
            ))
            _apply_layout(fig_heat, "Factor Loadings Heatmap",
                           f"Top 20 indicators by max loading | {n_pcs_actual} PCs",
                           max(400, n_pcs_actual * 45))
            fig_heat.update_layout(
                xaxis=dict(tickangle=45, tickfont=dict(size=9)),
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig_heat, use_container_width=True)

            # --- PC Interpretation ---
            with st.expander("PC Interpretation (top 5 loadings per PC)"):
                for i in range(n_pcs_actual):
                    pc_name = f"PC{i+1}"
                    loads = loadings_df.loc[pc_name].sort_values(key=abs, ascending=False)
                    top5 = loads.head(5)
                    desc_parts = []
                    for ind_name, load_val in top5.items():
                        direction = "+" if load_val > 0 else "-"
                        desc_parts.append(f"{direction}{ind_name} ({load_val:.2f})")
                    st.markdown(
                        f"**{pc_name}** ({last_explained[i]*100:.1f}% var): "
                        f"{', '.join(desc_parts)}"
                    )

            # --- IC Analysis for each PC ---
            st.markdown("---")
            st.markdown(f"#### PC Predictive Power — {pca_horizon} Forward Returns")

            fwd = analysis["fwd_returns"].get(pca_horizon)
            if fwd is None:
                st.warning("Forward returns not available.")
            else:
                pc_ic_results = []
                for pc_name in pc_df.columns:
                    pc_series = pc_df[pc_name]
                    ic_val, ic_pval = compute_ic(pc_series, fwd)
                    ric = compute_rolling_ic(pc_series, fwd, rolling_ic_win)
                    stab = compute_ic_stability(ric, ic_val)
                    hr = compute_hit_rate(pc_series, fwd)
                    qdf = compute_quintile_returns(pc_series, fwd)
                    mono = compute_monotonicity(qdf)
                    comp = compute_composite_score(ic_val, stab, hr)

                    pc_ic_results.append({
                        "PC": pc_name,
                        "IC": ic_val,
                        "p-value": ic_pval,
                        "Stability": stab,
                        "Hit Rate": hr,
                        "Monotonicity": mono,
                        "Composite": comp,
                        "rolling_ic": ric,
                        "quintile_df": qdf,
                    })

                # Summary table
                summary_df = pd.DataFrame([{
                    "PC": r["PC"],
                    "IC": f"{r['IC']:+.4f}" if not np.isnan(r["IC"]) else "-",
                    "p-value": f"{r['p-value']:.4f}" if not np.isnan(r["p-value"]) else "-",
                    "Stability": f"{r['Stability']:.1%}" if not np.isnan(r["Stability"]) else "-",
                    "Hit Rate": f"{r['Hit Rate']:.1%}" if not np.isnan(r["Hit Rate"]) else "-",
                    "Monotonicity": f"{r['Monotonicity']:+.3f}" if not np.isnan(r["Monotonicity"]) else "-",
                    "Composite": f"{r['Composite']:.4f}" if not np.isnan(r["Composite"]) else "-",
                } for r in pc_ic_results])
                st.dataframe(summary_df, use_container_width=True, hide_index=True)

                # Top PC metrics
                valid_pcs = [r for r in pc_ic_results if not np.isnan(r["IC"])]
                if valid_pcs:
                    best_pc = max(valid_pcs, key=lambda r: abs(r["IC"]))
                    mc1, mc2, mc3, mc4 = st.columns(4)
                    mc1.metric("Best PC", best_pc["PC"])
                    mc2.metric("Best IC", f"{best_pc['IC']:+.4f}")
                    mc3.metric("Stability", f"{best_pc['Stability']:.1%}")
                    mc4.metric("Total Var Explained", f"{cum_var[-1]:.1f}%")

                # --- Rolling IC for top PCs ---
                st.markdown("#### Rolling IC — Top PCs")
                # Plot rolling IC for top 3 PCs by |IC|
                top3_pcs = sorted(valid_pcs, key=lambda r: abs(r["IC"]), reverse=True)[:3]

                fig_pca_ric = go.Figure()
                pc_colors = [ACCENT, GREEN, PURPLE, YELLOW, RED]
                for idx, r in enumerate(top3_pcs):
                    ric = r["rolling_ic"]
                    if not ric.empty:
                        fig_pca_ric.add_trace(go.Scatter(
                            x=ric.index, y=ric.values,
                            mode="lines",
                            line=dict(color=pc_colors[idx % len(pc_colors)], width=1.5),
                            name=f"{r['PC']} (IC={r['IC']:+.3f})",
                        ))
                fig_pca_ric.add_hline(y=0, line_color="rgba(139,148,158,0.5)")
                _apply_layout(fig_pca_ric, "Rolling IC of Top Principal Components",
                               f"{rolling_ic_win}-period rolling Spearman IC vs {pca_horizon} forward {target_index} returns",
                               400)
                fig_pca_ric.update_layout(yaxis_title="Spearman IC")
                st.plotly_chart(fig_pca_ric, use_container_width=True)

                # --- Quintile Returns for best PC ---
                if best_pc["quintile_df"] is not None and not best_pc["quintile_df"].empty:
                    st.markdown(f"#### Quintile Returns — {best_pc['PC']}")
                    qdf_best = best_pc["quintile_df"]
                    fig_pq = go.Figure()
                    bar_colors = [
                        QUINTILE_COLORS[int(q) - 1] if int(q) <= len(QUINTILE_COLORS) else ACCENT
                        for q in qdf_best["Quintile"]
                    ]
                    fig_pq.add_trace(go.Bar(
                        x=[f"Q{int(q)}" for q in qdf_best["Quintile"]],
                        y=qdf_best["Mean Return"] * 100,
                        marker_color=bar_colors,
                        text=[f"{v*100:.2f}%" for v in qdf_best["Mean Return"]],
                        textposition="outside",
                    ))
                    _apply_layout(fig_pq, f"Quintile Returns: {best_pc['PC']}",
                                   f"Mean {pca_horizon} forward {target_index} return by {best_pc['PC']} quintile",
                                   380)
                    fig_pq.update_layout(
                        yaxis_title="Mean Forward Return (%)",
                        showlegend=False,
                    )
                    st.plotly_chart(fig_pq, use_container_width=True)

                # --- PCA Composite Signal & Backtest ---
                st.markdown("---")
                st.subheader("PCA Composite Signal & Backtest")
                st.markdown(
                    "Combine predictive PCs (|IC| > 0.05) into an IC-weighted composite signal, "
                    "then run the same allocation backtest as the Multi-Indicator tab."
                )

                # Build composite from PCs with |IC| > 0.05
                predictive_pcs = [r for r in valid_pcs if abs(r["IC"]) > 0.05]
                if not predictive_pcs:
                    st.warning("No PCs with |IC| > 0.05. Try different settings.")
                else:
                    # IC-weighted composite of PCs
                    composite_parts = {}
                    weights = {}
                    for r in predictive_pcs:
                        pc_name = r["PC"]
                        ic_val = r["IC"]
                        # Flip PC direction based on IC sign
                        composite_parts[pc_name] = pc_df[pc_name] * np.sign(ic_val)
                        weights[pc_name] = abs(ic_val)

                    pca_comp_df = pd.DataFrame(composite_parts).dropna()
                    if not pca_comp_df.empty:
                        total_w = sum(weights.values())
                        pca_composite = sum(
                            pca_comp_df[name] * (w / total_w)
                            for name, w in weights.items()
                        )
                        pca_composite.name = "PCA_Composite"

                        # Composite IC
                        pca_comp_ic, pca_comp_pval = compute_ic(pca_composite, fwd)
                        pca_comp_ric = compute_rolling_ic(pca_composite, fwd, rolling_ic_win)
                        pca_comp_stab = compute_ic_stability(pca_comp_ric, pca_comp_ic)
                        pca_comp_hr = compute_hit_rate(pca_composite, fwd)
                        pca_comp_qdf = compute_quintile_returns(pca_composite, fwd)
                        pca_comp_mono = compute_monotonicity(pca_comp_qdf)

                        st.markdown(f"**PCA Composite:** {len(predictive_pcs)} PCs, IC-weighted")
                        pm1, pm2, pm3, pm4, pm5 = st.columns(5)
                        pm1.metric("Composite IC", f"{pca_comp_ic:+.4f}" if not np.isnan(pca_comp_ic) else "-")
                        pm2.metric("p-value", f"{pca_comp_pval:.4f}" if not np.isnan(pca_comp_pval) else "-")
                        pm3.metric("Stability", f"{pca_comp_stab:.1%}" if not np.isnan(pca_comp_stab) else "-")
                        pm4.metric("Hit Rate", f"{pca_comp_hr:.1%}" if not np.isnan(pca_comp_hr) else "-")
                        pm5.metric("Monotonicity", f"{pca_comp_mono:+.3f}" if not np.isnan(pca_comp_mono) else "-")

                        # Composite rolling IC
                        if not pca_comp_ric.empty:
                            fig_pcric = go.Figure()
                            fig_pcric.add_trace(go.Scatter(
                                x=pca_comp_ric.index, y=pca_comp_ric.values,
                                mode="lines", fill="tozeroy",
                                line=dict(color=PURPLE, width=1.5),
                                fillcolor="rgba(188,140,255,0.15)",
                            ))
                            fig_pcric.add_hline(y=0, line_color="rgba(139,148,158,0.5)")
                            fig_pcric.add_hline(
                                y=pca_comp_ic, line_dash="dash", line_color=GREEN,
                                annotation_text=f"Full IC: {pca_comp_ic:.3f}",
                            )
                            _apply_layout(fig_pcric, "PCA Composite Rolling IC",
                                           f"{rolling_ic_win}-period rolling Spearman IC", 380)
                            fig_pcric.update_layout(showlegend=False)
                            st.plotly_chart(fig_pcric, use_container_width=True)

                        # --- Backtest ---
                        acwi_weekly = analysis["acwi_resampled"]
                        acwi_ret = acwi_weekly.pct_change().dropna()

                        signal_lagged = pca_composite.shift(1)
                        signal_pctile = signal_lagged.rolling(
                            zscore_win, min_periods=zscore_win // 2
                        ).apply(
                            lambda x: sp_stats.percentileofscore(x[:-1], x[-1]) / 100.0
                            if len(x) > 1 else 0.5,
                            raw=True,
                        )
                        eq_weight = (0.10 + signal_pctile * 0.80).clip(0.10, 0.90)

                        bt_df = pd.concat({
                            "idx_ret": acwi_ret,
                            "eq_weight": eq_weight,
                        }, axis=1).dropna()

                        if len(bt_df) > 52:
                            bt_df["strategy_ret"] = bt_df["eq_weight"] * bt_df["idx_ret"]
                            bt_df["benchmark_ret"] = 0.50 * bt_df["idx_ret"]
                            bt_df["strategy_cum"] = (1 + bt_df["strategy_ret"]).cumprod()
                            bt_df["benchmark_cum"] = (1 + bt_df["benchmark_ret"]).cumprod()
                            bt_df["idx_cum"] = (1 + bt_df["idx_ret"]).cumprod()

                            ann_factor = 52
                            n_years = len(bt_df) / ann_factor
                            strat_ann = bt_df["strategy_cum"].iloc[-1] ** (1 / n_years) - 1
                            bench_ann = bt_df["benchmark_cum"].iloc[-1] ** (1 / n_years) - 1
                            strat_vol = bt_df["strategy_ret"].std() * np.sqrt(ann_factor)
                            bench_vol = bt_df["benchmark_ret"].std() * np.sqrt(ann_factor)
                            strat_sharpe = strat_ann / strat_vol if strat_vol > 0 else 0
                            bench_sharpe = bench_ann / bench_vol if bench_vol > 0 else 0

                            def _max_dd(cum):
                                return (cum / cum.expanding().max() - 1).min()

                            strat_mdd = _max_dd(bt_df["strategy_cum"])
                            bench_mdd = _max_dd(bt_df["benchmark_cum"])
                            excess = bt_df["strategy_ret"] - bt_df["benchmark_ret"]
                            te = excess.std() * np.sqrt(ann_factor)
                            ir = (strat_ann - bench_ann) / te if te > 0 else 0

                            st.markdown("#### PCA Backtest Performance")
                            bm1, bm2, bm3, bm4 = st.columns(4)
                            bm1.metric("Strategy Ann Return", f"{strat_ann:.1%}",
                                       f"vs Bench {bench_ann:.1%}")
                            bm2.metric("Strategy Sharpe", f"{strat_sharpe:.2f}",
                                       f"vs Bench {bench_sharpe:.2f}")
                            bm3.metric("Max Drawdown", f"{strat_mdd:.1%}",
                                       f"vs Bench {bench_mdd:.1%}")
                            bm4.metric("Information Ratio", f"{ir:.2f}")

                            bm5, bm6, bm7, bm8 = st.columns(4)
                            bm5.metric("Strategy Volatility", f"{strat_vol:.1%}")
                            bm6.metric("Tracking Error", f"{te:.1%}")
                            bm7.metric("Weekly Hit Rate", f"{(excess > 0).mean():.1%}")
                            bm8.metric("Avg Equity Weight", f"{bt_df['eq_weight'].mean():.0%}")

                            # Cumulative return chart
                            fig_pbt = go.Figure()
                            fig_pbt.add_trace(go.Scatter(
                                x=bt_df.index, y=bt_df["strategy_cum"],
                                name="PCA Strategy", line=dict(color=GREEN, width=2),
                            ))
                            fig_pbt.add_trace(go.Scatter(
                                x=bt_df.index, y=bt_df["benchmark_cum"],
                                name="50% Benchmark", line=dict(color=MUTED, width=1.5, dash="dash"),
                            ))
                            fig_pbt.add_trace(go.Scatter(
                                x=bt_df.index, y=bt_df["idx_cum"],
                                name=f"100% {target_index}",
                                line=dict(color=ACCENT, width=1, dash="dot"),
                                opacity=0.6,
                            ))
                            _apply_layout(fig_pbt, "PCA Strategy Cumulative Returns",
                                           f"Strategy vs 50% Benchmark vs 100% {target_index}", 450)
                            fig_pbt.update_layout(yaxis_title="Growth of $1")
                            st.plotly_chart(fig_pbt, use_container_width=True)

                            # Equity weight
                            fig_pwt = go.Figure()
                            fig_pwt.add_trace(go.Scatter(
                                x=bt_df.index, y=bt_df["eq_weight"] * 100,
                                mode="lines", fill="tozeroy",
                                line=dict(color=ACCENT, width=1),
                                fillcolor="rgba(88,166,255,0.2)",
                            ))
                            fig_pwt.add_hline(y=50, line_dash="dash", line_color=MUTED,
                                              annotation_text="50% Benchmark")
                            _apply_layout(fig_pwt, "PCA Signal — Equity Weight Over Time",
                                           "Composite PCA signal-driven allocation (10%-90%)", 300)
                            fig_pwt.update_layout(
                                yaxis_title="Equity Weight (%)",
                                yaxis_range=[0, 100],
                                showlegend=False,
                            )
                            st.plotly_chart(fig_pwt, use_container_width=True)

                            # Drawdown comparison
                            strat_dd = bt_df["strategy_cum"] / bt_df["strategy_cum"].expanding().max() - 1
                            bench_dd = bt_df["benchmark_cum"] / bt_df["benchmark_cum"].expanding().max() - 1
                            fig_pdd = go.Figure()
                            fig_pdd.add_trace(go.Scatter(
                                x=strat_dd.index, y=strat_dd.values * 100,
                                name="PCA Strategy", fill="tozeroy",
                                line=dict(color=RED, width=1),
                                fillcolor="rgba(248,81,73,0.2)",
                            ))
                            fig_pdd.add_trace(go.Scatter(
                                x=bench_dd.index, y=bench_dd.values * 100,
                                name="Benchmark", line=dict(color=MUTED, width=1, dash="dash"),
                            ))
                            _apply_layout(fig_pdd, "Drawdown Comparison",
                                           "PCA strategy vs 50% benchmark", 350)
                            fig_pdd.update_layout(yaxis_title="Drawdown (%)")
                            st.plotly_chart(fig_pdd, use_container_width=True)
                        else:
                            st.warning("Insufficient data for PCA backtest (need >52 periods).")
                    else:
                        st.warning("Could not align PCA composite data.")


# ===========================================================================
# TAB 7: METHODOLOGY
# ===========================================================================

with tab_method:
    st.subheader("Methodology")

    st.markdown("""
### Objective

This app tests whether **liquidity conditions** -- as measured by central bank balance sheets,
money supply, credit conditions, financial conditions indices, and related indicators --
have statistically significant **predictive power** for forward equity index returns.

The target variable is **forward simple returns** of the selected equity index at horizons
of 1 month (~4 weeks), 3 months (~13 weeks), 6 months (~26 weeks), and 12 months (~52 weeks).

---

### Why Liquidity Matters for Equity Returns

Liquidity conditions affect equity markets through multiple transmission channels:

1. **Portfolio Rebalancing Channel**: When central banks purchase assets (QE), they push
   investors out the risk curve into equities. When they drain liquidity (QT), the
   reverse happens.

2. **Credit Channel**: Easier financial conditions lower the cost of capital for
   corporations, supporting earnings growth and equity valuations (P/E expansion).

3. **Risk Premium Channel**: Abundant liquidity compresses risk premia (including the
   equity risk premium), pushing up asset prices. Liquidity withdrawal has the opposite effect.

4. **Money Supply Channel**: Excess money creation (M2 growth exceeding real GDP growth)
   flows into financial assets. This is sometimes called the "liquidity tide."

5. **Global Dollar Liquidity**: The US dollar is the world's reserve currency. When dollar
   liquidity is ample (weak DXY, QE), global risk assets rally. Dollar shortages
   (strong DXY, QT) create headwinds for global equities.

---

### Statistical Methods

**1. Information Coefficient (IC)**

The primary metric is the Spearman rank correlation between each indicator (z-scored)
and forward N-period index returns. Spearman is preferred over Pearson because:
- It captures monotonic (not just linear) relationships
- It is robust to outliers, which are common in both macro data and equity returns
- It makes no distributional assumptions

**2. IC Stability**

The fraction of rolling windows where the IC sign matches the full-sample IC sign.
An indicator with IC = +0.10 but stability = 50% is just noise -- the relationship
randomly flips. We want stability > 60%, ideally > 70%.

**3. Rolling IC**

Time series of the rolling IC, which reveals whether the signal is stable or decaying
over time. A once-strong signal that has lost power in recent years is less useful
than one with consistent IC across regimes.

**4. Quintile Analysis**

Periods are sorted into quintiles (Q1-Q5) by indicator z-score. We compute the mean
forward return in each quintile. A good predictor shows **monotonic** returns across
quintiles -- Q5 should consistently have higher (or lower) returns than Q1.

The **monotonicity score** is the Spearman correlation between quintile rank and mean
return. Values near +1 or -1 indicate strong monotonic relationships.

**5. Hit Rate**

The fraction of periods where the sign of the indicator z-score correctly predicts
the sign of the forward return. 50% = random. >55% is meaningful for macro signals.
Note: hit rate can be misleading for asymmetric signals (e.g., indicators that only
matter in extreme readings).

**6. Univariate Regression**

Standard OLS regression of forward returns on the indicator z-score. We report R-squared,
beta coefficient, t-statistic, and p-value. In macro predictive regressions, R-squared
above 2-3% is considered meaningful at the quarterly horizon.

**7. Composite Score**

A weighted combination: **50% |IC| + 30% Stability + 20% Hit Rate**. This balances
signal strength (IC magnitude), reliability (stability), and practical usefulness
(directional accuracy).

---

### Z-Score Normalization

All indicators are z-scored using a **rolling window** (default: 104 weeks = 2 years)
before analysis. This ensures:
- All indicators are on the same scale for fair comparison
- The analysis captures *relative* indicator readings, not absolute levels
- It mimics how a practitioner would use these indicators in real time
- It avoids look-ahead bias (expanding window or full-sample z-scoring would leak information)

---

### Composite Signal Construction

The multi-indicator composite selects the top-N indicators by composite score and
combines them using either:

- **IC-Weighted**: Each indicator is weighted proportional to its |IC| with the sign
  preserved. This gives more weight to stronger predictors.
- **Equal-Weighted**: Each indicator gets equal weight, with the sign determined by IC
  direction. More robust to estimation error but ignores signal strength differences.

Indicator series are directionally aligned (flipped based on IC sign) before averaging,
so that a positive composite always means "bullish for forward returns."

---

### Backtest Methodology

- **Benchmark**: 50% equity / 50% cash
- **Signal mapping**: The composite signal's **percentile rank** (rolling, using same
  z-score window) maps linearly to equity weights: 0th percentile = 10% equity,
  100th percentile = 90% equity
- **Lag**: Signal is lagged by 1 period to prevent look-ahead bias
- **No transaction costs**: This is a research tool, not a production backtest.
  Rebalancing is weekly but turnover is typically low (smooth signal)
- **No leverage**: Equity weight is capped at [10%, 90%]

---

### Limitations

1. **In-sample selection**: While individual ICs are computed on the full sample,
   the ranking and composite construction use full-sample metrics. A true out-of-sample
   test would use expanding windows for indicator selection -- not implemented here.

2. **Publication lag**: Some indicators (M2, credit, China data) are published with
   a 4-8 week lag. We do NOT adjust for this in the current analysis, which slightly
   overstates the practical IC.

3. **Survivorship bias**: We only test indicators that are available today. Indicators
   that were once popular but lost data coverage are excluded.

4. **Regime dependence**: IC values can vary substantially across monetary regimes
   (ZIRP vs normal rates). The rolling IC chart helps identify this.

5. **Correlation among indicators**: Many liquidity indicators are correlated with
   each other. The composite may not add as much diversification as the indicator
   count suggests.

---

### Data Sources

All data sourced from the Investment-X database, which aggregates from FRED,
Bloomberg, and computed custom indicators. Equity indices are loaded from the database
with yfinance as fallback.
""")


# ===========================================================================
# Update agent memory with key findings
# ===========================================================================
# (No runtime memory writes -- this section documents the structure for reference)
