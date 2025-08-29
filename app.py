# app.py
import streamlit as st
import pandas as pd
import numpy as np
from math import sqrt
from typing import Iterable, Tuple
import plotly.express as px
import plotly.graph_objects as go
import ix

# =========================
# Helpers
# =========================
@st.cache_data(show_spinner=False)
def load_yahoo(sym: str) -> pd.DataFrame:
    df = ix.misc.crawler.get_yahoo_data(sym)
    df = df.sort_index()
    df = df.rename(columns={c: c.title() for c in df.columns})
    for c in ["Open", "High", "Low", "Close"]:
        if c not in df.columns:
            raise ValueError(f"Missing column '{c}' in data for {sym}: {df.columns.tolist()}")
    return df

def build_thresholds(
    vix_df: pd.DataFrame,
    mode: str,
    abs_spike: float,
    abs_cool: float,
    full_pct_spike: float,
    full_pct_cool: float,
    roll_window: int,
    roll_pct_spike: float,
    roll_pct_cool: float,
    zspike_sigma: float,
    zcool_sigma: float,
) -> pd.DataFrame:
    out = vix_df.copy()

    if mode == "static_absolute":
        out["spike_thr"] = float(abs_spike)
        out["cool_thr"]  = float(abs_cool)

    elif mode == "static_percentile":
        spk = out["High"].quantile(full_pct_spike)
        cll = out["Close"].quantile(full_pct_cool)
        out["spike_thr"] = spk
        out["cool_thr"]  = cll

    elif mode == "rolling_percentile":
        out["spike_thr"] = out["High"].rolling(roll_window, min_periods=roll_window).quantile(roll_pct_spike)
        out["cool_thr"]  = out["Close"].rolling(roll_window, min_periods=roll_window).quantile(roll_pct_cool)

    elif mode == "zscore":
        high_mean, high_std = out["High"].mean(), out["High"].std(ddof=1)
        close_mean, close_std = out["Close"].mean(), out["Close"].std(ddof=1)
        out["spike_thr"] = high_mean + zspike_sigma * high_std
        out["cool_thr"]  = close_mean + zcool_sigma * close_std
    else:
        raise ValueError(f"Unknown threshold mode: {mode}")

    return out

def find_signals_dynamic(vix_df: pd.DataFrame, use_low_for_cool: bool) -> pd.DataFrame:
    """
    Expects columns: High, Close, (Low if use_low_for_cool), spike_thr, cool_thr.
    Rule:
      - Start 'spike block' on first day with High >= spike_thr.
      - End block at first subsequent day where (Close or Low) < cool_thr; that day = signal_date.
      - Multiple highs above threshold before cool-off = one block (one eventual signal).
    """
    cool_series = vix_df["Low"] if use_low_for_cool else vix_df["Close"]

    in_spike = False
    spike_start = None
    signals = []

    for dt in vix_df.index:
        spk_thr = vix_df.at[dt, "spike_thr"]
        cool_thr = vix_df.at[dt, "cool_thr"]
        if pd.isna(spk_thr) or pd.isna(cool_thr):
            continue

        h = vix_df.at[dt, "High"]
        c = cool_series.at[dt]

        if not in_spike:
            if h >= spk_thr:
                in_spike = True
                spike_start = dt
        else:
            if c < cool_thr:
                signal_date = dt
                prev_ix = vix_df.index.get_loc(dt) - 1
                spike_end = vix_df.index[max(prev_ix, 0)]
                signals.append({
                    "spike_start": spike_start,
                    "spike_end": spike_end,
                    "signal_date": signal_date,
                    "spike_thr": float(spk_thr),
                    "cool_thr": float(cool_thr),
                })
                in_spike = False
                spike_start = None

    return pd.DataFrame(signals)

def fwd_returns(price: pd.Series, horizons: Iterable[int]) -> pd.DataFrame:
    out = pd.DataFrame(index=price.index)
    for h in horizons:
        out[f"fwd_{h}d"] = price.shift(-h) / price - 1.0
    return out

def attach_perf(signals_df: pd.DataFrame, fr_df: pd.DataFrame, horizons: Iterable[int]) -> pd.DataFrame:
    if signals_df.empty:
        return pd.DataFrame(columns=list(signals_df.columns) + [f"fwd_{h}d" for h in horizons])
    rows = []
    for _, row in signals_df.iterrows():
        d = row["signal_date"]
        if d in fr_df.index:
            r = row.to_dict()
            r.update(fr_df.loc[d].to_dict())
            rows.append(r)
    return pd.DataFrame(rows)

def summarize_event_perf(df: pd.DataFrame, horizons: Iterable[int]) -> pd.DataFrame:
    stats = []
    for h in horizons:
        col = f"fwd_{h}d"
        s = df[col].dropna()
        stats.append({
            "horizon_days": h,
            "n": int(s.shape[0]),
            "mean": float(s.mean()) if s.size else np.nan,
            "median": float(s.median()) if s.size else np.nan,
            "stdev": float(s.std(ddof=1)) if s.size > 1 else np.nan,
            "hit_ratio": float((s > 0).mean()) if s.size else np.nan,
            "min": float(s.min()) if s.size else np.nan,
            "max": float(s.max()) if s.size else np.nan,
        })
    return pd.DataFrame(stats)

def onesample_t(s: pd.Series, mu=0.0):
    s = s.dropna()
    n = s.shape[0]
    if n < 2:
        return {"n": int(n), "t": np.nan, "se": np.nan, "mean": float(s.mean()) if n else np.nan}
    se = s.std(ddof=1) / sqrt(n)
    t = (s.mean() - mu) / se if se > 0 else np.nan
    return {"n": int(n), "t": float(t), "se": float(se), "mean": float(s.mean())}

def apply_quiet_period(signals_df: pd.DataFrame, quiet_days: int) -> pd.DataFrame:
    if signals_df.empty:
        return signals_df.copy()
    d = signals_df.sort_values("signal_date").copy()
    d["gap"] = d["signal_date"].diff()
    keep = d["gap"].isna() | (d["gap"] > pd.Timedelta(days=quiet_days))
    return d.loc[keep, ["spike_start", "spike_end", "signal_date", "spike_thr", "cool_thr"]]

def robustness_dynamic(
    vix_df_base: pd.DataFrame,
    bench_close: pd.Series,
    horizons: Iterable[int],
    mode: str,
    abs_spike: float,
    abs_cool: float,
    roll_window: int,
    use_low_for_cool: bool,
) -> pd.DataFrame:
    """Small grid around chosen mode's parameters; meant for quick sensitivity checks."""
    fr_local = fwd_returns(bench_close, horizons)
    results = []

    if mode == "static_absolute":
        for spk in (abs_spike-5, abs_spike, abs_spike+5):
            for cool in (abs_cool-2, abs_cool, abs_cool+2):
                tmp = vix_df_base.copy()
                tmp["spike_thr"] = spk
                tmp["cool_thr"]  = cool
                sigs = find_signals_dynamic(tmp, use_low_for_cool)
                ep = attach_perf(sigs, fr_local, horizons)
                mean_63 = ep.get("fwd_63d", pd.Series(dtype=float)).mean() if not ep.empty else np.nan
                results.append({"spike_param": spk, "cool_param": cool, "n": int(ep.shape[0]), "fwd_63d_mean": float(mean_63) if pd.notna(mean_63) else np.nan})

    elif mode in ("static_percentile", "rolling_percentile"):
        spk_grid = (0.97, 0.98, 0.99)
        cool_grid = (0.50, 0.60, 0.70)
        for spk_q in spk_grid:
            for cool_q in cool_grid:
                tmp = vix_df_base.copy()
                if mode == "static_percentile":
                    tmp["spike_thr"] = tmp["High"].quantile(spk_q)
                    tmp["cool_thr"]  = tmp["Close"].quantile(cool_q)
                else:
                    tmp["spike_thr"] = tmp["High"].rolling(roll_window, min_periods=roll_window).quantile(spk_q)
                    tmp["cool_thr"]  = tmp["Close"].rolling(roll_window, min_periods=roll_window).quantile(cool_q)
                sigs = find_signals_dynamic(tmp, use_low_for_cool)
                ep = attach_perf(sigs, fr_local, horizons)
                mean_63 = ep.get("fwd_63d", pd.Series(dtype=float)).mean() if not ep.empty else np.nan
                results.append({"spike_param": spk_q, "cool_param": cool_q, "n": int(ep.shape[0]), "fwd_63d_mean": float(mean_63) if pd.notna(mean_63) else np.nan})

    elif mode == "zscore":
        spk_grid = (2.0, 2.5, 3.0)
        cool_grid = (-1.0, -0.5, 0.0)
        for spk_s in spk_grid:
            for cool_s in cool_grid:
                tmp = vix_df_base.copy()
                h_mean, h_std = tmp["High"].mean(), tmp["High"].std(ddof=1)
                c_mean, c_std = tmp["Close"].mean(), tmp["Close"].std(ddof=1)
                tmp["spike_thr"] = h_mean + spk_s * h_std
                tmp["cool_thr"]  = c_mean + cool_s * c_std
                sigs = find_signals_dynamic(tmp, use_low_for_cool)
                ep = attach_perf(sigs, fr_local, horizons)
                mean_63 = ep.get("fwd_63d", pd.Series(dtype=float)).mean() if not ep.empty else np.nan
                results.append({"spike_param": spk_s, "cool_param": cool_s, "n": int(ep.shape[0]), "fwd_63d_mean": float(mean_63) if pd.notna(mean_63) else np.nan})

    res = pd.DataFrame(results)
    if not res.empty:
        res = res.sort_values(["n", "fwd_63d_mean"], ascending=[False, False])
    return res

# =========================
# UI
# =========================
st.set_page_config(page_title="VIX Spike → Cool-off Event Study", layout="wide")
st.title("VIX Spike → Cool-off Event Study")

with st.sidebar:
    st.header("Data & Bench")
    vix_symbol = st.text_input("VIX symbol", value="^VIX")
    bench_symbol = st.selectbox("Benchmark", options=["^GSPC", "SPY"], index=0)

    st.header("Threshold Mode")
    mode = st.selectbox(
        "Mode",
        options=["rolling_percentile", "static_absolute", "static_percentile", "zscore"],
        index=0,
        help="Choose how spike and cool-off thresholds are defined."
    )

    st.subheader("Parameters")
    abs_spike = st.number_input("ABS spike (High ≥)", value=60.0, step=1.0)
    abs_cool  = st.number_input("ABS cool (Close/Low <)", value=30.0, step=1.0)

    full_pct_spike = st.slider("Full-sample percentile (spike thr)", 0.80, 0.999, 0.98, step=0.001)
    full_pct_cool  = st.slider("Full-sample percentile (cool thr)", 0.10, 0.90, 0.60, step=0.01)

    roll_window = st.number_input("Rolling window (trading days)", value=504, step=21, min_value=60)
    roll_pct_spike = st.slider("Rolling percentile (spike thr)", 0.80, 0.999, 0.98, step=0.001)
    roll_pct_cool  = st.slider("Rolling percentile (cool thr)", 0.10, 0.90, 0.60, step=0.01)

    zspike_sigma = st.number_input("Z-score spike σ", value=2.5, step=0.1)
    zcool_sigma  = st.number_input("Z-score cool σ", value=-0.5, step=0.1)

    st.header("Rules")
    use_low_for_cool = st.selectbox("Cool-off uses", options=["Close < thr", "Low < thr"], index=0) == "Low < thr"
    quiet_days = st.number_input("Quiet period (days)", value=126, step=21, min_value=0)

    st.header("Horizons")
    default_horizons = "21,63,126,252"
    horizons_str = st.text_input("Forward horizons (days, comma-separated)", value=default_horizons)
    horizons = tuple(int(x.strip()) for x in horizons_str.split(",") if x.strip().isdigit())

    show_robust = st.checkbox("Show robustness grid", value=True)

# =========================
# Data
# =========================
try:
    vix = load_yahoo(vix_symbol)
    bench = load_yahoo(bench_symbol)

    common_idx = vix.index.intersection(bench.index)
    vix = vix.loc[common_idx]
    bench = bench.loc[common_idx]

    vix_thr = build_thresholds(
        vix, mode,
        abs_spike, abs_cool,
        full_pct_spike, full_pct_cool,
        roll_window, roll_pct_spike, roll_pct_cool,
        zspike_sigma, zcool_sigma
    )

    signals = find_signals_dynamic(vix_thr, use_low_for_cool)
    fr = fwd_returns(bench["Close"], horizons)
    event_perf = attach_perf(signals, fr, horizons)
    summary_all = summarize_event_perf(event_perf, horizons)
    t_results = {f"fwd_{h}d": onesample_t(event_perf[f"fwd_{h}d"]) for h in horizons}

    signals_pruned = apply_quiet_period(signals, quiet_days)
    event_perf_pruned = attach_perf(signals_pruned, fr, horizons)
    summary_pruned = summarize_event_perf(event_perf_pruned, horizons)

    # =========================
    # Layout
    # =========================
    st.markdown(f"**Mode:** `{mode}`  |  **Cool-off:** `{'Low' if use_low_for_cool else 'Close'}`  |  **Quiet days:** `{quiet_days}`")

    # Top charts
    with st.expander("Charts", expanded=True):
        # VIX with thresholds
        vix_plot = vix_thr[["High", "Close"]].copy()
        vix_plot["Spike Threshold"] = vix_thr["spike_thr"]
        vix_plot["Cool Threshold"] = vix_thr["cool_thr"]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=vix_plot.index, y=vix_plot["High"], name="VIX High", mode="lines"))
        fig.add_trace(go.Scatter(x=vix_plot.index, y=vix_plot["Close"], name="VIX Close", mode="lines", opacity=0.6))
        fig.add_trace(go.Scatter(x=vix_plot.index, y=vix_plot["Spike Threshold"], name="Spike thr", mode="lines"))
        fig.add_trace(go.Scatter(x=vix_plot.index, y=vix_plot["Cool Threshold"], name="Cool thr", mode="lines"))

        # Mark signal dates
        if not signals.empty:
            fig.add_trace(go.Scatter(
                x=signals["signal_date"], y=vix_thr.loc[signals["signal_date"], "Close"],
                mode="markers", name="Signal date", marker=dict(size=8, symbol="x")
            ))
        fig.update_layout(title="VIX & Dynamic Thresholds", legend=dict(orientation="h"))
        st.plotly_chart(fig, use_container_width=True)

        # Benchmark price
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=bench.index, y=bench["Close"], name=f"{bench_symbol} Close", mode="lines"))
        if not signals.empty:
            yvals = bench.loc[signals["signal_date"], "Close"]
            fig2.add_trace(go.Scatter(x=signals["signal_date"], y=yvals, mode="markers", name="Signal on bench", marker=dict(size=7)))
        fig2.update_layout(title=f"{bench_symbol} Close with Signal Markers", legend=dict(orientation="h"))
        st.plotly_chart(fig2, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Signals (raw)")
        st.dataframe(signals)
        st.download_button("Download signals CSV", data=signals.to_csv(index=True).encode("utf-8"), file_name="signals.csv", mime="text/csv")

    with col2:
        st.subheader("Event Performance (raw)")
        st.dataframe(event_perf)
        st.download_button("Download event performance CSV", data=event_perf.to_csv(index=False).encode("utf-8"), file_name="event_performance.csv", mime="text/csv")

    st.subheader("Summary (all signals)")
    st.dataframe(summary_all)

    st.subheader("T-stats vs 0 mean (all signals)")
    st.json(t_results)

    st.subheader("Quiet-period pruned")
    st.dataframe(signals_pruned)
    st.dataframe(summary_pruned)

    if show_robust:
        st.subheader("Robustness grid (mean 63d return)")
        robust = robustness_dynamic(vix_thr, bench["Close"], horizons, mode, abs_spike, abs_cool, roll_window, use_low_for_cool)
        st.dataframe(robust)
        st.download_button("Download robustness CSV", data=robust.to_csv(index=False).encode("utf-8"), file_name="robustness.csv", mime="text/csv")

except Exception as e:
    st.error(f"Error: {e}")
    st.stop()
