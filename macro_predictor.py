"""
Macro Indicator -> Forward Equity Return Predictor
====================================================
Unified analysis of macro indicators across 4 categories:
  Growth, Inflation, Liquidity, Tactical.

Tests each indicator against forward 1m/3m/6m/12m returns for a user-selected
equity index using IC analysis, quintile decomposition, rolling IC stability,
regression, PCA, and category comparison.

Replaces the separate liquidity_market_predictor.py and
tactical_market_predictor.py.

Run with:  streamlit run macro_predictor.py
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
    page_title="Macro -> Equity Return Predictor",
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
ORANGE = "#f0883e"

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
    "Growth": "#3fb950",
    "Inflation": "#f0883e",
    "Liquidity": "#58a6ff",
    "Tactical": "#bc8cff",
}

ALL_CATEGORIES = list(CATEGORY_COLORS.keys())

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


@st.cache_data(ttl=3600, show_spinner="Loading macro indicators...")
def load_all_indicators(
    selected_categories: tuple,
) -> Dict[str, Tuple[pd.Series, str, str, bool]]:
    """Load all indicators in parallel, filtered by selected categories.

    Returns {name: (series, category, desc, invert)}.
    """
    from ix.db.custom.macro_taxonomy import build_macro_registry
    registry = build_macro_registry()

    # Filter by selected categories
    filtered = [r for r in registry if r[2] in selected_categories]

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

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {}
        meta = {}
        for name, fn, cat, desc, inv in filtered:
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
    """Monotonicity score: Spearman correlation between quintile rank and mean return."""
    if quintile_df.empty or len(quintile_df) < 3:
        return np.nan
    corr, _ = sp_stats.spearmanr(quintile_df["Quintile"], quintile_df["Mean Return"])
    return corr


def compute_hit_rate(indicator: pd.Series, fwd_ret: pd.Series) -> float:
    """Fraction of times indicator direction matches forward return direction."""
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
    _index_prices: pd.Series,
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
    acwi = resample_to_freq(_index_prices, freq)

    fwd_returns = {}
    for label, periods in HORIZON_MAP.items():
        fwd_returns[label] = compute_forward_returns(acwi, periods)

    results = {}
    indicator_series_aligned = {}

    for name, (raw_series, cat, desc, invert) in _indicators.items():
        ind_resampled = resample_to_freq(raw_series, freq)
        if ind_resampled.empty or len(ind_resampled) < 52:
            continue

        ind_z = rolling_zscore(ind_resampled, zscore_window)
        if ind_z.empty or len(ind_z) < 52:
            continue

        indicator_series_aligned[name] = ind_z

        for horizon_label, fwd in fwd_returns.items():
            key = (horizon_label, name)

            df = pd.concat({"ind": ind_z, "ret": fwd}, axis=1).dropna()
            if len(df) < 60:
                continue

            ic_val, ic_pval = compute_ic(df["ind"], df["ret"])
            ric = compute_rolling_ic(df["ind"], df["ret"], rolling_ic_window)
            stability = compute_ic_stability(ric, ic_val)
            hr = compute_hit_rate(df["ind"], df["ret"])
            qdf = compute_quintile_returns(df["ind"], df["ret"])
            mono = compute_monotonicity(qdf)
            reg = compute_regression(df["ind"], df["ret"])
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
# HELPER: Build composite signal from top-N indicators
# ===========================================================================


def build_composite_signal(
    ranking_df: pd.DataFrame,
    analysis: Dict,
    horizon: str,
    top_n: int,
    weight_method: str,
    corr_threshold: float,
) -> Tuple[pd.Series | None, list, list]:
    """Build IC-weighted composite from top N indicators with collinearity filter.

    Returns (composite_signal, selected_names, skipped_info).
    """
    rdf = ranking_df if not ranking_df.empty else build_ranking_df(analysis, horizon)
    if rdf.empty:
        return None, [], []

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

    if not selected:
        return None, [], skipped

    # Get ICs for selected indicators
    top_ics = {}
    for name in selected:
        k = (horizon, name)
        if k in analysis["results"]:
            top_ics[name] = analysis["results"][k]["ic"]

    composite_parts = {}
    weights = {}
    for name in selected:
        if name in ind_data:
            ic_val = top_ics.get(name, 0)
            if weight_method == "IC-Weighted":
                w = ic_val
            else:
                w = np.sign(ic_val) if ic_val != 0 else 1.0
            weights[name] = w
            composite_parts[name] = ind_data[name] * np.sign(ic_val)

    if not composite_parts:
        return None, selected, skipped

    comp_df = pd.DataFrame(composite_parts).dropna()
    if comp_df.empty:
        return None, selected, skipped

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
    return composite_signal, selected, skipped


# ===========================================================================
# HELPER: Run backtest from a signal
# ===========================================================================


def run_backtest(
    composite_signal: pd.Series,
    acwi_resampled: pd.Series,
    zscore_win: int,
    target_index: str,
) -> Dict | None:
    """Run a simple allocation backtest from a composite signal.

    Returns a dict with bt_df, metrics, or None if insufficient data.
    """
    acwi_ret = acwi_resampled.pct_change().dropna()

    signal_lagged = composite_signal.shift(1)
    signal_pctile = signal_lagged.rolling(
        zscore_win, min_periods=zscore_win // 2
    ).apply(
        lambda x: sp_stats.percentileofscore(x[:-1], x[-1]) / 100.0
        if len(x) > 1 else 0.5,
        raw=True,
    )

    eq_weight = 0.10 + signal_pctile * 0.80
    eq_weight = eq_weight.clip(0.10, 0.90)

    bt_df = pd.concat({
        "idx_ret": acwi_ret,
        "eq_weight": eq_weight,
    }, axis=1).dropna()

    if len(bt_df) < 52:
        return None

    bt_df["strategy_ret"] = bt_df["eq_weight"] * bt_df["idx_ret"]
    bt_df["benchmark_ret"] = 0.50 * bt_df["idx_ret"]
    bt_df["strategy_cum"] = (1 + bt_df["strategy_ret"]).cumprod()
    bt_df["benchmark_cum"] = (1 + bt_df["benchmark_ret"]).cumprod()
    bt_df["idx_cum"] = (1 + bt_df["idx_ret"]).cumprod()

    ann_factor = 52
    n_years = len(bt_df) / ann_factor

    strat_ann_ret = bt_df["strategy_cum"].iloc[-1] ** (1 / n_years) - 1
    bench_ann_ret = bt_df["benchmark_cum"].iloc[-1] ** (1 / n_years) - 1
    idx_ann_ret = bt_df["idx_cum"].iloc[-1] ** (1 / n_years) - 1

    strat_vol = bt_df["strategy_ret"].std() * np.sqrt(ann_factor)
    bench_vol = bt_df["benchmark_ret"].std() * np.sqrt(ann_factor)

    strat_sharpe = strat_ann_ret / strat_vol if strat_vol > 0 else 0
    bench_sharpe = bench_ann_ret / bench_vol if bench_vol > 0 else 0

    def _max_dd(cum):
        return (cum / cum.expanding().max() - 1).min()

    strat_mdd = _max_dd(bt_df["strategy_cum"])
    bench_mdd = _max_dd(bt_df["benchmark_cum"])

    excess = bt_df["strategy_ret"] - bt_df["benchmark_ret"]
    te = excess.std() * np.sqrt(ann_factor)
    ir = (strat_ann_ret - bench_ann_ret) / te if te > 0 else 0
    bt_hit = (excess > 0).mean()

    return {
        "bt_df": bt_df,
        "strat_ann_ret": strat_ann_ret,
        "bench_ann_ret": bench_ann_ret,
        "idx_ann_ret": idx_ann_ret,
        "strat_vol": strat_vol,
        "bench_vol": bench_vol,
        "strat_sharpe": strat_sharpe,
        "bench_sharpe": bench_sharpe,
        "strat_mdd": strat_mdd,
        "bench_mdd": bench_mdd,
        "te": te,
        "ir": ir,
        "bt_hit": bt_hit,
        "excess": excess,
    }


def render_backtest_charts(
    bt_result: Dict,
    target_index: str,
    strategy_name: str = "Strategy",
    strategy_color: str = GREEN,
):
    """Render standard backtest charts (cumulative, weight, drawdown, rolling excess)."""
    bt_df = bt_result["bt_df"]

    # Performance metrics
    st.markdown(f"#### {strategy_name} Performance Summary")
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Ann Return", f"{bt_result['strat_ann_ret']:.1%}",
               f"vs Bench {bt_result['bench_ann_ret']:.1%}")
    mc2.metric("Sharpe", f"{bt_result['strat_sharpe']:.2f}",
               f"vs Bench {bt_result['bench_sharpe']:.2f}")
    mc3.metric("Max Drawdown", f"{bt_result['strat_mdd']:.1%}",
               f"vs Bench {bt_result['bench_mdd']:.1%}")
    mc4.metric("Information Ratio", f"{bt_result['ir']:.2f}")

    mc5, mc6, mc7, mc8 = st.columns(4)
    mc5.metric("Volatility", f"{bt_result['strat_vol']:.1%}")
    mc6.metric("Tracking Error", f"{bt_result['te']:.1%}")
    mc7.metric("Weekly Hit Rate", f"{bt_result['bt_hit']:.1%}")
    mc8.metric("Avg Equity Weight", f"{bt_df['eq_weight'].mean():.0%}")

    # Cumulative return chart
    fig_bt = go.Figure()
    fig_bt.add_trace(go.Scatter(
        x=bt_df.index, y=bt_df["strategy_cum"],
        name=strategy_name, line=dict(color=strategy_color, width=2),
    ))
    fig_bt.add_trace(go.Scatter(
        x=bt_df.index, y=bt_df["benchmark_cum"],
        name="50% Benchmark", line=dict(color=MUTED, width=1.5, dash="dash"),
    ))
    fig_bt.add_trace(go.Scatter(
        x=bt_df.index, y=bt_df["idx_cum"],
        name=f"100% {target_index}", line=dict(color=ACCENT, width=1, dash="dot"),
        opacity=0.6,
    ))
    _apply_layout(fig_bt, "Cumulative Returns",
                   f"{strategy_name} vs 50% Benchmark vs 100% {target_index}", 450)
    fig_bt.update_layout(yaxis_title="Growth of $1")
    st.plotly_chart(fig_bt, use_container_width=True)

    # Equity weight over time
    fig_wt = go.Figure()
    fig_wt.add_trace(go.Scatter(
        x=bt_df.index, y=bt_df["eq_weight"] * 100,
        mode="lines", fill="tozeroy",
        line=dict(color=strategy_color, width=1),
        fillcolor=f"rgba({_hex_to_rgb(strategy_color)},0.2)",
    ))
    fig_wt.add_hline(y=50, line_dash="dash", line_color=MUTED,
                     annotation_text="50% Benchmark")
    _apply_layout(fig_wt, "Equity Weight Over Time",
                   "Signal-driven allocation (10%-90% range)", 300)
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
        name=strategy_name, fill="tozeroy",
        line=dict(color=RED, width=1),
        fillcolor="rgba(248,81,73,0.2)",
    ))
    fig_dd.add_trace(go.Scatter(
        x=bench_dd.index, y=bench_dd.values * 100,
        name="Benchmark", line=dict(color=MUTED, width=1, dash="dash"),
    ))
    _apply_layout(fig_dd, "Drawdown Comparison",
                   f"{strategy_name} vs 50% benchmark drawdown", 350)
    fig_dd.update_layout(yaxis_title="Drawdown (%)")
    st.plotly_chart(fig_dd, use_container_width=True)

    # Rolling 1-year excess return
    excess = bt_result["excess"]
    rolling_excess = excess.rolling(52).sum()
    if not rolling_excess.dropna().empty:
        fig_re = go.Figure()
        fig_re.add_trace(go.Scatter(
            x=rolling_excess.index,
            y=rolling_excess.values * 100,
            mode="lines",
            fill="tozeroy",
            line=dict(color=GREEN, width=1),
            fillcolor="rgba(63,185,80,0.15)",
        ))
        fig_re.add_hline(y=0, line_color="rgba(139,148,158,0.5)")
        _apply_layout(fig_re, "Rolling 1-Year Excess Return",
                       "Strategy minus 50% benchmark (trailing 52 weeks)", 350)
        fig_re.update_layout(yaxis_title="Excess Return (%)", showlegend=False)
        st.plotly_chart(fig_re, use_container_width=True)


def _hex_to_rgb(hex_color: str) -> str:
    """Convert hex color to 'r,g,b' string for rgba()."""
    h = hex_color.lstrip("#")
    return ",".join(str(int(h[i:i+2], 16)) for i in (0, 2, 4))


# ===========================================================================
# SIDEBAR
# ===========================================================================

target_index = st.sidebar.selectbox(
    "Target Index",
    list(INDEX_MAP.keys()),
    index=0,
    help="Equity index to predict forward returns for.",
)

st.sidebar.title(f"Macro -> {target_index} Returns")
st.sidebar.markdown("---")

# Category filter
selected_cats = st.sidebar.multiselect(
    "Category Filter",
    ALL_CATEGORIES,
    default=ALL_CATEGORIES,
    help="Select which macro categories to include in the analysis.",
)
if not selected_cats:
    st.sidebar.warning("Select at least one category.")
    st.stop()

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

index_prices = load_index(target_index)
if index_prices.empty:
    st.error(f"Cannot proceed without {target_index} data. Check database connection.")
    st.stop()

indicators_raw = load_all_indicators(tuple(sorted(selected_cats)))
if not indicators_raw:
    st.error("No indicators loaded. Check database connection and indicator functions.")
    st.stop()

freq_code = FREQ_MAP[resample_freq]

analysis = run_full_analysis(
    index_prices,
    indicators_raw,
    freq_code,
    zscore_win,
    rolling_ic_win,
    index_name=target_index,
)

ranking_df = build_ranking_df(analysis, horizon_choice)


# ===========================================================================
# TITLE & TABS
# ===========================================================================

st.title(f"Macro Indicators vs Forward {target_index} Returns")

# Count indicators per category
cat_counts = {}
for name, (_, cat, _, _) in indicators_raw.items():
    cat_counts[cat] = cat_counts.get(cat, 0) + 1
cat_summary = " | ".join(f"{c}: {cat_counts.get(c, 0)}" for c in selected_cats)

st.caption(
    f"Testing {len(indicators_raw)} indicators across {len(selected_cats)} categories "
    f"({cat_summary}) against forward {horizon_choice} {target_index} returns | "
    f"Resample: {resample_freq} | Z-score: {zscore_win} | Rolling IC: {rolling_ic_win}"
)

tab_rank, tab_ic, tab_quint, tab_deep, tab_multi, tab_wf, tab_pca, tab_compare, tab_method = st.tabs([
    "Rankings",
    "IC Analysis",
    "Quintile Analysis",
    "Indicator Deep Dive",
    "Multi-Indicator Model",
    "Walk-Forward Backtest",
    "PCA Factors",
    "Category Comparison",
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

        # Top 5 metrics
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

        all_horizons = list(HORIZON_MAP.keys())
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

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Full-Sample IC", f"{full_ic:+.4f}")
                c2.metric("Stability", f"{analysis['results'][key]['stability']:.1%}")
                c3.metric("Mean Rolling IC", f"{ric.mean():+.4f}")
                c4.metric("Rolling IC Std", f"{ric.std():.4f}")
            else:
                st.info("Not enough data for rolling IC.")

        # Category average IC bar chart across horizons
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
                    QUINTILE_COLORS[int(q) - 1] if int(q) <= len(QUINTILE_COLORS) else ACCENT
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
                    spreads.append({
                        "Indicator": row["Indicator"],
                        "Category": row["Category"],
                        "Q5-Q1 Spread (%)": spread,
                    })

        if spreads:
            spread_df = pd.DataFrame(spreads).sort_values("Q5-Q1 Spread (%)", ascending=True)
            fig_spread = go.Figure()
            colors = [
                CATEGORY_COLORS.get(c, ACCENT) for c in spread_df["Category"]
            ]
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
            cat = metrics["category"]
            st.markdown(
                f"**Category:** "
                f"<span style='color:{CATEGORY_COLORS.get(cat, ACCENT)}'>{cat}</span>",
                unsafe_allow_html=True,
            )
            st.markdown(f"**Description:** {metrics['description']}")
            if metrics["invert"]:
                st.markdown(
                    "*Note: This indicator is inversely related to favorable conditions. "
                    "A negative IC means that when the indicator is HIGH, "
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
                        line=dict(color=CATEGORY_COLORS.get(cat, ACCENT), width=1.5),
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
                    marker=dict(size=4, color=CATEGORY_COLORS.get(cat, ACCENT), opacity=0.4),
                    hovertemplate="Indicator: %{x:.2f}<br>Fwd Return: %{y:.1f}%<extra></extra>",
                ))
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

        rdf = build_ranking_df(analysis, composite_horizon)
        if rdf.empty:
            st.warning("No ranking data for selected horizon.")
        else:
            composite_signal, top_indicators, skipped = build_composite_signal(
                rdf, analysis, composite_horizon, top_n, weight_method, corr_threshold,
            )

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

            if composite_signal is not None:
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
                            bar_colors_cq = [
                                QUINTILE_COLORS[int(q) - 1]
                                if int(q) <= len(QUINTILE_COLORS) else ACCENT
                                for q in comp_qdf["Quintile"]
                            ]
                            fig_cq.add_trace(go.Bar(
                                x=[f"Q{int(q)}" for q in comp_qdf["Quintile"]],
                                y=comp_qdf["Mean Return"] * 100,
                                marker_color=bar_colors_cq,
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

                        bt_result = run_backtest(
                            composite_signal,
                            analysis["acwi_resampled"],
                            zscore_win,
                            target_index,
                        )
                        if bt_result is not None:
                            render_backtest_charts(bt_result, target_index,
                                                  "Composite Strategy", GREEN)
                        else:
                            st.warning("Insufficient data for backtest (need >52 periods).")

                    else:
                        st.warning("Insufficient aligned data for composite evaluation.")
                else:
                    st.warning("Forward returns not available for composite evaluation.")
            else:
                st.warning("Could not build composite signal from available indicators.")


# ===========================================================================
# TAB 6: WALK-FORWARD BACKTEST (OUT-OF-SAMPLE)
# ===========================================================================


def _wf_category_backtest(
    category_indicators: Dict[str, pd.Series],
    fwd_ret: pd.Series,
    acwi_ret: pd.Series,
    all_dates: pd.DatetimeIndex,
    lookback_weeks: int,
    top_n: int,
    corr_max: float,
    rebal_weeks: int,
    weight_method: str,
) -> Tuple[Dict | None, list]:
    """Walk-forward backtest for a SINGLE category's indicators.

    At each rebalancing date t:
      1. Compute Spearman IC for each indicator using ONLY trailing lookback_weeks
      2. Rank by |IC|, greedily select top N after removing correlated pairs
      3. Build composite with IC-weights or equal-weights (direction from IC sign)
      4. Map composite percentile rank (trailing) to equity weight [10%, 90%]
      5. Hold weight until next rebalance
    """
    min_start = lookback_weeks + 52
    if len(all_dates) < min_start + 52 or not category_indicators:
        return None, []

    selection_history = []
    eq_weights = pd.Series(dtype=float, name="eq_weight")
    rebal_indices = list(range(min_start, len(all_dates), rebal_weeks))

    for rebal_idx in rebal_indices:
        t = all_dates[rebal_idx]
        w_start = max(0, rebal_idx - lookback_weeks)
        window_dates = all_dates[w_start:rebal_idx]
        if len(window_dates) < 104:
            continue

        # --- Step 1: compute trailing IC for every indicator in this category ---
        ic_scores = {}
        for ind_name, ind_series in category_indicators.items():
            w_ind = ind_series.reindex(window_dates).dropna()
            w_fwd = fwd_ret.reindex(window_dates).dropna()
            overlap = pd.concat({"ind": w_ind, "ret": w_fwd}, axis=1).dropna()
            if len(overlap) < 52:
                continue
            try:
                ic_val, _ = sp_stats.spearmanr(overlap["ind"], overlap["ret"])
                if not np.isnan(ic_val):
                    ic_scores[ind_name] = ic_val
            except Exception:
                continue

        if len(ic_scores) < 2:
            continue

        # --- Step 2: rank by |IC|, greedy selection with correlation filter ---
        ranked = sorted(ic_scores.items(), key=lambda x: abs(x[1]), reverse=True)
        selected = []
        for ind_name, ic_val in ranked:
            if not selected:
                selected.append((ind_name, ic_val))
                continue
            candidate = category_indicators[ind_name].reindex(window_dates).dropna()
            too_corr = False
            for sel_name, _ in selected:
                sel_s = category_indicators[sel_name].reindex(window_dates).dropna()
                ov = pd.concat({"a": candidate, "b": sel_s}, axis=1).dropna()
                if len(ov) >= 30 and abs(ov["a"].corr(ov["b"])) > corr_max:
                    too_corr = True
                    break
            if not too_corr:
                selected.append((ind_name, ic_val))
            if len(selected) >= top_n:
                break

        if not selected:
            continue

        # --- Step 3: build composite signal (data up to t only) ---
        parts = {}
        wts = {}
        for ind_name, ic_val in selected:
            parts[ind_name] = category_indicators[ind_name] * np.sign(ic_val)
            wts[ind_name] = abs(ic_val) if weight_method == "IC-Weighted" else 1.0

        comp_df = pd.DataFrame(parts).loc[:t].dropna()
        if comp_df.empty:
            continue
        total_w = sum(wts.values())
        if total_w == 0:
            continue
        composite = sum(comp_df[k] * (wts[k] / total_w) for k in wts if k in comp_df.columns)
        if composite.empty or len(composite) < 52:
            continue

        # --- Step 4: percentile rank from trailing window ---
        trail = composite.iloc[-lookback_weeks:]
        if len(trail) < 52:
            continue
        pctile = sp_stats.percentileofscore(trail.iloc[:-1].values, trail.iloc[-1]) / 100.0
        eq_wt = max(0.10, min(0.90, 0.10 + pctile * 0.80))

        # --- Step 5: hold until next rebalance ---
        next_rebal = min(rebal_idx + rebal_weeks, len(all_dates))
        for d in all_dates[rebal_idx:next_rebal]:
            eq_weights[d] = eq_wt

        selection_history.append({
            "date": t,
            "selected": [n for n, _ in selected],
            "ics": {n: ic for n, ic in selected},
            "eq_weight": eq_wt,
            "n_candidates": len(ic_scores),
        })

    if not selection_history or eq_weights.empty:
        return None, selection_history

    # --- Build performance ---
    bt_df = pd.concat({"idx_ret": acwi_ret, "eq_weight": eq_weights}, axis=1).dropna()
    if len(bt_df) < 52:
        return None, selection_history

    bt_df["strategy_ret"] = bt_df["eq_weight"] * bt_df["idx_ret"]
    bt_df["benchmark_ret"] = 0.50 * bt_df["idx_ret"]
    bt_df["strategy_cum"] = (1 + bt_df["strategy_ret"]).cumprod()
    bt_df["benchmark_cum"] = (1 + bt_df["benchmark_ret"]).cumprod()
    bt_df["idx_cum"] = (1 + bt_df["idx_ret"]).cumprod()

    ann = 52
    ny = len(bt_df) / ann
    sa = bt_df["strategy_cum"].iloc[-1] ** (1 / ny) - 1
    ba = bt_df["benchmark_cum"].iloc[-1] ** (1 / ny) - 1
    sv = bt_df["strategy_ret"].std() * np.sqrt(ann)
    bv = bt_df["benchmark_ret"].std() * np.sqrt(ann)
    excess = bt_df["strategy_ret"] - bt_df["benchmark_ret"]
    te = excess.std() * np.sqrt(ann)

    def _mdd(c):
        return (c / c.expanding().max() - 1).min()

    return {
        "bt_df": bt_df,
        "strat_ann_ret": sa, "bench_ann_ret": ba,
        "strat_vol": sv, "bench_vol": bv,
        "strat_sharpe": sa / sv if sv > 0 else 0,
        "bench_sharpe": ba / bv if bv > 0 else 0,
        "strat_mdd": _mdd(bt_df["strategy_cum"]),
        "bench_mdd": _mdd(bt_df["benchmark_cum"]),
        "te": te,
        "ir": (sa - ba) / te if te > 0 else 0,
        "bt_hit": (excess > 0).mean(),
        "excess": excess,
    }, selection_history


def _wf_regime_backtest(
    growth_indicators: Dict[str, pd.Series],
    inflation_indicators: Dict[str, pd.Series],
    fwd_ret: pd.Series,
    acwi_ret: pd.Series,
    all_dates: pd.DatetimeIndex,
    lookback_weeks: int,
    top_n: int,
    corr_max: float,
    rebal_weeks: int,
    weight_method: str,
) -> Tuple[Dict | None, list]:
    """Walk-forward REGIME backtest: Growth x Inflation → 4 quadrants.

    At each rebalance:
      1. Build Growth composite (trailing IC, top N from Growth indicators)
      2. Build Inflation composite (trailing IC, top N from Inflation indicators)
      3. Classify regime from (growth_signal, inflation_signal):
         - Goldilocks  (G>0, I≤0) → 90% equity
         - Reflation   (G>0, I>0)  → 70% equity
         - Deflation   (G≤0, I≤0) → 30% equity
         - Stagflation (G≤0, I>0)  → 10% equity
    """
    min_start = lookback_weeks + 52
    if len(all_dates) < min_start + 52:
        return None, []

    # Regime allocation map
    REGIME_ALLOC = {
        "Goldilocks": 0.90,   # Growth up, Inflation down
        "Reflation": 0.70,    # Growth up, Inflation up
        "Deflation": 0.30,    # Growth down, Inflation down
        "Stagflation": 0.10,  # Growth down, Inflation up
    }

    def _build_signal(indicators, window_dates, t):
        """Build composite signal for a set of indicators at time t."""
        ic_scores = {}
        for ind_name, ind_series in indicators.items():
            w_ind = ind_series.reindex(window_dates).dropna()
            w_fwd = fwd_ret.reindex(window_dates).dropna()
            ov = pd.concat({"ind": w_ind, "ret": w_fwd}, axis=1).dropna()
            if len(ov) < 52:
                continue
            try:
                ic_val, _ = sp_stats.spearmanr(ov["ind"], ov["ret"])
                if not np.isnan(ic_val):
                    ic_scores[ind_name] = ic_val
            except Exception:
                continue

        if len(ic_scores) < 2:
            return None, []

        ranked = sorted(ic_scores.items(), key=lambda x: abs(x[1]), reverse=True)
        selected = []
        for ind_name, ic_val in ranked:
            if not selected:
                selected.append((ind_name, ic_val))
                continue
            cand = indicators[ind_name].reindex(window_dates).dropna()
            too_corr = False
            for sn, _ in selected:
                ss = indicators[sn].reindex(window_dates).dropna()
                ov2 = pd.concat({"a": cand, "b": ss}, axis=1).dropna()
                if len(ov2) >= 30 and abs(ov2["a"].corr(ov2["b"])) > corr_max:
                    too_corr = True
                    break
            if not too_corr:
                selected.append((ind_name, ic_val))
            if len(selected) >= top_n:
                break

        if not selected:
            return None, []

        parts = {}
        wts_local = {}
        for n, ic in selected:
            parts[n] = indicators[n] * np.sign(ic)
            wts_local[n] = abs(ic) if weight_method == "IC-Weighted" else 1.0
        comp_df = pd.DataFrame(parts).loc[:t].dropna()
        if comp_df.empty:
            return None, selected
        tw = sum(wts_local.values())
        if tw == 0:
            return None, selected
        sig = sum(comp_df[k] * (wts_local[k] / tw) for k in wts_local if k in comp_df.columns)
        return sig, [(n, ic) for n, ic in selected]

    eq_weights = pd.Series(dtype=float, name="eq_weight")
    selection_history = []
    rebal_indices = list(range(min_start, len(all_dates), rebal_weeks))

    for rebal_idx in rebal_indices:
        t = all_dates[rebal_idx]
        w_start = max(0, rebal_idx - lookback_weeks)
        window_dates = all_dates[w_start:rebal_idx]
        if len(window_dates) < 104:
            continue

        g_sig, g_sel = _build_signal(growth_indicators, window_dates, t)
        i_sig, i_sel = _build_signal(inflation_indicators, window_dates, t)

        if g_sig is None or i_sig is None:
            continue
        if len(g_sig) < 52 or len(i_sig) < 52:
            continue

        # Percentile rank of each signal (trailing)
        g_trail = g_sig.iloc[-lookback_weeks:]
        i_trail = i_sig.iloc[-lookback_weeks:]
        if len(g_trail) < 52 or len(i_trail) < 52:
            continue

        g_pctile = sp_stats.percentileofscore(g_trail.iloc[:-1].values, g_trail.iloc[-1]) / 100.0
        i_pctile = sp_stats.percentileofscore(i_trail.iloc[:-1].values, i_trail.iloc[-1]) / 100.0

        # Binary regime classification: above/below median (0.5 percentile)
        g_up = g_pctile > 0.50
        i_up = i_pctile > 0.50

        if g_up and not i_up:
            regime = "Goldilocks"
        elif g_up and i_up:
            regime = "Reflation"
        elif not g_up and i_up:
            regime = "Stagflation"
        else:
            regime = "Deflation"

        eq_wt = REGIME_ALLOC[regime]

        next_rebal = min(rebal_idx + rebal_weeks, len(all_dates))
        for d in all_dates[rebal_idx:next_rebal]:
            eq_weights[d] = eq_wt

        selection_history.append({
            "date": t,
            "regime": regime,
            "growth_pctile": g_pctile,
            "inflation_pctile": i_pctile,
            "eq_weight": eq_wt,
            "growth_selected": [n for n, _ in g_sel] if g_sel else [],
            "inflation_selected": [n for n, _ in i_sel] if i_sel else [],
            "selected": ([n for n, _ in g_sel] if g_sel else [])
                      + ([n for n, _ in i_sel] if i_sel else []),
            "ics": dict(g_sel or []) | dict(i_sel or []),
            "n_candidates": 0,
        })

    if not selection_history or eq_weights.empty:
        return None, selection_history

    bt_df = pd.concat({"idx_ret": acwi_ret, "eq_weight": eq_weights}, axis=1).dropna()
    if len(bt_df) < 52:
        return None, selection_history

    bt_df["strategy_ret"] = bt_df["eq_weight"] * bt_df["idx_ret"]
    bt_df["benchmark_ret"] = 0.50 * bt_df["idx_ret"]
    bt_df["strategy_cum"] = (1 + bt_df["strategy_ret"]).cumprod()
    bt_df["benchmark_cum"] = (1 + bt_df["benchmark_ret"]).cumprod()
    bt_df["idx_cum"] = (1 + bt_df["idx_ret"]).cumprod()

    ann = 52
    ny = len(bt_df) / ann
    sa = bt_df["strategy_cum"].iloc[-1] ** (1 / ny) - 1
    ba = bt_df["benchmark_cum"].iloc[-1] ** (1 / ny) - 1
    sv = bt_df["strategy_ret"].std() * np.sqrt(ann)
    bv = bt_df["benchmark_ret"].std() * np.sqrt(ann)
    excess = bt_df["strategy_ret"] - bt_df["benchmark_ret"]
    te = excess.std() * np.sqrt(ann)

    def _mdd(c):
        return (c / c.expanding().max() - 1).min()

    return {
        "bt_df": bt_df,
        "strat_ann_ret": sa, "bench_ann_ret": ba,
        "strat_vol": sv, "bench_vol": bv,
        "strat_sharpe": sa / sv if sv > 0 else 0,
        "bench_sharpe": ba / bv if bv > 0 else 0,
        "strat_mdd": _mdd(bt_df["strategy_cum"]),
        "bench_mdd": _mdd(bt_df["benchmark_cum"]),
        "te": te,
        "ir": (sa - ba) / te if te > 0 else 0,
        "bt_hit": (excess > 0).mean(),
        "excess": excess,
    }, selection_history


with tab_wf:
    st.subheader("Walk-Forward Backtest (Out-of-Sample)")
    st.markdown(
        "**Zero look-ahead bias.** Five separate backtests, each using ONLY trailing "
        "5-year data to compute IC, select indicators, and set weights. "
        "At every rebalancing date, the model has never seen the future."
    )

    if not analysis["indicator_series"]:
        st.warning("No indicator data available.")
    else:
        wf_c1, wf_c2, wf_c3 = st.columns(3)
        wf_lookback = wf_c1.slider(
            "IC Lookback (years)", 3, 10, 5, key="wf_lookback",
            help="Trailing years for IC computation at each rebalance.",
        )
        wf_top_n = wf_c2.slider("Top N indicators (per category)", 3, 15, 10, key="wf_topn")
        wf_corr_max = wf_c3.slider(
            "Max Correlation", 0.30, 1.00, 0.70, step=0.05, key="wf_corr",
        )

        wf_c4, wf_c5, wf_c6 = st.columns(3)
        wf_horizon = wf_c4.selectbox(
            "Forward Horizon",
            list(HORIZON_MAP.keys()),
            index=list(HORIZON_MAP.keys()).index(horizon_choice),
            key="wf_h",
        )
        wf_rebal_freq = wf_c5.selectbox(
            "Rebalance Frequency",
            ["Quarterly (13w)", "Monthly (4w)", "Semi-Annual (26w)"],
            index=0, key="wf_rebal",
        )
        wf_weight_method = wf_c6.selectbox(
            "Weighting", ["IC-Weighted", "Equal-Weighted"], index=0, key="wf_wm",
        )

        rebal_map = {"Quarterly (13w)": 13, "Monthly (4w)": 4, "Semi-Annual (26w)": 26}
        rebal_weeks = rebal_map[wf_rebal_freq]
        lookback_weeks = wf_lookback * 52

        ind_data = analysis["indicator_series"]
        acwi_weekly = analysis["acwi_resampled"]
        acwi_ret = acwi_weekly.pct_change().dropna()
        fwd_ret = analysis["fwd_returns"].get(wf_horizon)

        if fwd_ret is None or fwd_ret.empty:
            st.warning("Forward returns not available.")
        elif len(acwi_ret.index) < lookback_weeks + 104:
            st.warning("Insufficient data for the chosen lookback period.")
        else:
            # Build category indicator pools from analysis results
            ind_cats = {}
            for (h, name), metrics in analysis["results"].items():
                if name not in ind_cats:
                    ind_cats[name] = metrics.get("category", "Unknown")

            cat_pools = {"Growth": {}, "Inflation": {}, "Liquidity": {}, "Tactical": {}}
            for name, series in ind_data.items():
                cat = ind_cats.get(name)
                if cat in cat_pools:
                    cat_pools[cat][name] = series

            all_dates = acwi_ret.index

            # ---- Run 5 backtests ----
            STRAT_COLORS = {
                "Growth": GREEN, "Inflation": ORANGE,
                "Liquidity": ACCENT, "Tactical": PURPLE, "Regime": RED,
            }

            with st.spinner("Running 5 walk-forward backtests... (this takes ~1 min)"):
                wf_results = {}
                wf_histories = {}

                for cat_name in ["Growth", "Inflation", "Liquidity", "Tactical"]:
                    pool = cat_pools.get(cat_name, {})
                    if len(pool) < 3:
                        continue
                    res, hist = _wf_category_backtest(
                        pool, fwd_ret, acwi_ret, all_dates,
                        lookback_weeks, wf_top_n, wf_corr_max,
                        rebal_weeks, wf_weight_method,
                    )
                    if res is not None:
                        wf_results[cat_name] = res
                        wf_histories[cat_name] = hist

                # Regime: Growth x Inflation
                if len(cat_pools["Growth"]) >= 3 and len(cat_pools["Inflation"]) >= 3:
                    res, hist = _wf_regime_backtest(
                        cat_pools["Growth"], cat_pools["Inflation"],
                        fwd_ret, acwi_ret, all_dates,
                        lookback_weeks, wf_top_n, wf_corr_max,
                        rebal_weeks, wf_weight_method,
                    )
                    if res is not None:
                        wf_results["Regime"] = res
                        wf_histories["Regime"] = hist

            if not wf_results:
                st.error("No backtests produced results. Try shorter lookback.")
            else:
                # ============================================================
                # PERFORMANCE SUMMARY TABLE
                # ============================================================
                st.markdown("---")
                st.subheader("Performance Comparison")

                perf_rows = []
                for strat_name in ["Growth", "Inflation", "Liquidity", "Tactical", "Regime"]:
                    if strat_name not in wf_results:
                        continue
                    r = wf_results[strat_name]
                    perf_rows.append({
                        "Strategy": strat_name,
                        "Ann Return": f"{r['strat_ann_ret']:.1%}",
                        "Sharpe": f"{r['strat_sharpe']:.2f}",
                        "Max DD": f"{r['strat_mdd']:.1%}",
                        "Info Ratio": f"{r['ir']:.2f}",
                        "Tracking Err": f"{r['te']:.1%}",
                        "Hit Rate": f"{r['bt_hit']:.1%}",
                        "Avg Eq Wt": f"{r['bt_df']['eq_weight'].mean():.0%}",
                    })
                # Add benchmark row
                first_r = list(wf_results.values())[0]
                perf_rows.append({
                    "Strategy": "50% Benchmark",
                    "Ann Return": f"{first_r['bench_ann_ret']:.1%}",
                    "Sharpe": f"{first_r['bench_sharpe']:.2f}",
                    "Max DD": f"{first_r['bench_mdd']:.1%}",
                    "Info Ratio": "-",
                    "Tracking Err": "-",
                    "Hit Rate": "-",
                    "Avg Eq Wt": "50%",
                })
                st.dataframe(
                    pd.DataFrame(perf_rows),
                    use_container_width=True, hide_index=True,
                )

                # ============================================================
                # CUMULATIVE RETURNS — all 5 strategies
                # ============================================================
                st.markdown("---")
                st.markdown("#### Cumulative Returns")

                fig_cum = go.Figure()
                for strat_name in ["Growth", "Inflation", "Liquidity", "Tactical", "Regime"]:
                    if strat_name not in wf_results:
                        continue
                    bt = wf_results[strat_name]["bt_df"]
                    fig_cum.add_trace(go.Scatter(
                        x=bt.index, y=bt["strategy_cum"],
                        name=strat_name,
                        line=dict(color=STRAT_COLORS[strat_name], width=2),
                    ))
                first_bt = list(wf_results.values())[0]["bt_df"]
                fig_cum.add_trace(go.Scatter(
                    x=first_bt.index, y=first_bt["benchmark_cum"],
                    name="50% Benchmark",
                    line=dict(color=MUTED, width=1.5, dash="dash"),
                ))
                fig_cum.add_trace(go.Scatter(
                    x=first_bt.index, y=first_bt["idx_cum"],
                    name=f"100% {target_index}",
                    line=dict(color="#444", width=1, dash="dot"), opacity=0.5,
                ))
                _apply_layout(fig_cum, "Walk-Forward: 5 Strategies",
                               f"{wf_lookback}Y rolling IC | Top {wf_top_n} | "
                               f"{wf_weight_method} | Rebal {wf_rebal_freq}", 550)
                fig_cum.update_layout(yaxis_title="Growth of $1")
                st.plotly_chart(fig_cum, use_container_width=True)

                # ============================================================
                # EQUITY WEIGHT OVER TIME — all strategies
                # ============================================================
                st.markdown("#### Equity Allocation Over Time")
                fig_wt = go.Figure()
                for strat_name in ["Growth", "Inflation", "Liquidity", "Tactical", "Regime"]:
                    if strat_name not in wf_results:
                        continue
                    bt = wf_results[strat_name]["bt_df"]
                    fig_wt.add_trace(go.Scatter(
                        x=bt.index, y=bt["eq_weight"] * 100,
                        name=strat_name, mode="lines",
                        line=dict(color=STRAT_COLORS[strat_name], width=1.5),
                    ))
                fig_wt.add_hline(y=50, line_dash="dash", line_color=MUTED,
                                 annotation_text="50% Benchmark")
                _apply_layout(fig_wt, "Equity Weight by Strategy",
                               "Each line = allocation from that category's rolling IC composite", 400)
                fig_wt.update_layout(yaxis_title="Equity Weight (%)", yaxis_range=[0, 100])
                st.plotly_chart(fig_wt, use_container_width=True)

                # ============================================================
                # DRAWDOWN — all strategies
                # ============================================================
                st.markdown("#### Drawdowns")
                fig_dd = go.Figure()
                for strat_name in ["Growth", "Inflation", "Liquidity", "Tactical", "Regime"]:
                    if strat_name not in wf_results:
                        continue
                    bt = wf_results[strat_name]["bt_df"]
                    dd = bt["strategy_cum"] / bt["strategy_cum"].expanding().max() - 1
                    fig_dd.add_trace(go.Scatter(
                        x=dd.index, y=dd.values * 100,
                        name=strat_name,
                        line=dict(color=STRAT_COLORS[strat_name], width=1.5),
                    ))
                bench_dd = first_bt["benchmark_cum"] / first_bt["benchmark_cum"].expanding().max() - 1
                fig_dd.add_trace(go.Scatter(
                    x=bench_dd.index, y=bench_dd.values * 100,
                    name="Benchmark", line=dict(color=MUTED, width=1, dash="dash"),
                ))
                _apply_layout(fig_dd, "Drawdown Comparison", "", 400)
                fig_dd.update_layout(yaxis_title="Drawdown (%)")
                st.plotly_chart(fig_dd, use_container_width=True)

                # ============================================================
                # REGIME HISTORY (if available)
                # ============================================================
                if "Regime" in wf_histories and wf_histories["Regime"]:
                    st.markdown("---")
                    st.subheader("Regime Classification Over Time")
                    regime_hist = wf_histories["Regime"]
                    regime_df = pd.DataFrame([{
                        "Date": h["date"],
                        "Regime": h["regime"],
                        "Growth Pctile": h["growth_pctile"],
                        "Inflation Pctile": h["inflation_pctile"],
                        "Equity Weight": h["eq_weight"],
                    } for h in regime_hist])

                    regime_colors = {
                        "Goldilocks": GREEN, "Reflation": ORANGE,
                        "Stagflation": RED, "Deflation": ACCENT,
                    }

                    # Regime bar chart over time
                    fig_reg = go.Figure()
                    for regime_name in ["Goldilocks", "Reflation", "Stagflation", "Deflation"]:
                        mask = regime_df["Regime"] == regime_name
                        if mask.any():
                            sub = regime_df[mask]
                            fig_reg.add_trace(go.Bar(
                                x=sub["Date"], y=[1] * len(sub),
                                name=regime_name,
                                marker_color=regime_colors[regime_name],
                                hovertemplate=(
                                    "Date: %{x}<br>Regime: " + regime_name +
                                    "<extra></extra>"
                                ),
                            ))
                    _apply_layout(fig_reg, "Regime History",
                                   "Growth x Inflation quadrant at each rebalance", 250)
                    fig_reg.update_layout(
                        barmode="stack", showlegend=True, bargap=0,
                        yaxis=dict(showticklabels=False, showgrid=False),
                    )
                    st.plotly_chart(fig_reg, use_container_width=True)

                    # Regime frequency
                    regime_counts = regime_df["Regime"].value_counts()
                    rc1, rc2, rc3, rc4 = st.columns(4)
                    for i, (regime_name, col) in enumerate(zip(
                        ["Goldilocks", "Reflation", "Stagflation", "Deflation"],
                        [rc1, rc2, rc3, rc4]
                    )):
                        cnt = regime_counts.get(regime_name, 0)
                        pct = cnt / len(regime_df) * 100 if len(regime_df) > 0 else 0
                        col.metric(regime_name, f"{cnt} ({pct:.0f}%)")

                # ============================================================
                # FACTOR SELECTION PER CATEGORY
                # ============================================================
                st.markdown("---")
                st.subheader("Factor Selection by Category")

                wf_cat_tab = st.selectbox(
                    "View category:",
                    [k for k in ["Growth", "Inflation", "Liquidity", "Tactical", "Regime"]
                     if k in wf_histories],
                    key="wf_cat_view",
                )

                if wf_cat_tab and wf_cat_tab in wf_histories:
                    history = wf_histories[wf_cat_tab]
                    if history:
                        # Selection frequency
                        all_sel = set()
                        for h in history:
                            all_sel.update(h.get("selected", []))
                        all_sel = sorted(all_sel)

                        sel_matrix = []
                        dates = []
                        for h in history:
                            dates.append(h["date"])
                            row = [h["ics"].get(n, 0.0) for n in all_sel]
                            sel_matrix.append(row)

                        sel_df_mat = pd.DataFrame(sel_matrix, index=dates, columns=all_sel)
                        freq_counts = (sel_df_mat != 0).sum().sort_values(ascending=False)

                        st.markdown(f"#### {wf_cat_tab}: Selection Frequency")
                        st.caption(
                            f"{len(history)} rebalancing dates | "
                            f"{len(all_sel)} unique indicators ever selected"
                        )

                        top_freq = freq_counts.head(20)
                        fig_freq = go.Figure()
                        fig_freq.add_trace(go.Bar(
                            x=top_freq.values,
                            y=top_freq.index.tolist(),
                            orientation="h",
                            marker_color=STRAT_COLORS.get(wf_cat_tab, ACCENT),
                            text=[f"{v}/{len(history)}" for v in top_freq.values],
                            textposition="outside",
                        ))
                        _apply_layout(fig_freq, f"{wf_cat_tab} Selection Frequency",
                                       "How often each indicator was in the top N",
                                       max(350, len(top_freq) * 24))
                        fig_freq.update_layout(
                            xaxis_title="Times Selected",
                            yaxis=dict(autorange="reversed"), showlegend=False,
                        )
                        st.plotly_chart(fig_freq, use_container_width=True)

                        # Selection heatmap
                        top15 = freq_counts.head(15).index.tolist()
                        if top15:
                            hm_data = sel_df_mat[top15].values.T
                            hm_text = [[f"{v:+.3f}" if v != 0 else "" for v in row] for row in hm_data]
                            hm_display = np.where(hm_data == 0, np.nan, hm_data)

                            fig_hm = go.Figure(data=go.Heatmap(
                                z=hm_display,
                                x=[d.strftime("%Y-%m") if hasattr(d, 'strftime') else str(d)[:7]
                                   for d in dates],
                                y=top15,
                                colorscale="RdBu", zmid=0, zmin=-0.25, zmax=0.25,
                                text=hm_text, texttemplate="%{text}", textfont=dict(size=8),
                            ))
                            _apply_layout(fig_hm, f"{wf_cat_tab}: Factor Evolution",
                                           "IC at selection time | Blue=positive, Red=negative",
                                           max(400, len(top15) * 28))
                            fig_hm.update_layout(
                                xaxis=dict(tickangle=45, tickfont=dict(size=9)),
                                yaxis=dict(autorange="reversed"),
                            )
                            st.plotly_chart(fig_hm, use_container_width=True)

                        # Latest selection
                        st.markdown("#### Latest Selection")
                        latest = history[-1]
                        if wf_cat_tab == "Regime":
                            st.markdown(
                                f"**Date:** {latest['date']} | "
                                f"**Regime:** {latest.get('regime', '?')} | "
                                f"**Growth pctile:** {latest.get('growth_pctile', 0):.0%} | "
                                f"**Inflation pctile:** {latest.get('inflation_pctile', 0):.0%} | "
                                f"**Equity weight:** {latest['eq_weight']:.0%}"
                            )
                        else:
                            st.markdown(
                                f"**Date:** {latest['date']} | "
                                f"**Selected:** {len(latest.get('selected', []))} | "
                                f"**Equity weight:** {latest['eq_weight']:.0%}"
                            )
                        if latest.get("selected"):
                            lat_df = pd.DataFrame([
                                {"Indicator": n, "Trailing IC": f"{latest['ics'][n]:+.4f}"}
                                for n in latest["selected"] if n in latest.get("ics", {})
                            ])
                            if not lat_df.empty:
                                st.dataframe(lat_df, use_container_width=True, hide_index=True)


# ===========================================================================
# TAB 7: PCA FACTORS
# ===========================================================================

with tab_pca:
    st.subheader("PCA Factor Analysis")
    st.markdown(
        "Extract orthogonal principal components from all indicator z-scores, "
        "then test each PC's ability to predict forward returns. PCs are "
        "**guaranteed uncorrelated** -- eliminating collinearity entirely."
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
        ind_df = pd.DataFrame(ind_data)
        thresh = len(ind_df) * 0.6
        ind_df = ind_df.dropna(axis=1, thresh=int(thresh))
        ind_df = ind_df.ffill().dropna()

        if ind_df.shape[1] < 5 or len(ind_df) < pca_window + 52:
            st.warning(
                f"Insufficient overlapping data for PCA. "
                f"Have {ind_df.shape[1]} indicators x {len(ind_df)} periods; "
                f"need at least 5 indicators x {pca_window + 52} periods."
            )
        else:
            indicator_names = ind_df.columns.tolist()
            n_pcs_actual = min(n_components, ind_df.shape[1])

            # --- Rolling PCA ---
            pc_scores = {f"PC{i+1}": [] for i in range(n_pcs_actual)}
            pc_dates = []
            last_loadings = None
            last_explained = None
            prev_signs = None

            for t in range(pca_window, len(ind_df)):
                window_data = ind_df.iloc[t - pca_window : t].values
                mu = window_data.mean(axis=0)
                sigma = window_data.std(axis=0)
                sigma[sigma == 0] = 1.0
                window_std = (window_data - mu) / sigma

                pca = PCA(n_components=n_pcs_actual)
                pca.fit(window_std)

                current = ind_df.iloc[t].values
                current_std = (current - mu) / sigma
                scores = pca.transform(current_std.reshape(1, -1))[0]

                loadings = pca.components_
                if prev_signs is not None:
                    for i in range(n_pcs_actual):
                        max_idx = np.argmax(np.abs(loadings[i]))
                        if np.sign(loadings[i, max_idx]) != prev_signs[i]:
                            scores[i] *= -1
                            loadings[i] *= -1

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
            col_order = loadings_df.loc["PC1"].abs().sort_values(ascending=False).index.tolist()
            loadings_df = loadings_df[col_order]

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
                    top5_loads = loads.head(5)
                    desc_parts = []
                    for ind_name, load_val in top5_loads.items():
                        direction = "+" if load_val > 0 else "-"
                        desc_parts.append(f"{direction}{ind_name} ({load_val:.2f})")
                    st.markdown(
                        f"**{pc_name}** ({last_explained[i]*100:.1f}% var): "
                        f"{', '.join(desc_parts)}"
                    )

            # --- IC Analysis for each PC ---
            st.markdown("---")
            st.markdown(f"#### PC Predictive Power -- {pca_horizon} Forward Returns")

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
                st.markdown("#### Rolling IC -- Top PCs")
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
                    st.markdown(f"#### Quintile Returns -- {best_pc['PC']}")
                    qdf_best = best_pc["quintile_df"]
                    fig_pq = go.Figure()
                    bar_colors_pq = [
                        QUINTILE_COLORS[int(q) - 1] if int(q) <= len(QUINTILE_COLORS) else ACCENT
                        for q in qdf_best["Quintile"]
                    ]
                    fig_pq.add_trace(go.Bar(
                        x=[f"Q{int(q)}" for q in qdf_best["Quintile"]],
                        y=qdf_best["Mean Return"] * 100,
                        marker_color=bar_colors_pq,
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

                predictive_pcs = [r for r in valid_pcs if abs(r["IC"]) > 0.05]
                if not predictive_pcs:
                    st.warning("No PCs with |IC| > 0.05. Try different settings.")
                else:
                    composite_parts_pca = {}
                    weights_pca = {}
                    for r in predictive_pcs:
                        pc_name = r["PC"]
                        ic_val = r["IC"]
                        composite_parts_pca[pc_name] = pc_df[pc_name] * np.sign(ic_val)
                        weights_pca[pc_name] = abs(ic_val)

                    pca_comp_df = pd.DataFrame(composite_parts_pca).dropna()
                    if not pca_comp_df.empty:
                        total_w = sum(weights_pca.values())
                        pca_composite = sum(
                            pca_comp_df[name] * (w / total_w)
                            for name, w in weights_pca.items()
                        )
                        pca_composite.name = "PCA_Composite"

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

                        # Rolling IC
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

                        # Backtest
                        bt_result = run_backtest(
                            pca_composite,
                            analysis["acwi_resampled"],
                            zscore_win,
                            target_index,
                        )
                        if bt_result is not None:
                            render_backtest_charts(bt_result, target_index,
                                                  "PCA Strategy", PURPLE)
                        else:
                            st.warning("Insufficient data for PCA backtest (need >52 periods).")
                    else:
                        st.warning("Could not align PCA composite data.")


# ===========================================================================
# TAB 7: CATEGORY COMPARISON
# ===========================================================================

with tab_compare:
    st.subheader("Category Comparison")
    st.markdown(
        "Compare composite signals built from each of the 4 macro categories. "
        "Each category composite uses IC-weighted top-5 indicators from that category."
    )

    if ranking_df.empty:
        st.warning("No data available.")
    else:
        compare_horizon = st.selectbox(
            "Comparison Horizon",
            list(HORIZON_MAP.keys()),
            index=list(HORIZON_MAP.keys()).index(horizon_choice),
            key="compare_h",
        )

        rdf_compare = build_ranking_df(analysis, compare_horizon)
        if rdf_compare.empty:
            st.warning("No ranking data for this horizon.")
        else:
            # Build per-category composites
            category_composites = {}
            category_metrics = []

            active_cats = [c for c in ALL_CATEGORIES if c in rdf_compare["Category"].values]

            for cat in active_cats:
                cat_rdf = rdf_compare[rdf_compare["Category"] == cat].copy()
                if cat_rdf.empty:
                    continue

                # Build composite from top 5 indicators in this category
                cat_signal, cat_selected, cat_skipped = build_composite_signal(
                    cat_rdf, analysis, compare_horizon,
                    top_n=5,
                    weight_method="IC-Weighted",
                    corr_threshold=0.80,
                )

                if cat_signal is None or cat_signal.empty:
                    continue

                category_composites[cat] = cat_signal

                # Compute metrics for this category composite
                fwd = analysis["fwd_returns"].get(compare_horizon)
                if fwd is not None:
                    df_cat = pd.concat({"signal": cat_signal, "ret": fwd}, axis=1).dropna()
                    if len(df_cat) > 60:
                        cat_ic, cat_pval = sp_stats.spearmanr(df_cat["signal"], df_cat["ret"])
                        cat_ric = compute_rolling_ic(df_cat["signal"], df_cat["ret"], rolling_ic_win)
                        cat_stab = compute_ic_stability(cat_ric, cat_ic)
                        cat_hr = compute_hit_rate(df_cat["signal"], df_cat["ret"])
                        cat_qdf = compute_quintile_returns(df_cat["signal"], df_cat["ret"])
                        cat_mono = compute_monotonicity(cat_qdf)

                        category_metrics.append({
                            "Category": cat,
                            "IC": cat_ic,
                            "p-value": cat_pval,
                            "Stability": cat_stab,
                            "Hit Rate": cat_hr,
                            "Monotonicity": cat_mono,
                            "Composite Score": compute_composite_score(cat_ic, cat_stab, cat_hr),
                            "N Indicators": len(cat_selected),
                            "rolling_ic": cat_ric,
                            "quintile_df": cat_qdf,
                        })

            if not category_metrics:
                st.warning("Could not build category composites. Need more data.")
            else:
                # --- 1. Summary Metrics Table ---
                st.markdown("#### Category Composite Summary")
                summary_rows = []
                for m in category_metrics:
                    summary_rows.append({
                        "Category": m["Category"],
                        "IC": f"{m['IC']:+.4f}" if not np.isnan(m["IC"]) else "-",
                        "p-value": f"{m['p-value']:.4f}" if not np.isnan(m["p-value"]) else "-",
                        "Stability": f"{m['Stability']:.1%}" if not np.isnan(m["Stability"]) else "-",
                        "Hit Rate": f"{m['Hit Rate']:.1%}" if not np.isnan(m["Hit Rate"]) else "-",
                        "Monotonicity": f"{m['Monotonicity']:+.3f}" if not np.isnan(m["Monotonicity"]) else "-",
                        "Composite": f"{m['Composite Score']:.4f}" if not np.isnan(m["Composite Score"]) else "-",
                        "N Indicators": m["N Indicators"],
                    })
                st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

                # Top-level metrics
                best_cat = max(category_metrics, key=lambda m: abs(m["IC"]) if not np.isnan(m["IC"]) else 0)
                bc1, bc2, bc3, bc4 = st.columns(4)
                bc1.metric("Best Category", best_cat["Category"])
                bc2.metric("Best Category IC", f"{best_cat['IC']:+.4f}")
                bc3.metric("Categories Tested", str(len(category_metrics)))
                bc4.metric("Horizon", compare_horizon)

                # --- 2. Rolling IC Comparison ---
                st.markdown("---")
                st.markdown("#### Rolling IC Comparison")
                st.markdown("Rolling Spearman IC for each category's composite signal.")

                fig_ric_comp = go.Figure()
                for m in category_metrics:
                    cat = m["Category"]
                    ric = m["rolling_ic"]
                    if not ric.empty:
                        fig_ric_comp.add_trace(go.Scatter(
                            x=ric.index, y=ric.values,
                            mode="lines",
                            line=dict(color=CATEGORY_COLORS.get(cat, ACCENT), width=1.5),
                            name=f"{cat} (IC={m['IC']:+.3f})",
                        ))
                fig_ric_comp.add_hline(y=0, line_color="rgba(139,148,158,0.5)")
                _apply_layout(fig_ric_comp, "Rolling IC by Category",
                               f"{rolling_ic_win}-period rolling Spearman IC vs {compare_horizon} forward {target_index}",
                               450)
                fig_ric_comp.update_layout(yaxis_title="Spearman IC")
                st.plotly_chart(fig_ric_comp, use_container_width=True)

                # --- 3. Quintile Returns Grid ---
                st.markdown("---")
                st.markdown("#### Quintile Returns by Category")

                n_cats = len(category_metrics)
                cols_per_row = min(n_cats, 2)
                for row_start in range(0, n_cats, cols_per_row):
                    cols_q = st.columns(cols_per_row)
                    for i, col in enumerate(cols_q):
                        idx = row_start + i
                        if idx >= n_cats:
                            break
                        m = category_metrics[idx]
                        cat = m["Category"]
                        qdf = m["quintile_df"]
                        with col:
                            if not qdf.empty:
                                fig_qcat = go.Figure()
                                bar_colors_qc = [
                                    QUINTILE_COLORS[int(q) - 1] if int(q) <= len(QUINTILE_COLORS) else ACCENT
                                    for q in qdf["Quintile"]
                                ]
                                fig_qcat.add_trace(go.Bar(
                                    x=[f"Q{int(q)}" for q in qdf["Quintile"]],
                                    y=qdf["Mean Return"] * 100,
                                    marker_color=bar_colors_qc,
                                    text=[f"{v*100:.1f}%" for v in qdf["Mean Return"]],
                                    textposition="outside",
                                ))
                                _apply_layout(fig_qcat, cat,
                                               f"IC={m['IC']:+.3f}", 350)
                                fig_qcat.update_layout(
                                    yaxis_title="Mean Fwd Return (%)",
                                    showlegend=False,
                                )
                                st.plotly_chart(fig_qcat, use_container_width=True)
                            else:
                                st.info(f"No quintile data for {cat}.")

                # --- 4. Backtest Comparison ---
                st.markdown("---")
                st.markdown("#### Backtest Comparison")
                st.markdown(
                    "Each category composite drives a 10-90% equity allocation strategy. "
                    "All compared against a 50% equity benchmark."
                )

                acwi_resamp = analysis["acwi_resampled"]
                acwi_ret = acwi_resamp.pct_change().dropna()

                fig_bt_comp = go.Figure()
                bt_summary_rows = []
                has_bt_data = False

                for m in category_metrics:
                    cat = m["Category"]
                    if cat not in category_composites:
                        continue
                    bt_result = run_backtest(
                        category_composites[cat],
                        acwi_resamp,
                        zscore_win,
                        target_index,
                    )
                    if bt_result is not None:
                        has_bt_data = True
                        bt_df = bt_result["bt_df"]
                        fig_bt_comp.add_trace(go.Scatter(
                            x=bt_df.index, y=bt_df["strategy_cum"],
                            name=cat,
                            line=dict(color=CATEGORY_COLORS.get(cat, ACCENT), width=2),
                        ))
                        bt_summary_rows.append({
                            "Category": cat,
                            "Ann Return": f"{bt_result['strat_ann_ret']:.1%}",
                            "Sharpe": f"{bt_result['strat_sharpe']:.2f}",
                            "Max DD": f"{bt_result['strat_mdd']:.1%}",
                            "Info Ratio": f"{bt_result['ir']:.2f}",
                            "Tracking Error": f"{bt_result['te']:.1%}",
                            "Avg Eq Weight": f"{bt_df['eq_weight'].mean():.0%}",
                        })

                if has_bt_data:
                    # Add benchmark
                    bench_cum = (1 + 0.50 * acwi_ret).cumprod()
                    fig_bt_comp.add_trace(go.Scatter(
                        x=bench_cum.index, y=bench_cum.values,
                        name="50% Benchmark",
                        line=dict(color=MUTED, width=1.5, dash="dash"),
                    ))

                    _apply_layout(fig_bt_comp, "Category Strategy Comparison",
                                   f"Cumulative returns | {compare_horizon} signal horizon", 500)
                    fig_bt_comp.update_layout(yaxis_title="Growth of $1")
                    st.plotly_chart(fig_bt_comp, use_container_width=True)

                    # Backtest summary table
                    st.dataframe(pd.DataFrame(bt_summary_rows), use_container_width=True, hide_index=True)
                else:
                    st.warning("Insufficient data for category backtests.")

                # --- 5. Current Signal Readings ---
                st.markdown("---")
                st.markdown("#### Current Signal Readings")
                st.markdown(
                    "Latest z-score of each category composite. "
                    "Positive = bullish, negative = bearish."
                )

                current_signals = {}
                for cat, signal in category_composites.items():
                    if not signal.empty:
                        # Rolling z-score of the composite
                        z = rolling_zscore(signal, min(52, len(signal) // 2))
                        if not z.empty:
                            current_signals[cat] = z.iloc[-1]

                if current_signals:
                    fig_current = go.Figure()
                    cats_sorted = sorted(current_signals.keys(), key=lambda c: current_signals[c])
                    vals = [current_signals[c] for c in cats_sorted]
                    bar_colors_curr = [
                        GREEN if v > 0 else RED for v in vals
                    ]
                    fig_current.add_trace(go.Bar(
                        x=cats_sorted,
                        y=vals,
                        marker_color=[CATEGORY_COLORS.get(c, ACCENT) for c in cats_sorted],
                        text=[f"{v:+.2f}" for v in vals],
                        textposition="outside",
                    ))
                    fig_current.add_hline(y=0, line_color="rgba(139,148,158,0.5)")
                    _apply_layout(fig_current, "Current Category Signal Z-Scores",
                                   "Positive = bullish for forward equity returns | As of latest data point",
                                   400)
                    fig_current.update_layout(yaxis_title="Z-Score", showlegend=False)
                    st.plotly_chart(fig_current, use_container_width=True)

                    # Signal interpretation
                    sig_cols = st.columns(len(current_signals))
                    for i, (cat, val) in enumerate(sorted(current_signals.items())):
                        with sig_cols[i]:
                            label = "BULLISH" if val > 0.5 else "BEARISH" if val < -0.5 else "NEUTRAL"
                            delta_color = "normal" if val > 0 else "inverse"
                            st.metric(cat, f"{val:+.2f}", label, delta_color=delta_color)

                # --- 6. Category Correlation Matrix ---
                st.markdown("---")
                st.markdown("#### Category Composite Correlation Matrix")
                st.markdown(
                    "How correlated are the 4 category composites? Low correlation "
                    "means they capture different dimensions of macro risk."
                )

                if len(category_composites) >= 2:
                    corr_df = pd.DataFrame(category_composites).dropna()
                    if len(corr_df) > 30:
                        corr_matrix = corr_df.corr()

                        fig_corr = go.Figure(data=go.Heatmap(
                            z=corr_matrix.values,
                            x=corr_matrix.columns.tolist(),
                            y=corr_matrix.index.tolist(),
                            colorscale="RdBu",
                            zmid=0,
                            zmin=-1,
                            zmax=1,
                            text=[[f"{v:.2f}" for v in row] for row in corr_matrix.values],
                            texttemplate="%{text}",
                            textfont=dict(size=12),
                            hovertemplate="%{y} vs %{x}: %{z:.3f}<extra></extra>",
                        ))
                        _apply_layout(fig_corr, "Category Composite Correlation",
                                       "Pearson correlation of category composite signals", 400)
                        fig_corr.update_layout(
                            yaxis=dict(autorange="reversed"),
                        )
                        st.plotly_chart(fig_corr, use_container_width=True)

                        # Average off-diagonal correlation
                        mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
                        off_diag = corr_matrix.where(mask)
                        avg_corr = off_diag.stack().mean()
                        st.markdown(
                            f"**Average off-diagonal correlation:** {avg_corr:.3f} "
                            f"({'Low' if abs(avg_corr) < 0.3 else 'Moderate' if abs(avg_corr) < 0.6 else 'High'} "
                            f"-- {'good diversification' if abs(avg_corr) < 0.3 else 'some overlap' if abs(avg_corr) < 0.6 else 'significant overlap'})"
                        )
                    else:
                        st.info("Not enough overlapping data for correlation analysis.")
                else:
                    st.info("Need at least 2 categories for correlation analysis.")


# ===========================================================================
# TAB 8: METHODOLOGY
# ===========================================================================

with tab_method:
    st.subheader("Methodology")

    st.markdown("""
### Objective

This app tests whether **macro indicators** -- organized across four fundamental categories
(Growth, Inflation, Liquidity, Tactical) -- have statistically significant **predictive power**
for forward equity index returns.

The target variable is **forward simple returns** of the selected equity index at horizons
of 1 month (~4 weeks), 3 months (~13 weeks), 6 months (~26 weeks), and 12 months (~52 weeks).

---

### The Four-Category Framework

Macro indicators are organized into four mutually exclusive categories that capture
the key dimensions of the investment environment:

**1. Growth** (~31 indicators)
Economic activity and leading indicators: OECD CLIs, PMIs, ISM, nowcasting data,
earnings revisions, trade data, economic surprises. These capture the fundamental
growth cycle that drives corporate earnings.

**2. Inflation** (~13 indicators)
Price pressure and real-rate dynamics: CPI surprises, breakeven inflation, commodity
prices, oil, gold. These capture the inflationary environment that affects discount
rates and central bank reaction functions.

**3. Liquidity** (~45 indicators)
Financial plumbing: central bank balance sheets, money supply, credit conditions,
spreads, financial conditions, monetary policy expectations, yield curve, fund flows.
These capture the liquidity tide that lifts or sinks all boats.

**4. Tactical** (~24 indicators)
Short-term risk signals: volatility structure, sentiment, positioning, cross-asset
correlations, regime detection. These capture the tactical risk environment that
drives shorter-horizon return variation.

---

### Why This Matters

Different macro dimensions predict returns at different horizons:
- **Growth** tends to have strongest IC at 6-12 month horizons (slow-moving fundamentals)
- **Liquidity** peaks at 3-6 months (portfolio rebalancing and credit channels)
- **Tactical** is most predictive at 1-3 months (mean-reversion and sentiment)
- **Inflation** effects depend on the regime (supply vs demand driven)

The **Category Comparison** tab quantifies these differences empirically.

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

A **collinearity filter** (default: 0.70 correlation threshold) prevents redundant
indicators from dominating the composite.

---

### Category Comparison

For each of the four categories, we build an independent composite signal:
1. Take the top-5 indicators within that category (by composite score)
2. IC-weight them (with 0.80 correlation threshold)
3. Compute IC, stability, hit rate, and monotonicity for the composite
4. Run the standard allocation backtest

This reveals which macro dimension is currently most predictive and allows
comparison of diversification potential across categories.

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

### PCA Factor Analysis

Principal Component Analysis extracts orthogonal factors from the full indicator matrix:
- Rolling PCA (default: 156-week window) avoids look-ahead bias
- Sign consistency is maintained across windows using dominant-loading tracking
- Each PC is tested for predictive power using the same IC framework
- Predictive PCs (|IC| > 0.05) are combined into an IC-weighted composite

PCA is particularly useful when many indicators are correlated (e.g., within the
Liquidity category), as it extracts independent dimensions of variation.

---

### Walk-Forward Backtest (Out-of-Sample)

The **Walk-Forward Backtest** tab eliminates look-ahead bias entirely:

1. **Rolling IC window**: At each rebalancing date, Spearman IC is computed using
   ONLY the trailing N years (default: 5 years = 260 weeks) of data.

2. **Dynamic indicator selection**: Indicators are ranked by |IC| from the trailing
   window. Top-N are selected after removing highly correlated pairs (default: |ρ| > 0.70).

3. **Adaptive weighting**: IC-weighted uses the trailing IC magnitudes. Equal-weighted
   uses unit weights with IC sign for direction. Both methods are tested.

4. **No future information**: The model at time t has never seen any data beyond t.
   Selection, weighting, and signal percentile ranking all use only past data.

5. **Factor evolution**: The selection heatmap reveals which indicators matter in
   different market regimes — e.g., credit signals dominate during stress periods,
   growth signals during expansions.

---

### Limitations

1. **Static indicator universe**: We test only indicators available today.
   The walk-forward backtest fixes selection bias but not survivorship bias.

2. **Publication lag**: Some indicators (M2, credit, China data) are published with
   a 4-8 week lag. We do NOT adjust for this in the current analysis, which slightly
   overstates the practical IC.

3. **Survivorship bias**: We only test indicators that are available today. Indicators
   that were once popular but lost data coverage are excluded.

4. **Regime dependence**: IC values can vary substantially across monetary regimes
   (ZIRP vs normal rates). The rolling IC chart helps identify this.

5. **Correlation among indicators**: Many indicators within a category are correlated.
   The collinearity filter and PCA help mitigate this, but the composite may not add
   as much diversification as the indicator count suggests.

---

### Data Sources

All data sourced from the Investment-X database, which aggregates from FRED,
Bloomberg, and computed custom indicators. Equity indices are loaded from the database
with yfinance as fallback.
""")
