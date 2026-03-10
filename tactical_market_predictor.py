"""
Tactical Indicators -> Forward Equity Return Predictor
=======================================================
Which tactical/short-term indicators best predict forward equity returns?

Tests a comprehensive set of tactical indicators (volatility structure,
credit stress, sentiment, positioning, cross-asset regime, nowcasting, etc.)
against forward 1m/3m/6m/12m returns for a user-selected equity index
using IC analysis, quintile decomposition, rolling IC stability, and regression.

Run with:  streamlit run tactical_market_predictor.py
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
    page_title="Tactical -> Equity Return Predictor",
    page_icon="\u26a1",
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

QUINTILE_COLORS = ["#f85149", "#d29922", "#8b949e", "#58a6ff", "#3fb950"]
CATEGORY_COLORS = {
    "Volatility Structure": "#f85149",
    "Credit Stress": "#d29922",
    "Sentiment & Positioning": "#e3b341",
    "Cross-Asset Regime": "#58a6ff",
    "Risk Appetite": "#bc8cff",
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
# "invert": if True, negate before narrative (the IC is always raw).

def _build_indicator_registry() -> List[Tuple[str, Callable, str, str, bool]]:
    """Build the full registry of tactical indicators.

    IMPORTANT: This registry deliberately EXCLUDES indicators that overlap
    with the Growth, Inflation, or Liquidity axes in ix/core/macro/indicators.py.
    Removed overlaps:
      Growth:     CESI Breadth/Momentum, Baltic Dry, SOX, Momentum, Nowcasting, Earnings
      Inflation:  10Y Breakeven
      Liquidity:  FCI US, US 10Y Real, US 2s10s, Leveraged Loan, Credit Conditions,
                  Credit Stress Index (has curve component)
    """
    from ix.db.custom import (
        # Tactical core (all 12 from TACTICAL_LOADERS)
        risk_appetite,
        fci_stress,
        vix,
        put_call_zscore,
        risk_on_off_breadth,
        credit_equity_divergence,
        vix_realized_vol_spread,
        hy_spread,
        hy_ig_ratio,
        erp_zscore,
        dollar_index,
        us_sector_breadth,
        # Additional credit
        ig_spread,
    )
    from ix.db.custom.volatility import (
        vix_term_structure,
        vix_term_spread,
        skew_index,
        skew_zscore,
        vol_risk_premium_zscore,
        vvix_vix_ratio,
        gamma_exposure_proxy,
        realized_vol_regime,
    )
    from ix.db.custom.correlation_regime import (
        equity_bond_corr_zscore,
        safe_haven_demand,
        tail_risk_index,
        cross_asset_correlation_fast,
        diversification_index,
        correlation_surprise,
    )
    from ix.db.custom.credit_deep import (
        hy_spread_momentum,
        hy_spread_velocity,
        ig_hy_compression,
    )
    from ix.db.custom.fund_flows import (
        margin_debt_yoy,
        equity_bond_flow_ratio,
        risk_rotation_index,
    )

    registry = [
        # --- Volatility Structure (10) ---
        ("VIX", lambda: vix(freq="W"), "Volatility Structure",
         "CBOE Volatility Index. Contrarian: spikes = oversold = bullish.", False),
        ("VIX Term Structure", vix_term_structure, "Volatility Structure",
         "VIX/VIX3M ratio. >1 = backwardation = acute stress.", False),
        ("VIX Term Spread", vix_term_spread, "Volatility Structure",
         "VIX3M minus VIX in vol points. Negative = backwardation.", False),
        ("VIX-Realized Vol", vix_realized_vol_spread, "Volatility Structure",
         "VIX minus SPX realized vol. Positive = fear premium (contrarian bullish).", False),
        ("Vol Risk Premium Z", vol_risk_premium_zscore, "Volatility Structure",
         "Z-score of VIX/realized vol ratio. Extreme = mean-reversion likely.", False),
        ("SKEW Index", skew_index, "Volatility Structure",
         "CBOE SKEW. High = tail risk priced in. Contrarian bullish.", False),
        ("SKEW Z-Score", skew_zscore, "Volatility Structure",
         "Rolling z-score of SKEW index.", False),
        ("VVIX/VIX Ratio", vvix_vix_ratio, "Volatility Structure",
         "Vol-of-vol normalized. High = dealer uncertainty.", False),
        ("Gamma Exposure Proxy", gamma_exposure_proxy, "Volatility Structure",
         "Combined dealer gamma (VIX TS + put/call). Positive = vol-suppression.", False),
        ("Realized Vol Regime", realized_vol_regime, "Volatility Structure",
         "Short-term/long-term realized vol ratio. >1 = vol expansion.", True),

        # --- Credit Stress (8) ---
        ("HY Spread", hy_spread, "Credit Stress",
         "ICE BofA US HY OAS. Wider = stress.", True),
        ("IG Spread", ig_spread, "Credit Stress",
         "ICE BofA US IG OAS.", True),
        ("HY/IG Ratio", hy_ig_ratio, "Credit Stress",
         "HY-to-IG spread ratio. Rises in stress.", True),
        ("HY Spread Momentum", lambda: hy_spread_momentum(), "Credit Stress",
         "HY spread 60-day change (bps). Positive = widening.", True),
        ("HY Spread Velocity", lambda: hy_spread_velocity(), "Credit Stress",
         "Acceleration of HY spread widening. Panic detection.", True),
        ("IG/HY Compression", ig_hy_compression, "Credit Stress",
         "IG/HY ratio. Rising = spread compression = risk appetite.", False),
        ("FCI Stress", fci_stress, "Credit Stress",
         "Financial stress (VIX + MOVE + spreads). Higher = stress.", True),
        ("Credit-Equity Div", credit_equity_divergence, "Credit Stress",
         "SPX momentum vs HY momentum divergence. Negative = dangerous.", True),

        # --- Sentiment & Positioning (5) ---
        ("Put/Call Z-Score", put_call_zscore, "Sentiment & Positioning",
         "Rolling z-score of put/call ratio. High = fear = contrarian bullish.", False),
        ("ERP Z-Score", lambda: erp_zscore(), "Sentiment & Positioning",
         "SPX equity risk premium z-score. Extreme high = cheap.", False),
        ("Margin Debt YoY", margin_debt_yoy, "Sentiment & Positioning",
         "FINRA margin debt YoY growth. Leverage cycle.", False),
        ("Equity/Bond Flow Proxy", lambda: equity_bond_flow_ratio(), "Sentiment & Positioning",
         "SPY/TLT relative momentum. Flow rotation proxy.", False),
        ("Risk Rotation Index", risk_rotation_index, "Sentiment & Positioning",
         "SPY/TLT + HY/IG + Russell/SPX rotation composite.", False),

        # --- Cross-Asset Regime (8) ---
        ("Risk On/Off Breadth", risk_on_off_breadth, "Cross-Asset Regime",
         "% of 6 cross-asset signals in risk-on mode.", False),
        ("Eq/Bond Corr Z", equity_bond_corr_zscore, "Cross-Asset Regime",
         "Equity-bond correlation z-score. Regime change detector.", False),
        ("Safe Haven Demand", safe_haven_demand, "Cross-Asset Regime",
         "Gold + Treasury strength vs equities. Rising = risk-off.", True),
        ("Tail Risk Index", tail_risk_index, "Cross-Asset Regime",
         "Composite: VIX + skew + spreads + eq-bond corr.", True),
        ("Cross-Asset Corr", cross_asset_correlation_fast, "Cross-Asset Regime",
         "Avg absolute correlation across major assets. High = crisis.", True),
        ("Diversification Index", diversification_index, "Cross-Asset Regime",
         "Inverse of cross-asset correlation. Low = dangerous.", False),
        ("Correlation Surprise", correlation_surprise, "Cross-Asset Regime",
         "Short-term vs long-term correlation deviation. Regime shift.", False),
        ("Dollar Index", lambda: dollar_index(freq="W"), "Cross-Asset Regime",
         "DXY. Strong dollar = tighter global conditions.", True),

        # --- Risk Appetite (2) ---
        ("Risk Appetite", lambda: risk_appetite(), "Risk Appetite",
         "Inverted avg z-score of vol + spreads. Higher = more appetite.", False),
        ("US Sector Breadth", us_sector_breadth, "Risk Appetite",
         "% of US GICS sectors outperforming SPX. High = healthy.", False),
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
    "ACWI": "ACWI", "S&P 500": "^GSPC", "DAX": "^GDAXI",
    "Nikkei 225": "^N225", "KOSPI": "^KS11", "Nifty 50": "^NSEI",
    "Hang Seng": "^HSI", "Shanghai Comp": "000001.SS",
    "Stoxx 50": "^STOXX50E", "FTSE 100": "^FTSE",
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


@st.cache_data(ttl=3600, show_spinner="Loading tactical indicators...")
def load_all_indicators() -> Dict[str, Tuple[pd.Series, str, str, bool]]:
    """Load all indicators in parallel. Returns {name: (series, category, desc, invert)}."""
    registry = _build_indicator_registry()
    results = {}

    def _load_one(name: str, fn: Callable) -> Tuple[str, pd.Series | None]:
        try:
            raw = fn()
            if isinstance(raw, pd.DataFrame):
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
            if series is not None and len(series) > 200:
                cat, desc, inv = meta[name]
                results[name] = (series, cat, desc, inv)

    return results


def resample_to_freq(s: pd.Series, freq: str) -> pd.Series:
    """Resample to target frequency, forward-filling mixed-frequency gaps."""
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
    """Spearman rank IC between indicator and forward returns."""
    df = pd.concat([indicator, fwd_ret], axis=1).dropna()
    if len(df) < 100:
        return np.nan, np.nan
    corr, pval = sp_stats.spearmanr(df.iloc[:, 0], df.iloc[:, 1])
    return corr, pval


def compute_rolling_ic(
    indicator: pd.Series, fwd_ret: pd.Series, window: int = 52
) -> pd.Series:
    """Rolling Spearman IC over a window."""
    df = pd.concat({"ind": indicator, "ret": fwd_ret}, axis=1).dropna()
    if len(df) < window:
        return pd.Series(dtype=float)
    ind_rank = df["ind"].rolling(window).rank()
    ret_rank = df["ret"].rolling(window).rank()
    ric = ind_rank.rolling(window).corr(ret_rank).dropna()
    ric.name = "Rolling IC"
    return ric


def compute_quintile_returns(indicator: pd.Series, fwd_ret: pd.Series) -> pd.DataFrame:
    """Mean forward return per quintile of indicator level."""
    df = pd.concat({"ind": indicator, "ret": fwd_ret}, axis=1).dropna()
    if len(df) < 50:
        return pd.DataFrame()
    df["Q"] = pd.qcut(df["ind"], 5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"], duplicates="drop")
    return df.groupby("Q", observed=True)["ret"].agg(["mean", "count"]).rename(
        columns={"mean": "Mean Return", "count": "N"}
    )


@st.cache_data(ttl=3600, show_spinner="Running full analysis...")
def run_full_analysis(
    _index_prices: pd.Series,
    _indicators: Dict,
    freq: str,
    zscore_window: int,
    rolling_ic_window: int,
    index_name: str = "ACWI",
) -> Dict:
    """Run complete IC analysis across all indicators and horizons."""
    price = resample_to_freq(_index_prices, freq)

    results = {}
    for horizon_label, n_periods in HORIZON_MAP.items():
        fwd = compute_forward_returns(price, n_periods)
        horizon_results = {}

        for name, (raw_series, cat, desc, invert) in _indicators.items():
            ind = resample_to_freq(raw_series, freq)
            if len(ind) < 52:
                continue

            z = rolling_zscore(ind, zscore_window)
            if len(z) < 52:
                continue

            ic, pval = compute_ic(z, fwd)
            if np.isnan(ic):
                continue

            ric = compute_rolling_ic(z, fwd, rolling_ic_window)
            stability = (ric > 0).mean() if len(ric) > 10 else np.nan
            hit_rate = np.nan
            mono = np.nan

            qr = compute_quintile_returns(z, fwd)
            if not qr.empty and len(qr) == 5:
                means = qr["Mean Return"].values
                hit_rate = np.mean(
                    [
                        means[-1] > means[0],
                        means[-1] > means[-2] if len(means) > 1 else False,
                        means[0] < means[1] if len(means) > 1 else False,
                    ]
                )
                mono_corr, _ = sp_stats.spearmanr([1, 2, 3, 4, 5], means)
                mono = mono_corr

            composite_score = (
                0.50 * abs(ic)
                + 0.30 * (stability if not np.isnan(stability) else 0.5)
                + 0.20 * (hit_rate if not np.isnan(hit_rate) else 0.5)
            )

            horizon_results[name] = {
                "IC": ic,
                "p-value": pval,
                "|IC|": abs(ic),
                "Stability": stability,
                "Hit Rate": hit_rate,
                "Monotonicity": mono,
                "Composite": composite_score,
                "Category": cat,
                "Description": desc,
                "Invert": invert,
                "N_obs": len(pd.concat([z, fwd], axis=1).dropna()),
                "Start": str(z.index.min().date()) if not z.empty else "",
                "End": str(z.index.max().date()) if not z.empty else "",
            }

        results[horizon_label] = horizon_results

    return results


# ===========================================================================
# SIDEBAR
# ===========================================================================

target_index = st.sidebar.selectbox(
    "Target Index", list(INDEX_MAP.keys()), index=0,
    help="Equity index to predict forward returns for.",
)

st.sidebar.markdown(f"## \u26a1 Tactical \u2192 {target_index} Returns")
st.sidebar.markdown(
    f"**Target:** Forward {target_index} returns\n\n"
    "**Indicators:** Tactical/short-term"
)
st.sidebar.divider()

horizon_choice = st.sidebar.selectbox(
    "Forward Return Horizon",
    list(HORIZON_MAP.keys()),
    index=1,
    help="How far forward to measure returns",
)
freq_choice = st.sidebar.selectbox(
    "Resample Frequency",
    list(FREQ_MAP.keys()),
    help="Frequency for analysis",
)
zscore_window = st.sidebar.slider(
    "Z-Score Window (periods)",
    52, 208, 104,
    help="Lookback for z-score normalization",
)
rolling_ic_window = st.sidebar.slider(
    "Rolling IC Window (periods)",
    26, 104, 52,
    help="Lookback for rolling IC computation",
)

freq = FREQ_MAP[freq_choice]
n_periods = HORIZON_MAP[horizon_choice]

# ===========================================================================
# DATA LOADING
# ===========================================================================

index_prices = load_index(target_index)
if index_prices.empty:
    st.error(f"Could not load {target_index} price data.")
    st.stop()

indicators = load_all_indicators()
if not indicators:
    st.error("No indicators loaded successfully.")
    st.stop()

st.sidebar.success(f"Loaded {len(indicators)} indicators")

# ===========================================================================
# MAIN ANALYSIS
# ===========================================================================

analysis = run_full_analysis(
    index_prices, indicators, freq, zscore_window, rolling_ic_window,
    index_name=target_index,
)

horizon_data = analysis.get(horizon_choice, {})
if not horizon_data:
    st.warning(f"No results for {horizon_choice} horizon.")
    st.stop()

# ===========================================================================
# TABS
# ===========================================================================

tab_rank, tab_deep, tab_multi, tab_roll, tab_pca, tab_method = st.tabs(
    ["\U0001f3c6 Rankings", "\U0001f50d Deep Dive", "\U0001f9e9 Multi-Indicator Model",
     "\U0001f4c8 Rolling IC", "\U0001f9ec PCA Factors", "\U0001f4d6 Methodology"]
)

# ---- TAB: RANKINGS ----
with tab_rank:
    st.header(f"Tactical Indicator Rankings \u2014 {horizon_choice} Forward {target_index} Returns")

    ranking_df = pd.DataFrame(horizon_data).T
    ranking_df = ranking_df.sort_values("Composite", ascending=False)

    # Summary metrics
    top3 = ranking_df.head(3)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Top Indicator", top3.index[0] if len(top3) > 0 else "-")
    col2.metric("Best IC", f"{top3['IC'].iloc[0]:+.4f}" if len(top3) > 0 else "-")
    col3.metric("Avg |IC|", f"{ranking_df['|IC|'].mean():.4f}")
    col4.metric("Indicators Loaded", str(len(ranking_df)))

    # Full table
    display_cols = ["IC", "p-value", "|IC|", "Stability", "Hit Rate",
                    "Monotonicity", "Composite", "Category", "N_obs", "Start", "End"]
    fmt = {
        "IC": "{:+.4f}", "p-value": "{:.4f}", "|IC|": "{:.4f}",
        "Stability": "{:.1%}", "Hit Rate": "{:.1%}",
        "Monotonicity": "{:+.3f}", "Composite": "{:.4f}",
        "N_obs": "{:,.0f}",
    }
    st.dataframe(
        ranking_df[display_cols].style.format(fmt, na_rep="-"),
        use_container_width=True,
        height=min(35 * len(ranking_df) + 38, 800),
    )

    # IC by category chart
    st.subheader("IC by Category")
    cat_ic = ranking_df.groupby("Category")["IC"].agg(["mean", "count"])
    cat_ic = cat_ic.sort_values("mean")
    colors = [CATEGORY_COLORS.get(c, MUTED) for c in cat_ic.index]
    fig = go.Figure(go.Bar(
        x=cat_ic["mean"], y=cat_ic.index, orientation="h",
        marker_color=colors,
        text=[f"{v:+.3f} (n={int(n)})" for v, n in zip(cat_ic["mean"], cat_ic["count"])],
        textposition="outside",
    ))
    _apply_layout(fig, "Mean IC by Category",
                  f"Average Spearman IC for {horizon_choice} forward {target_index} returns", 400)
    st.plotly_chart(fig, use_container_width=True)

    # Top / Bottom indicators bar chart
    st.subheader("Top & Bottom Indicators by IC")
    top_n = 15
    ranked = ranking_df.sort_values("IC")
    top_bottom = pd.concat([ranked.head(top_n), ranked.tail(top_n)]).drop_duplicates()
    top_bottom = top_bottom.sort_values("IC")
    colors_tb = [RED if v < 0 else GREEN for v in top_bottom["IC"]]
    fig = go.Figure(go.Bar(
        x=top_bottom["IC"], y=top_bottom.index, orientation="h",
        marker_color=colors_tb,
        text=[f"{v:+.4f}" for v in top_bottom["IC"]],
        textposition="outside",
    ))
    _apply_layout(fig, f"Top & Bottom Indicators",
                  f"Spearman rank IC for {horizon_choice} forward {target_index} returns",
                  max(400, 25 * len(top_bottom)))
    st.plotly_chart(fig, use_container_width=True)


# ---- TAB: DEEP DIVE ----
with tab_deep:
    st.header("Indicator Deep Dive")

    sorted_names = ranking_df.index.tolist()
    selected = st.selectbox("Select Indicator", sorted_names)

    if selected and selected in indicators:
        raw_series, cat, desc, invert = indicators[selected]
        meta = horizon_data.get(selected, {})

        st.markdown(f"**Category:** {cat} | **{desc}**")

        if meta:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("IC", f"{meta['IC']:+.4f}")
            c2.metric("p-value", f"{meta['p-value']:.4f}")
            c3.metric("Stability", f"{meta['Stability']:.1%}" if not np.isnan(meta.get("Stability", np.nan)) else "-")
            c4.metric("Monotonicity", f"{meta['Monotonicity']:+.3f}" if not np.isnan(meta.get("Monotonicity", np.nan)) else "-")

        ind = resample_to_freq(raw_series, freq)
        z = rolling_zscore(ind, zscore_window)
        price = resample_to_freq(index_prices, freq)
        fwd = compute_forward_returns(price, n_periods)

        # Time series chart
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Scatter(x=z.index, y=z.values, name=f"{selected} (z-score)",
                       line=dict(color=ACCENT, width=1.5)),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(x=price.index, y=price.values, name=target_index,
                       line=dict(color=MUTED, width=1, dash="dot")),
            secondary_y=True,
        )
        _apply_layout(fig, f"{selected} vs {target_index}", f"Z-score ({zscore_window}-period rolling)")
        fig.update_yaxes(title_text="Z-Score", secondary_y=False)
        fig.update_yaxes(title_text=target_index, secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)

        # Quintile returns
        qr = compute_quintile_returns(z, fwd)
        if not qr.empty:
            fig = go.Figure(go.Bar(
                x=qr.index, y=qr["Mean Return"] * 100,
                marker_color=QUINTILE_COLORS[:len(qr)],
                text=[f"{v:.2f}%" for v in qr["Mean Return"] * 100],
                textposition="outside",
            ))
            _apply_layout(fig, f"Quintile Returns: {selected}",
                          f"Mean {horizon_choice} forward {target_index} return by {selected} quintile")
            fig.update_yaxes(title_text="Mean Forward Return (%)")
            st.plotly_chart(fig, use_container_width=True)

        # Rolling IC
        ric = compute_rolling_ic(z, fwd, rolling_ic_window)
        if not ric.empty:
            full_ic = meta.get("IC", 0) if meta else 0
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=ric.index, y=ric.values, name="Rolling IC",
                line=dict(color=ACCENT, width=1.5),
                fill="tozeroy", fillcolor="rgba(88,166,255,0.1)",
            ))
            fig.add_hline(y=full_ic, line_dash="dash", line_color=GREEN,
                          annotation_text=f"Full IC: {full_ic:+.3f}")
            fig.add_hline(y=0, line_color=MUTED, line_width=0.5)
            _apply_layout(fig, f"Rolling IC: {selected}",
                          f"{rolling_ic_window}-period rolling Spearman IC vs {horizon_choice} fwd {target_index} returns")
            st.plotly_chart(fig, use_container_width=True)

        # Cross-horizon IC
        st.subheader("Cross-Horizon IC")
        cross_data = {}
        for h, h_data in analysis.items():
            if selected in h_data:
                cross_data[h] = h_data[selected]["IC"]
        if cross_data:
            ch_df = pd.DataFrame.from_dict(cross_data, orient="index", columns=["IC"])
            colors_ch = [GREEN if v > 0 else RED for v in ch_df["IC"]]
            fig = go.Figure(go.Bar(
                x=ch_df.index, y=ch_df["IC"],
                marker_color=colors_ch,
                text=[f"{v:+.4f}" for v in ch_df["IC"]],
                textposition="outside",
            ))
            _apply_layout(fig, f"IC Across Horizons: {selected}",
                          f"Spearman rank IC for each forward horizon", 350)
            st.plotly_chart(fig, use_container_width=True)


# ---- TAB: MULTI-INDICATOR MODEL ----
with tab_multi:
    st.header(f"Multi-Indicator Tactical Model \u2014 {horizon_choice} Forward {target_index} Returns")

    price = resample_to_freq(index_prices, freq)
    fwd = compute_forward_returns(price, n_periods)

    # Build z-score matrix
    top_k = st.slider("Number of top indicators", 3, min(30, len(horizon_data)), 10)
    corr_threshold = st.slider("Max Correlation (collinearity filter)", 0.30, 1.00, 0.70, 0.05,
                               help="Skip indicators too correlated with already-selected ones")
    weight_method = st.radio("Weighting", ["IC-Weighted", "Equal-Weighted"], horizontal=True)

    ranked_names = ranking_df.sort_values("Composite", ascending=False).index.tolist()

    # Greedy forward-selection with collinearity filter
    selected_names = []
    skipped = []
    z_dict = {}

    for name in ranked_names:
        if len(selected_names) >= top_k:
            break
        raw_series, cat, desc, invert = indicators[name]
        z = rolling_zscore(resample_to_freq(raw_series, freq), zscore_window)
        if len(z) < 52:
            continue
        z_dict[name] = z

        if selected_names:
            max_corr = 0.0
            most_corr_with = ""
            existing_df = pd.DataFrame({n: z_dict[n] for n in selected_names})
            for ex_name in selected_names:
                pair = pd.concat([z, z_dict[ex_name]], axis=1).dropna()
                if len(pair) > 30:
                    c = abs(pair.iloc[:, 0].corr(pair.iloc[:, 1]))
                    if c > max_corr:
                        max_corr = c
                        most_corr_with = ex_name
            if max_corr > corr_threshold:
                skipped.append((name, most_corr_with, max_corr))
                continue

        selected_names.append(name)

    if skipped:
        with st.expander(f"Skipped {len(skipped)} collinear indicators"):
            for name, corr_with, corr_val in skipped:
                st.write(f"**{name}** \u2194 {corr_with} (corr={corr_val:.3f})")

    if not selected_names:
        st.warning("No indicators selected after filtering.")
    else:
        z_matrix = pd.DataFrame({n: z_dict[n] for n in selected_names})
        aligned = pd.concat([z_matrix, fwd.rename("fwd_ret")], axis=1).dropna()

        if len(aligned) < 52:
            st.warning("Not enough aligned data for composite model.")
        else:
            X = aligned[selected_names]
            y = aligned["fwd_ret"]

            if weight_method == "IC-Weighted":
                weights = {}
                for name in selected_names:
                    ic_val = horizon_data.get(name, {}).get("IC", 0)
                    weights[name] = ic_val
                w = pd.Series(weights)
                composite = (X * w).sum(axis=1) / w.abs().sum()
            else:
                composite = X.mean(axis=1)

            composite.name = "Tactical Composite"

            # Composite IC
            comp_ic, comp_pval = compute_ic(composite, y)
            comp_ric = compute_rolling_ic(composite, y, rolling_ic_window)
            comp_stability = (comp_ric > 0).mean() if len(comp_ric) > 10 else np.nan

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Composite IC", f"{comp_ic:+.4f}")
            c2.metric("p-value", f"{comp_pval:.4f}")
            c3.metric("Stability", f"{comp_stability:.1%}" if not np.isnan(comp_stability) else "-")
            c4.metric("Indicators Used", str(len(selected_names)))

            # Weights
            st.subheader("Indicator Weights")
            if weight_method == "IC-Weighted":
                w_display = w.abs() / w.abs().sum()
                w_display = w_display.sort_values(ascending=True)
            else:
                w_display = pd.Series(1 / len(selected_names), index=selected_names).sort_values(ascending=True)
            fig = go.Figure(go.Bar(
                x=w_display.values, y=w_display.index, orientation="h",
                marker_color=ACCENT,
                text=[f"{v:.1%}" for v in w_display.values],
                textposition="outside",
            ))
            _apply_layout(fig, "Indicator Weights in Composite", height=max(300, 25 * len(w_display)))
            st.plotly_chart(fig, use_container_width=True)

            # Composite rolling IC
            if not comp_ric.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=comp_ric.index, y=comp_ric.values, name="Composite Rolling IC",
                    line=dict(color=PURPLE, width=1.5),
                    fill="tozeroy", fillcolor="rgba(188,140,255,0.1)",
                ))
                fig.add_hline(y=comp_ic, line_dash="dash", line_color=GREEN,
                              annotation_text=f"Full IC: {comp_ic:+.3f}")
                fig.add_hline(y=0, line_color=MUTED, line_width=0.5)
                _apply_layout(fig, "Composite Rolling IC",
                              f"{rolling_ic_window}-period rolling Spearman IC")
                st.plotly_chart(fig, use_container_width=True)

            # Quintile returns
            qr = compute_quintile_returns(composite, y)
            if not qr.empty:
                fig = go.Figure(go.Bar(
                    x=qr.index, y=qr["Mean Return"] * 100,
                    marker_color=QUINTILE_COLORS[:len(qr)],
                    text=[f"{v:.2f}%" for v in qr["Mean Return"] * 100],
                    textposition="outside",
                ))
                _apply_layout(fig, "Quintile Returns: Tactical Composite",
                              f"Mean {horizon_choice} forward {target_index} return by composite quintile")
                fig.update_yaxes(title_text="Mean Forward Return (%)")
                st.plotly_chart(fig, use_container_width=True)

            # === BACKTEST ===
            st.subheader("Tactical Composite Backtest")
            smooth_hl = st.slider("Allocation EMA halflife (weeks)", 1, 26, 8,
                                  help="Smooth allocation to reduce turnover. Higher = slower adjustment.")
            st.caption("Allocation: EMA-smoothed percentile rank of composite \u2192 10%-90% equity weight, 1-period lag.")

            comp_full = composite.reindex(price.index).ffill().dropna()
            # Smooth composite before ranking to reduce whipsaws
            comp_smooth = comp_full.ewm(halflife=smooth_hl, min_periods=smooth_hl).mean()
            expanding_rank = comp_smooth.expanding(min_periods=52).rank(pct=True)
            eq_weight = (expanding_rank * 0.80 + 0.10).shift(1).dropna()

            idx_ret = price.pct_change().dropna()
            common_idx = eq_weight.index.intersection(idx_ret.index)
            eq_weight = eq_weight.loc[common_idx]
            idx_ret = idx_ret.loc[common_idx]

            strat_ret = eq_weight * idx_ret
            bench_ret = 0.50 * idx_ret

            cum_strat = (1 + strat_ret).cumprod()
            cum_bench = (1 + bench_ret).cumprod()

            n_years = len(strat_ret) / 52
            ann_strat = (cum_strat.iloc[-1] ** (1 / n_years) - 1) if n_years > 0 else 0
            ann_bench = (cum_bench.iloc[-1] ** (1 / n_years) - 1) if n_years > 0 else 0
            vol_strat = strat_ret.std() * np.sqrt(52)
            vol_bench = bench_ret.std() * np.sqrt(52)
            sharpe_strat = ann_strat / vol_strat if vol_strat > 0 else 0
            sharpe_bench = ann_bench / vol_bench if vol_bench > 0 else 0
            dd_strat = (cum_strat / cum_strat.cummax() - 1).min()
            dd_bench = (cum_bench / cum_bench.cummax() - 1).min()
            tracking = (strat_ret - bench_ret).std() * np.sqrt(52)
            ir = (ann_strat - ann_bench) / tracking if tracking > 0 else 0
            hit = (strat_ret > bench_ret).mean()

            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Strategy Ann Return", f"{ann_strat:.1%}",
                       delta=f"\u2191 vs Bench {ann_bench:.1%}")
            mc2.metric("Strategy Sharpe", f"{sharpe_strat:.2f}",
                       delta=f"\u2191 vs Bench {sharpe_bench:.2f}")
            mc3.metric("Max Drawdown", f"{dd_strat:.1%}",
                       delta=f"\u2191 vs Bench {dd_bench:.1%}")
            mc4.metric("Information Ratio", f"{ir:.2f}")

            mc5, mc6, mc7, mc8 = st.columns(4)
            mc5.metric("Strategy Volatility", f"{vol_strat:.1%}")
            mc6.metric("Tracking Error", f"{tracking:.1%}")
            mc7.metric("Weekly Hit Rate", f"{hit:.1%}")
            mc8.metric("Avg Equity Weight", f"{eq_weight.mean():.0%}")

            # Cumulative returns chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=cum_strat.index, y=cum_strat.values, name="Tactical Strategy",
                line=dict(color=ACCENT, width=2),
            ))
            fig.add_trace(go.Scatter(
                x=cum_bench.index, y=cum_bench.values, name=f"50% {target_index} Benchmark",
                line=dict(color=MUTED, width=1.5, dash="dash"),
            ))
            _apply_layout(fig, "Tactical Strategy Cumulative Returns",
                          "Composite signal-driven allocation vs 50% benchmark")
            fig.update_yaxes(title_text="Growth of $1")
            st.plotly_chart(fig, use_container_width=True)

            # Equity weight chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=eq_weight.index, y=eq_weight.values * 100,
                name="Equity Weight",
                line=dict(color=ACCENT, width=1),
                fill="tozeroy", fillcolor="rgba(88,166,255,0.15)",
            ))
            fig.add_hline(y=50, line_dash="dash", line_color=MUTED)
            _apply_layout(fig, "Tactical Signal \u2014 Equity Weight Over Time",
                          "Composite signal-driven allocation (10%-90%)")
            fig.update_yaxes(title_text="Equity Weight (%)")
            st.plotly_chart(fig, use_container_width=True)

            # Drawdown chart
            dd_s = cum_strat / cum_strat.cummax() - 1
            dd_b = cum_bench / cum_bench.cummax() - 1
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dd_s.index, y=dd_s.values * 100, name="Tactical Strategy",
                line=dict(color=RED, width=1),
                fill="tozeroy", fillcolor="rgba(248,81,73,0.15)",
            ))
            fig.add_trace(go.Scatter(
                x=dd_b.index, y=dd_b.values * 100, name="Benchmark",
                line=dict(color=MUTED, width=1, dash="dash"),
            ))
            _apply_layout(fig, "Drawdown Comparison",
                          "Tactical strategy vs 50% benchmark")
            fig.update_yaxes(title_text="Drawdown (%)")
            st.plotly_chart(fig, use_container_width=True)


# ---- TAB: ROLLING IC ----
with tab_roll:
    st.header(f"Rolling IC Stability \u2014 {horizon_choice} Forward {target_index} Returns")

    price = resample_to_freq(index_prices, freq)
    fwd = compute_forward_returns(price, n_periods)

    top_n_roll = st.slider("Number of indicators to display", 3, 20, 8, key="roll_n")
    top_names = ranking_df.head(top_n_roll).index.tolist()

    fig = go.Figure()
    palette = ["#58a6ff", "#3fb950", "#bc8cff", "#f85149", "#d29922",
               "#f0883e", "#a5d6ff", "#7ee787", "#ff7b72", "#ffa657",
               "#d2a8ff", "#79c0ff", "#56d364", "#e3b341", "#ff9bce",
               "#a371f7", "#ffd33d", "#b1bac4", "#ea6045", "#2dba4e"]

    for i, name in enumerate(top_names):
        if name not in indicators:
            continue
        raw_series, cat, desc, invert = indicators[name]
        z = rolling_zscore(resample_to_freq(raw_series, freq), zscore_window)
        ric = compute_rolling_ic(z, fwd, rolling_ic_window)
        if not ric.empty:
            ic_val = horizon_data.get(name, {}).get("IC", 0)
            fig.add_trace(go.Scatter(
                x=ric.index, y=ric.values,
                name=f"{name} (IC={ic_val:+.3f})",
                line=dict(color=palette[i % len(palette)], width=1.2),
            ))

    fig.add_hline(y=0, line_color=MUTED, line_width=0.5)
    _apply_layout(fig, "Rolling IC of Top Tactical Indicators",
                  f"{rolling_ic_window}-period rolling Spearman IC vs {horizon_choice} forward {target_index} returns",
                  500)
    st.plotly_chart(fig, use_container_width=True)

    # Stability table
    st.subheader("IC Stability Table")
    stab_data = []
    for name in ranking_df.index:
        meta = horizon_data[name]
        stab_data.append({
            "Indicator": name,
            "Category": meta["Category"],
            "IC": meta["IC"],
            "Stability": meta["Stability"],
            "% Positive IC": meta["Stability"],
            "Composite": meta["Composite"],
        })
    stab_df = pd.DataFrame(stab_data).set_index("Indicator")
    stab_df = stab_df.sort_values("Stability", ascending=False)
    st.dataframe(
        stab_df.style.format({
            "IC": "{:+.4f}", "Stability": "{:.1%}",
            "% Positive IC": "{:.1%}", "Composite": "{:.4f}",
        }, na_rep="-"),
        use_container_width=True,
        height=min(35 * len(stab_df) + 38, 600),
    )


# ---- TAB: PCA FACTORS ----
with tab_pca:
    st.header(f"PCA Factors \u2014 {horizon_choice} Forward {target_index} Returns")
    st.caption("Extract orthogonal principal components from all indicator z-scores, "
               "then test each PC's predictive power for forward returns.")

    pca_col1, pca_col2, pca_col3 = st.columns(3)
    n_components = pca_col1.slider("Number of PCs", 3, 10, 5, key="pca_n")
    pca_window = pca_col2.slider("Rolling PCA Window (weeks)", 104, 260, 156, key="pca_w")
    pca_horizon = pca_col3.selectbox("Forward Horizon", list(HORIZON_MAP.keys()), index=1, key="pca_h")
    pca_periods = HORIZON_MAP[pca_horizon]

    price_pca = resample_to_freq(index_prices, freq)
    fwd_pca = compute_forward_returns(price_pca, pca_periods)

    # Build z-score matrix
    z_cols = {}
    for name, (raw_series, cat, desc, invert) in indicators.items():
        z = rolling_zscore(resample_to_freq(raw_series, freq), zscore_window)
        if len(z) >= 104:
            z_cols[name] = z

    if len(z_cols) < n_components + 1:
        st.warning(f"Need at least {n_components + 1} indicators with sufficient history.")
    else:
        z_df = pd.DataFrame(z_cols).sort_index()
        # Drop columns with > 40% missing
        missing_pct = z_df.isna().mean()
        keep_cols = missing_pct[missing_pct < 0.40].index.tolist()
        z_df = z_df[keep_cols].ffill(limit=4).dropna()

        if len(z_df) < pca_window + 52:
            st.warning("Not enough data after alignment for rolling PCA.")
        else:
            actual_n = min(n_components, len(keep_cols))

            # Rolling PCA
            dates = z_df.index[pca_window:]
            pc_scores = {f"PC{i+1}": [] for i in range(actual_n)}
            pc_dates = []
            all_loadings = []
            var_explained_list = []
            prev_dominant_signs = [1] * actual_n

            for t in range(pca_window, len(z_df)):
                window_data = z_df.iloc[t - pca_window:t]
                window_data = window_data.dropna(axis=1, how="any")
                if window_data.shape[1] < actual_n:
                    continue

                pca = PCA(n_components=actual_n)
                pca.fit(window_data.values)
                current_row = z_df.iloc[t:t+1][window_data.columns]
                if current_row.isna().any(axis=1).iloc[0]:
                    continue

                scores = pca.transform(current_row.values)[0]
                loadings = pca.components_

                # Sign consistency
                for j in range(actual_n):
                    dominant_idx = np.argmax(np.abs(loadings[j]))
                    current_sign = np.sign(loadings[j, dominant_idx])
                    if current_sign != prev_dominant_signs[j] and prev_dominant_signs[j] != 0:
                        scores[j] *= -1
                        loadings[j] *= -1
                    prev_dominant_signs[j] = np.sign(loadings[j, dominant_idx])

                for j in range(actual_n):
                    pc_scores[f"PC{j+1}"].append(scores[j])

                pc_dates.append(z_df.index[t])
                all_loadings.append((window_data.columns.tolist(), loadings, pca.explained_variance_ratio_))
                var_explained_list.append(pca.explained_variance_ratio_)

            if not pc_dates:
                st.warning("Rolling PCA produced no results.")
            else:
                pc_df = pd.DataFrame(pc_scores, index=pc_dates)

                # Variance Explained
                avg_var = np.mean(var_explained_list, axis=0)
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=[f"PC{i+1}" for i in range(actual_n)],
                    y=avg_var * 100,
                    marker_color=ACCENT,
                    text=[f"{v:.1f}%" for v in avg_var * 100],
                    textposition="outside",
                    name="Individual",
                ))
                fig.add_trace(go.Scatter(
                    x=[f"PC{i+1}" for i in range(actual_n)],
                    y=np.cumsum(avg_var) * 100,
                    mode="lines+markers",
                    line=dict(color=GREEN, width=2),
                    name="Cumulative",
                ))
                _apply_layout(fig, "Average Variance Explained",
                              f"Rolling PCA ({pca_window}-week window)", 350)
                fig.update_yaxes(title_text="Variance Explained (%)")
                st.plotly_chart(fig, use_container_width=True)

                # Loadings heatmap
                last_cols, last_loadings, _ = all_loadings[-1]
                max_abs_loading = np.max(np.abs(last_loadings), axis=0)
                top_k_loading = min(20, len(last_cols))
                top_idx = np.argsort(-max_abs_loading)[:top_k_loading]
                load_df = pd.DataFrame(
                    last_loadings[:, top_idx],
                    index=[f"PC{i+1}" for i in range(actual_n)],
                    columns=[last_cols[i] for i in top_idx],
                )
                fig = go.Figure(go.Heatmap(
                    z=load_df.values,
                    x=load_df.columns.tolist(),
                    y=load_df.index.tolist(),
                    colorscale="RdBu_r",
                    zmid=0,
                    text=[[f"{v:.2f}" for v in row] for row in load_df.values],
                    texttemplate="%{text}",
                    textfont=dict(size=10),
                ))
                _apply_layout(fig, "Factor Loadings (Latest Window)",
                              f"Top {top_k_loading} indicators by max |loading|",
                              max(300, 50 * actual_n))
                st.plotly_chart(fig, use_container_width=True)

                # PC Interpretation
                with st.expander("PC Interpretation (top 5 loadings per PC)"):
                    for j in range(actual_n):
                        sorted_idx = np.argsort(-np.abs(last_loadings[j]))
                        top5 = sorted_idx[:5]
                        parts = []
                        for idx in top5:
                            sign = "+" if last_loadings[j, idx] > 0 else "-"
                            parts.append(f"{sign}{last_cols[idx]} ({last_loadings[j, idx]:.2f})")
                        var_pct = avg_var[j] * 100
                        st.markdown(f"**PC{j+1}** ({var_pct:.1f}% var): {', '.join(parts)}")

                # IC analysis for each PC
                st.subheader(f"PC Predictive Power \u2014 {pca_horizon} Forward Returns")
                pc_results = []
                for j in range(actual_n):
                    pc_series = pc_df[f"PC{j+1}"]
                    ic, pval = compute_ic(pc_series, fwd_pca)
                    ric = compute_rolling_ic(pc_series, fwd_pca, rolling_ic_window)
                    stab = (ric > 0).mean() if len(ric) > 10 else np.nan
                    qr = compute_quintile_returns(pc_series, fwd_pca)
                    hr = np.nan
                    mono = np.nan
                    if not qr.empty and len(qr) == 5:
                        means = qr["Mean Return"].values
                        hr = np.mean([means[-1] > means[0],
                                      means[-1] > means[-2],
                                      means[0] < means[1]])
                        mono_c, _ = sp_stats.spearmanr([1, 2, 3, 4, 5], means)
                        mono = mono_c
                    comp = 0.50 * abs(ic) + 0.30 * (stab if not np.isnan(stab) else 0.5) + 0.20 * (hr if not np.isnan(hr) else 0.5)
                    pc_results.append({
                        "PC": f"PC{j+1}", "IC": ic, "p-value": pval,
                        "Stability": stab, "Hit Rate": hr,
                        "Monotonicity": mono, "Composite": comp,
                    })
                pc_res_df = pd.DataFrame(pc_results)
                st.dataframe(
                    pc_res_df.style.format({
                        "IC": "{:+.4f}", "p-value": "{:.4f}",
                        "Stability": "{:.1%}", "Hit Rate": "{:.1%}",
                        "Monotonicity": "{:+.3f}", "Composite": "{:.4f}",
                    }, na_rep="-"),
                    use_container_width=True,
                )

                best_pc_idx = pc_res_df["Composite"].idxmax()
                best_pc = pc_res_df.loc[best_pc_idx]
                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("Best PC", best_pc["PC"])
                mc2.metric("Best IC", f"{best_pc['IC']:+.4f}")
                mc3.metric("Stability", f"{best_pc['Stability']:.1%}" if not np.isnan(best_pc["Stability"]) else "-")
                mc4.metric("Total Var Explained", f"{np.sum(avg_var):.1%}")

                # Rolling IC for top 3 PCs
                st.subheader("Rolling IC \u2014 Top PCs")
                top3_pcs = pc_res_df.sort_values("|IC|" if "|IC|" in pc_res_df.columns else "Composite", ascending=False).head(3) if len(pc_res_df) >= 3 else pc_res_df
                top3_pc_names = top3_pcs["PC"].tolist()
                fig = go.Figure()
                pc_colors = [ACCENT, GREEN, PURPLE]
                for i, pc_name in enumerate(top3_pc_names):
                    pc_series = pc_df[pc_name]
                    ric = compute_rolling_ic(pc_series, fwd_pca, rolling_ic_window)
                    ic_val = pc_res_df[pc_res_df["PC"] == pc_name]["IC"].iloc[0]
                    if not ric.empty:
                        fig.add_trace(go.Scatter(
                            x=ric.index, y=ric.values,
                            name=f"{pc_name} (IC={ic_val:+.3f})",
                            line=dict(color=pc_colors[i], width=1.2),
                        ))
                fig.add_hline(y=0, line_color=MUTED, line_width=0.5)
                _apply_layout(fig, "Rolling IC of Top Principal Components",
                              f"{rolling_ic_window}-period rolling Spearman IC vs {pca_horizon} forward {target_index} returns",
                              450)
                st.plotly_chart(fig, use_container_width=True)

                # Quintile returns for best PC
                best_pc_name = best_pc["PC"]
                qr = compute_quintile_returns(pc_df[best_pc_name], fwd_pca)
                if not qr.empty:
                    st.subheader(f"Quintile Returns \u2014 {best_pc_name}")
                    fig = go.Figure(go.Bar(
                        x=qr.index, y=qr["Mean Return"] * 100,
                        marker_color=QUINTILE_COLORS[:len(qr)],
                        text=[f"{v:.2f}%" for v in qr["Mean Return"] * 100],
                        textposition="outside",
                    ))
                    _apply_layout(fig, f"Quintile Returns: {best_pc_name}",
                                  f"Mean {pca_horizon} forward {target_index} return by {best_pc_name} quintile")
                    fig.update_yaxes(title_text="Mean Forward Return (%)")
                    st.plotly_chart(fig, use_container_width=True)

                # PCA Composite Signal & Backtest
                st.subheader("PCA Composite Signal & Backtest")
                significant_pcs = pc_res_df[pc_res_df["IC"].abs() > 0.05]
                if significant_pcs.empty:
                    st.info("No PCs with |IC| > 0.05. Using all PCs equally.")
                    pca_weights = {f"PC{j+1}": 1.0 for j in range(actual_n)}
                else:
                    pca_weights = dict(zip(significant_pcs["PC"], significant_pcs["IC"]))

                w_pca = pd.Series(pca_weights)
                pca_composite = (pc_df[list(pca_weights.keys())] * w_pca).sum(axis=1) / w_pca.abs().sum()
                pca_composite.name = "PCA Composite"

                # Composite rolling IC
                pca_comp_ric = compute_rolling_ic(pca_composite, fwd_pca, rolling_ic_window)
                pca_comp_ic, _ = compute_ic(pca_composite, fwd_pca)
                if not pca_comp_ric.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=pca_comp_ric.index, y=pca_comp_ric.values,
                        name="PCA Composite Rolling IC",
                        line=dict(color=PURPLE, width=1.5),
                        fill="tozeroy", fillcolor="rgba(188,140,255,0.1)",
                    ))
                    fig.add_hline(y=pca_comp_ic, line_dash="dash", line_color=GREEN,
                                  annotation_text=f"Full IC: {pca_comp_ic:+.3f}")
                    fig.add_hline(y=0, line_color=MUTED, line_width=0.5)
                    _apply_layout(fig, "PCA Composite Rolling IC",
                                  f"{rolling_ic_window}-period rolling Spearman IC")
                    st.plotly_chart(fig, use_container_width=True)

                # Backtest
                st.subheader("PCA Backtest Performance")
                comp_reindexed = pca_composite.reindex(price_pca.index).ffill().dropna()
                comp_reindexed = comp_reindexed.ewm(halflife=8, min_periods=8).mean()
                exp_rank = comp_reindexed.expanding(min_periods=52).rank(pct=True)
                pca_eq_weight = (exp_rank * 0.80 + 0.10).shift(1).dropna()

                idx_ret = price_pca.pct_change().dropna()
                common = pca_eq_weight.index.intersection(idx_ret.index)
                pca_eq_weight = pca_eq_weight.loc[common]
                pca_idx_ret = idx_ret.loc[common]

                pca_strat_ret = pca_eq_weight * pca_idx_ret
                pca_bench_ret = 0.50 * pca_idx_ret
                pca_cum_strat = (1 + pca_strat_ret).cumprod()
                pca_cum_bench = (1 + pca_bench_ret).cumprod()

                ny = len(pca_strat_ret) / 52
                ann_s = (pca_cum_strat.iloc[-1] ** (1 / ny) - 1) if ny > 0 else 0
                ann_b = (pca_cum_bench.iloc[-1] ** (1 / ny) - 1) if ny > 0 else 0
                vol_s = pca_strat_ret.std() * np.sqrt(52)
                vol_b = pca_bench_ret.std() * np.sqrt(52)
                sh_s = ann_s / vol_s if vol_s > 0 else 0
                sh_b = ann_b / vol_b if vol_b > 0 else 0
                dd_s = (pca_cum_strat / pca_cum_strat.cummax() - 1).min()
                dd_b = (pca_cum_bench / pca_cum_bench.cummax() - 1).min()
                te = (pca_strat_ret - pca_bench_ret).std() * np.sqrt(52)
                ir = (ann_s - ann_b) / te if te > 0 else 0
                hit = (pca_strat_ret > pca_bench_ret).mean()

                pm1, pm2, pm3, pm4 = st.columns(4)
                pm1.metric("Strategy Ann Return", f"{ann_s:.1%}", delta=f"\u2191 vs Bench {ann_b:.1%}")
                pm2.metric("Strategy Sharpe", f"{sh_s:.2f}", delta=f"\u2191 vs Bench {sh_b:.2f}")
                pm3.metric("Max Drawdown", f"{dd_s:.1%}", delta=f"\u2191 vs Bench {dd_b:.1%}")
                pm4.metric("Information Ratio", f"{ir:.2f}")

                pm5, pm6, pm7, pm8 = st.columns(4)
                pm5.metric("Strategy Volatility", f"{vol_s:.1%}")
                pm6.metric("Tracking Error", f"{te:.1%}")
                pm7.metric("Weekly Hit Rate", f"{hit:.1%}")
                pm8.metric("Avg Equity Weight", f"{pca_eq_weight.mean():.0%}")

                # Charts
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=pca_cum_strat.index, y=pca_cum_strat.values, name="PCA Strategy",
                    line=dict(color=ACCENT, width=2),
                ))
                fig.add_trace(go.Scatter(
                    x=pca_cum_bench.index, y=pca_cum_bench.values, name=f"50% {target_index}",
                    line=dict(color=MUTED, width=1.5, dash="dash"),
                ))
                _apply_layout(fig, "PCA Strategy Cumulative Returns")
                st.plotly_chart(fig, use_container_width=True)

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=pca_eq_weight.index, y=pca_eq_weight.values * 100,
                    name="Equity Weight", line=dict(color=ACCENT, width=1),
                    fill="tozeroy", fillcolor="rgba(88,166,255,0.15)",
                ))
                fig.add_hline(y=50, line_dash="dash", line_color=MUTED)
                _apply_layout(fig, "PCA Signal \u2014 Equity Weight Over Time",
                              "Composite PCA signal-driven allocation (10%-90%)")
                fig.update_yaxes(title_text="Equity Weight (%)")
                st.plotly_chart(fig, use_container_width=True)

                pca_dd_s = pca_cum_strat / pca_cum_strat.cummax() - 1
                pca_dd_b = pca_cum_bench / pca_cum_bench.cummax() - 1
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=pca_dd_s.index, y=pca_dd_s.values * 100, name="PCA Strategy",
                    line=dict(color=RED, width=1),
                    fill="tozeroy", fillcolor="rgba(248,81,73,0.15)",
                ))
                fig.add_trace(go.Scatter(
                    x=pca_dd_b.index, y=pca_dd_b.values * 100, name="Benchmark",
                    line=dict(color=MUTED, width=1, dash="dash"),
                ))
                _apply_layout(fig, "Drawdown Comparison", "PCA strategy vs 50% benchmark")
                fig.update_yaxes(title_text="Drawdown (%)")
                st.plotly_chart(fig, use_container_width=True)


# ---- TAB: METHODOLOGY ----
with tab_method:
    st.header("Methodology")
    st.markdown(f"""
### Tactical Indicators \u2192 Forward {target_index} Return Prediction

This app tests **tactical/short-term indicators** for their ability to predict
forward equity index returns using a rigorous statistical framework.

---

#### Indicator Categories

| Category | Description | # Indicators |
|----------|-------------|:---:|
| **Volatility Structure** | VIX, term structure, SKEW, vol risk premium, gamma | 10 |
| **Credit Stress** | HY/IG spreads, momentum, velocity, FCI stress | 8 |
| **Sentiment & Positioning** | Put/call, ERP, margin debt, flows | 5 |
| **Cross-Asset Regime** | Risk on/off, correlations, safe haven, tail risk, dollar | 8 |
| **Risk Appetite** | Risk appetite, sector breadth | 2 |

*Note: Growth indicators (CESI, PMI, nowcasting, earnings, momentum factors),
inflation indicators (breakeven), and liquidity indicators (FCI US, real yields,
curve, credit conditions) are deliberately excluded to avoid overlap with the
Growth, Inflation, and Liquidity axes in the macro model.*

---

#### Key Concepts

**Contrarian vs Pro-Cyclical:**
- Tactical indicators split into **contrarian** (VIX, put/call, SKEW \u2014 high fear = bullish)
  and **pro-cyclical** (risk appetite, breadth \u2014 high = bullish).
- The IC is always raw Spearman correlation \u2014 sign interpretation differs by type.

**Information Coefficient (IC):**
Spearman rank correlation between indicator z-score at time *t* and forward
{target_index} return over the next N periods. Range: [-1, +1].

**Stability:**
Fraction of rolling windows where the IC has the same sign as the full-sample IC.
Higher = more consistent predictive power.

**Composite Score:**
`0.50 \u00d7 |IC| + 0.30 \u00d7 Stability + 0.20 \u00d7 Hit Rate`

**Backtest Methodology:**
1. Z-score each indicator using a {zscore_window}-period rolling window
2. Build composite (IC-weighted or equal-weighted)
3. Map composite to equity weight via expanding percentile rank \u2192 10%-90% range
4. Apply 1-period lag to avoid look-ahead bias
5. Compare to 50% constant benchmark

**PCA Approach:**
1. Rolling PCA on indicator z-score matrix (window = user-selected)
2. Sign consistency across windows via dominant loading tracking
3. Test each PC's forward return predictive power
4. IC-weighted composite of significant PCs (\u007CIC\u007C > 0.05)
""")

    st.markdown("---")
    st.caption("Built with Streamlit + Plotly. Data from Investment-X DB.")
