"""
Korea AA Bond Repo Leverage Strategy Analyzer
Uses ix-style data loading with fallback to synthetic data for demo.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, date

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Repo Leverage Strategy | KR Fixed Income",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

* { font-family: 'IBM Plex Sans', sans-serif; }
code, .mono { font-family: 'IBM Plex Mono', monospace; }

[data-testid="stApp"] {
    background: #0a0d12;
    color: #c8d0dc;
}
[data-testid="stSidebar"] {
    background: #0f1318 !important;
    border-right: 1px solid #1e2530;
}
[data-testid="stSidebar"] * { color: #a8b4c0 !important; }

.block-container { padding: 1.5rem 2rem; }

/* Metric cards */
.metric-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 12px;
    margin-bottom: 24px;
}
.metric-card {
    background: #0f1318;
    border: 1px solid #1e2530;
    border-radius: 6px;
    padding: 16px 18px;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
}
.metric-card.green::before { background: #00d4aa; }
.metric-card.red::before   { background: #ff4d6d; }
.metric-card.blue::before  { background: #4d9fff; }
.metric-card.gold::before  { background: #f0c040; }
.metric-card.purple::before { background: #b06dff; }

.metric-label {
    font-size: 10px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #5a6a7a;
    margin-bottom: 6px;
    font-family: 'IBM Plex Mono', monospace;
}
.metric-value {
    font-size: 22px;
    font-weight: 600;
    font-family: 'IBM Plex Mono', monospace;
    color: #e8eef4;
}
.metric-sub {
    font-size: 11px;
    color: #5a6a7a;
    margin-top: 4px;
    font-family: 'IBM Plex Mono', monospace;
}

/* Section headers */
.section-header {
    font-size: 11px;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #4d9fff;
    border-bottom: 1px solid #1e2530;
    padding-bottom: 8px;
    margin: 24px 0 16px 0;
    font-family: 'IBM Plex Mono', monospace;
}

/* Banner */
.banner {
    background: linear-gradient(135deg, #0f1318 0%, #141c24 100%);
    border: 1px solid #1e2530;
    border-left: 3px solid #4d9fff;
    border-radius: 6px;
    padding: 16px 24px;
    margin-bottom: 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.banner-title {
    font-size: 18px;
    font-weight: 600;
    color: #e8eef4;
    letter-spacing: 0.02em;
}
.banner-sub {
    font-size: 12px;
    color: #5a6a7a;
    font-family: 'IBM Plex Mono', monospace;
    margin-top: 4px;
}
.banner-tag {
    background: #1e2d3d;
    border: 1px solid #2d4060;
    color: #4d9fff;
    font-size: 11px;
    padding: 4px 10px;
    border-radius: 4px;
    font-family: 'IBM Plex Mono', monospace;
}

/* Override Plotly bg */
.js-plotly-plot { border-radius: 6px; }

/* Streamlit slider label */
[data-testid="stSlider"] label { color: #a8b4c0 !important; }
</style>
""", unsafe_allow_html=True)

# ── Data generation ───────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    """
    Attempt to load from ix; fall back to realistic synthetic KR rate data.
    """
    try:
        from ix import Series, MultiSeries
        data = MultiSeries(**{
            "Base":  Series("KR.BASERATE:PX_YTM").resample("B").ffill(),
            "Repo1": Series("REPOALLX001:PX_LAST").resample("B").ffill(),
            "Repo7": Series("REPOALLX007:PX_LAST").resample("B").ffill(),
            "AA0":   Series("BONDAV436:PX_YTM").resample("B").ffill(),
        })
        df = data.to_dataframe() if hasattr(data, "to_dataframe") else pd.DataFrame(data)
        return df, False
    except Exception:
        return _synthetic_data(), True


def _synthetic_data() -> pd.DataFrame:
    """Realistic synthetic Korean rate data 2010–2025."""
    idx = pd.bdate_range("2010-01-04", "2025-01-31")
    n   = len(idx)
    t   = np.arange(n) / 252  # years

    # Base rate: BOK policy path
    base = np.interp(t, [0, 2, 4, 5, 6, 8, 10, 11, 12, 13, 15],
                        [2.75, 3.25, 2.25, 1.75, 1.25, 1.50, 0.75, 0.50, 2.50, 3.50, 3.00])
    base += np.cumsum(np.random.normal(0, 0.01, n)) * 0.15
    base = np.clip(base, 0.25, 4.0)

    repo1 = base + 0.02 + np.random.normal(0, 0.02, n)
    repo7 = base + 0.06 + np.random.normal(0, 0.03, n)
    aa0   = base + 0.55 + np.abs(np.sin(t * 0.8)) * 0.3 + np.random.normal(0, 0.04, n)
    aa0   = np.clip(aa0, base + 0.25, base + 1.80)

    return pd.DataFrame({
        "Base":  np.round(base,  4),
        "Repo1": np.round(repo1, 4),
        "Repo7": np.round(repo7, 4),
        "AA0":   np.round(aa0,   4),
    }, index=idx)


# ── Helpers ───────────────────────────────────────────────────────────────────
def compute_strategy(df: pd.DataFrame, leverage: float, initial_capital: float,
                     funding_col: str, rebalance_freq: str) -> dict:
    """
    Compute leveraged AA0-repo carry strategy.

    Net daily carry (bps/yr basis):
        income   = leverage  * AA0
        funding  = (leverage-1) * Repo7
        net_carry= income - funding
    Daily P&L (on equity):
        pnl_daily = net_carry / 252 / 100
    """
    d = df.copy().dropna()

    d["net_carry_pct"] = leverage * d["AA0"] - (leverage - 1) * d[funding_col]
    d["spread"]        = d["AA0"] - d[funding_col]          # raw AA0-repo spread
    d["daily_pnl"]     = d["net_carry_pct"] / 252 / 100     # as fraction of equity
    d["cum_pnl"]       = (1 + d["daily_pnl"]).cumprod()
    d["equity_value"]  = initial_capital * d["cum_pnl"]

    # Drawdown
    roll_max           = d["equity_value"].cummax()
    d["drawdown"]      = (d["equity_value"] - roll_max) / roll_max * 100

    # Rolling 60d Sharpe
    roll_mean  = d["daily_pnl"].rolling(60).mean()
    roll_std   = d["daily_pnl"].rolling(60).std()
    d["sharpe_60d"] = np.where(roll_std > 0, roll_mean / roll_std * np.sqrt(252), np.nan)

    # Annual returns
    d["year"] = d.index.year
    annual = (d.groupby("year")["daily_pnl"]
                .apply(lambda x: (1 + x).prod() - 1)
                .rename("annual_return"))

    # Summary metrics
    total_ret   = d["cum_pnl"].iloc[-1] - 1
    ann_ret     = (1 + total_ret) ** (252 / len(d)) - 1
    ann_vol     = d["daily_pnl"].std() * np.sqrt(252)
    sharpe      = ann_ret / ann_vol if ann_vol > 0 else 0
    max_dd      = d["drawdown"].min()
    avg_carry   = d["net_carry_pct"].mean()
    avg_spread  = d["spread"].mean()

    return {
        "df": d,
        "annual": annual,
        "metrics": {
            "total_ret":   total_ret,
            "ann_ret":     ann_ret,
            "ann_vol":     ann_vol,
            "sharpe":      sharpe,
            "max_dd":      max_dd,
            "avg_carry":   avg_carry,
            "avg_spread":  avg_spread,
            "final_equity": d["equity_value"].iloc[-1],
        },
    }


AXIS_STYLE = dict(gridcolor="#1a2030", zerolinecolor="#1a2030")
XAXIS_STYLE = dict(**AXIS_STYLE, showspikes=True, spikecolor="#2a3a50", spikemode="across")

CHART_LAYOUT = dict(
    paper_bgcolor="#0a0d12",
    plot_bgcolor="#0f1318",
    font=dict(family="IBM Plex Mono", size=11, color="#7a8a9a"),
    hovermode="x unified",
    hoverlabel=dict(bgcolor="#0f1318", bordercolor="#2a3a50",
                    font=dict(family="IBM Plex Mono", size=11, color="#c8d0dc")),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#1e2530"),
    margin=dict(l=10, r=10, t=30, b=10),
)

def chart_layout(height=300, xaxis=None, yaxis=None, yaxis2=None, **kwargs):
    """Build a layout dict merging CHART_LAYOUT with per-chart axis overrides."""
    layout = dict(**CHART_LAYOUT, height=height)
    layout["xaxis"] = {**XAXIS_STYLE, **(xaxis or {})}
    layout["yaxis"] = {**AXIS_STYLE, **(yaxis or {})}
    if yaxis2 is not None:
        layout["yaxis2"] = yaxis2
    layout.update(kwargs)
    return layout

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Strategy Parameters")
    st.markdown("---")

    leverage = st.slider("Leverage", min_value=1.0, max_value=6.0, value=4.65,
                         step=0.05, format="%.2fx")

    initial_capital = st.number_input("Initial Capital (₩ bn)", min_value=1,
                                      max_value=10000, value=100, step=10)

    funding_col = st.selectbox("Funding Rate", ["Repo7", "Repo1"],
                                index=0, help="Primary repo funding leg")

    st.markdown("---")
    st.markdown("### 📅 Date Range")
    date_start = st.date_input("From", value=date(2010, 1, 1),
                                min_value=date(2010, 1, 1), max_value=date(2025, 1, 1))
    date_end   = st.date_input("To",   value=date(2025, 1, 31),
                                min_value=date(2010, 1, 1), max_value=date(2025, 1, 31))

    st.markdown("---")
    st.markdown("### 🔍 Display Options")
    show_base     = st.checkbox("Show BOK Base Rate", value=True)
    show_repo1    = st.checkbox("Show Repo 1D", value=False)
    show_drawdown = st.checkbox("Show Drawdown Chart", value=True)
    show_sharpe   = st.checkbox("Show Rolling Sharpe", value=True)

# ── Load & Filter Data ────────────────────────────────────────────────────────
raw_df, is_synthetic = load_data()
df = raw_df.loc[str(date_start):str(date_end)].copy()

results = compute_strategy(df, leverage, initial_capital, funding_col, "B")
d       = results["df"]
m       = results["metrics"]

# ── Banner ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="banner">
  <div>
    <div class="banner-title">AA Bond Repo Leverage Strategy</div>
    <div class="banner-sub">
      KR Corporate AA0 · Funded via {funding_col} · {leverage:.2f}× Leverage
      {"&nbsp;&nbsp;⚠ synthetic demo data" if is_synthetic else ""}
    </div>
  </div>
  <div style="display:flex;gap:8px;">
    <div class="banner-tag">{date_start.strftime('%Y-%m')} → {date_end.strftime('%Y-%m')}</div>
    <div class="banner-tag">Equity ₩{initial_capital}bn</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Metrics ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="metric-grid">
  <div class="metric-card green">
    <div class="metric-label">Total Return</div>
    <div class="metric-value">{m['total_ret']*100:+.1f}%</div>
    <div class="metric-sub">{m['ann_ret']*100:.2f}% / yr</div>
  </div>
  <div class="metric-card blue">
    <div class="metric-label">Net Carry (avg)</div>
    <div class="metric-value">{m['avg_carry']:.2f}%</div>
    <div class="metric-sub">Levered yield on equity</div>
  </div>
  <div class="metric-card gold">
    <div class="metric-label">AA0–Repo Spread</div>
    <div class="metric-value">{m['avg_spread']*100:.0f}bp</div>
    <div class="metric-sub">Raw carry before leverage</div>
  </div>
  <div class="metric-card {'green' if m['sharpe'] > 1 else 'purple'}">
    <div class="metric-label">Sharpe Ratio</div>
    <div class="metric-value">{m['sharpe']:.2f}</div>
    <div class="metric-sub">Ann. ret / Ann. vol</div>
  </div>
  <div class="metric-card red">
    <div class="metric-label">Max Drawdown</div>
    <div class="metric-value">{m['max_dd']:.2f}%</div>
    <div class="metric-sub">Peak-to-trough</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Chart 1: Rates Overview ───────────────────────────────────────────────────
st.markdown('<div class="section-header">Market Rates</div>', unsafe_allow_html=True)

fig_rates = go.Figure()
if show_base:
    fig_rates.add_trace(go.Scatter(x=d.index, y=d["Base"], name="BOK Base",
        line=dict(color="#5a6a7a", width=1.5, dash="dot")))
if show_repo1:
    fig_rates.add_trace(go.Scatter(x=d.index, y=d["Repo1"], name="Repo 1D",
        line=dict(color="#4d9fff", width=1, dash="dash")))
fig_rates.add_trace(go.Scatter(x=d.index, y=d["Repo7"], name="Repo 7D",
    line=dict(color="#4d9fff", width=1.5)))
fig_rates.add_trace(go.Scatter(x=d.index, y=d["AA0"], name="AA0 Bond YTM",
    line=dict(color="#00d4aa", width=2)))
fig_rates.add_trace(go.Scatter(x=d.index, y=d["spread"]*100,
    name="Spread (bp, rhs)", yaxis="y2",
    line=dict(color="#f0c040", width=1), opacity=0.7))

fig_rates.update_layout(**chart_layout(
    height=320,
    yaxis=dict(title="Rate (%)", tickformat=".2f"),
    yaxis2=dict(title="Spread (bp)", overlaying="y", side="right",
                gridcolor="#0f1318", tickformat=".0f", color="#f0c040"),
    legend=dict(orientation="h", y=1.05, x=0, bgcolor="rgba(0,0,0,0)"),
))
st.plotly_chart(fig_rates, use_container_width=True)

# ── Chart 2: Strategy P&L ─────────────────────────────────────────────────────
st.markdown('<div class="section-header">Strategy Performance</div>', unsafe_allow_html=True)

cols = st.columns([3, 2])

with cols[0]:
    fig_pnl = go.Figure()
    fig_pnl.add_trace(go.Scatter(
        x=d.index, y=d["equity_value"],
        name="Portfolio Value",
        fill="tozeroy",
        fillcolor="rgba(0,212,170,0.05)",
        line=dict(color="#00d4aa", width=2),
    ))
    # Unlevered reference
    unlevered = initial_capital * (1 + d["AA0"] / 252 / 100).cumprod()
    fig_pnl.add_trace(go.Scatter(
        x=d.index, y=unlevered,
        name="Unlevered AA0",
        line=dict(color="#5a6a7a", width=1, dash="dash"),
    ))
    fig_pnl.update_layout(**chart_layout(
        height=300,
        yaxis=dict(tickformat=",.1f"),
        legend=dict(orientation="h", y=1.1, x=0, bgcolor="rgba(0,0,0,0)"),
        title=dict(text="Equity Value (₩ bn)", font=dict(size=12, color="#7a8a9a"),
                   x=0, xanchor="left"),
    ))
    st.plotly_chart(fig_pnl, use_container_width=True)

with cols[1]:
    ann = results["annual"].reset_index()
    ann.columns = ["Year", "Return"]
    colors = ["#00d4aa" if r >= 0 else "#ff4d6d" for r in ann["Return"]]

    fig_ann = go.Figure(go.Bar(
        x=ann["Year"].astype(str),
        y=ann["Return"] * 100,
        marker_color=colors,
        marker_line_width=0,
        text=[f"{r*100:.1f}%" for r in ann["Return"]],
        textposition="outside",
        textfont=dict(size=9, color="#7a8a9a"),
    ))
    fig_ann.update_layout(**chart_layout(
        height=300,
        yaxis=dict(tickformat=".1f", ticksuffix="%"),
        title=dict(text="Annual Returns (%)", font=dict(size=12, color="#7a8a9a"),
                   x=0, xanchor="left"),
        bargap=0.3,
    ))
    st.plotly_chart(fig_ann, use_container_width=True)

# ── Chart 3: Drawdown + Sharpe ────────────────────────────────────────────────
if show_drawdown or show_sharpe:
    sub_cols = st.columns(2)

    if show_drawdown:
        with sub_cols[0]:
            st.markdown('<div class="section-header">Drawdown</div>', unsafe_allow_html=True)
            fig_dd = go.Figure()
            fig_dd.add_trace(go.Scatter(
                x=d.index, y=d["drawdown"],
                fill="tozeroy",
                fillcolor="rgba(255,77,109,0.12)",
                line=dict(color="#ff4d6d", width=1.5),
                name="Drawdown %",
            ))
            fig_dd.update_layout(**chart_layout(
                height=220,
                yaxis=dict(tickformat=".2f", ticksuffix="%"),
            ))
            st.plotly_chart(fig_dd, use_container_width=True)

    if show_sharpe:
        with sub_cols[1]:
            st.markdown('<div class="section-header">Rolling 60D Sharpe</div>', unsafe_allow_html=True)
            fig_sh = go.Figure()
            fig_sh.add_hrect(y0=1, y1=3, fillcolor="rgba(0,212,170,0.05)",
                             line_width=0, annotation_text="Good", 
                             annotation_position="top left",
                             annotation_font=dict(size=9, color="#00d4aa"))
            fig_sh.add_trace(go.Scatter(
                x=d.index, y=d["sharpe_60d"],
                line=dict(color="#4d9fff", width=1.5),
                name="Sharpe 60D",
            ))
            fig_sh.add_hline(y=0, line_color="#3a4a5a", line_width=1)
            fig_sh.update_layout(**chart_layout(
                height=220,
                yaxis=dict(tickformat=".1f"),
            ))
            st.plotly_chart(fig_sh, use_container_width=True)

# ── Chart 4: Net Carry Decomp ─────────────────────────────────────────────────
st.markdown('<div class="section-header">Carry Decomposition</div>', unsafe_allow_html=True)

fig_carry = make_subplots(specs=[[{"secondary_y": True}]])
fig_carry.add_trace(go.Scatter(
    x=d.index, y=leverage * d["AA0"],
    name="Levered Income", fill="tozeroy",
    fillcolor="rgba(0,212,170,0.07)",
    line=dict(color="#00d4aa", width=1.2),
))
fig_carry.add_trace(go.Scatter(
    x=d.index, y=(leverage - 1) * d[funding_col],
    name="Funding Cost", fill="tozeroy",
    fillcolor="rgba(255,77,109,0.07)",
    line=dict(color="#ff4d6d", width=1.2),
))
fig_carry.add_trace(go.Scatter(
    x=d.index, y=d["net_carry_pct"],
    name="Net Carry", line=dict(color="#f0c040", width=2),
))
fig_carry.update_layout(**chart_layout(
    height=280,
    yaxis=dict(title="Rate (%)", tickformat=".2f"),
    legend=dict(orientation="h", y=1.1, x=0, bgcolor="rgba(0,0,0,0)"),
))
st.plotly_chart(fig_carry, use_container_width=True)

# ── Leverage Sensitivity ──────────────────────────────────────────────────────
st.markdown('<div class="section-header">Leverage Sensitivity (current date range)</div>', unsafe_allow_html=True)

lev_range = np.arange(1.0, 7.05, 0.25)
sens_rows = []
for lv in lev_range:
    r = compute_strategy(df, lv, initial_capital, funding_col, "B")
    mm = r["metrics"]
    sens_rows.append({
        "Leverage": lv,
        "Ann Return (%)": mm["ann_ret"] * 100,
        "Ann Vol (%)":    mm["ann_vol"] * 100,
        "Sharpe":         mm["sharpe"],
        "Max DD (%)":     mm["max_dd"],
        "Avg Carry (%)":  mm["avg_carry"],
    })
sens_df = pd.DataFrame(sens_rows)

fig_sens = make_subplots(rows=1, cols=3,
    subplot_titles=("Ann. Return vs Leverage",
                    "Sharpe vs Leverage",
                    "Max Drawdown vs Leverage"))

fig_sens.add_trace(go.Scatter(x=sens_df["Leverage"], y=sens_df["Ann Return (%)"],
    line=dict(color="#00d4aa", width=2), showlegend=False), row=1, col=1)
fig_sens.add_trace(go.Scatter(x=sens_df["Leverage"], y=sens_df["Sharpe"],
    line=dict(color="#4d9fff", width=2), showlegend=False), row=1, col=2)
fig_sens.add_trace(go.Scatter(x=sens_df["Leverage"], y=sens_df["Max DD (%)"],
    line=dict(color="#ff4d6d", width=2), showlegend=False), row=1, col=3)

# Mark current leverage
for col_idx, y_col in enumerate(["Ann Return (%)", "Sharpe", "Max DD (%)"], start=1):
    y_val = np.interp(leverage, sens_df["Leverage"], sens_df[y_col])
    fig_sens.add_trace(go.Scatter(x=[leverage], y=[y_val],
        mode="markers+text",
        marker=dict(color="#f0c040", size=10, symbol="diamond"),
        text=[f"  {leverage:.2f}×"],
        textfont=dict(color="#f0c040", size=10),
        showlegend=False), row=1, col=col_idx)

fig_sens.update_layout(**chart_layout(height=260))
fig_sens.update_layout(
    annotations=[dict(font=dict(size=11, color="#7a8a9a"))
                 for _ in fig_sens.layout.annotations]
)
for ax in ["xaxis", "xaxis2", "xaxis3", "yaxis", "yaxis2", "yaxis3"]:
    fig_sens.update_layout(**{ax: dict(gridcolor="#1a2030",
                                       zerolinecolor="#1a2030",
                                       color="#7a8a9a")})
st.plotly_chart(fig_sens, use_container_width=True)

# ── Data Table ────────────────────────────────────────────────────────────────
with st.expander("📋 Raw Data Preview"):
    show_cols = ["Base", "Repo1", "Repo7", "AA0", "spread", "net_carry_pct",
                 "daily_pnl", "equity_value", "drawdown"]
    st.dataframe(
        d[show_cols].tail(252).style
          .format({c: "{:.4f}" for c in show_cols})
          .background_gradient(subset=["net_carry_pct"], cmap="RdYlGn"),
        use_container_width=True,
        height=300,
    )

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center;margin-top:40px;padding:16px;
            border-top:1px solid #1e2530;font-size:11px;color:#3a4a5a;
            font-family:"IBM Plex Mono",monospace;'>
  KR Fixed Income Desk · Repo Leverage Strategy Analyzer
  · Past performance is not indicative of future results
</div>
""", unsafe_allow_html=True)