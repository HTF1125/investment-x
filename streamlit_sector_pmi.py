import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ix.db.query import MultiSeries, Series


ETF_TICKERS = {
    "S&P 500": "SPY US EQUITY:PX_LAST",
    "Tech": "XLK US EQUITY:PX_LAST",
    "Energy": "XLE US EQUITY:PX_LAST",
    "Health": "XLV US EQUITY:PX_LAST",
    "Financials": "XLF US EQUITY:PX_LAST",
    "Discretionary": "XLY US EQUITY:PX_LAST",
    "Staples": "XLP US EQUITY:PX_LAST",
    "Industrials": "XLI US EQUITY:PX_LAST",
    "Utilities": "XLU US EQUITY:PX_LAST",
    "Materials": "XLB US EQUITY:PX_LAST",
    "Real Estate": "XLRE US EQUITY:PX_LAST",
    "Comm Svcs": "XLC US EQUITY:PX_LAST",
}


@st.cache_data(show_spinner=False, ttl=600)
def load_data(freq: str) -> pd.DataFrame:
    data = MultiSeries(
        **{
            "ISM Manufacturing": Series("ISMPMI_M:PX_LAST", freq=freq),
            **{name: Series(code, freq=freq) for name, code in ETF_TICKERS.items()},
        }
    ).ffill()
    data.index = pd.to_datetime(data.index)
    return data.dropna(how="all")


def compute_sensitivity(df: pd.DataFrame) -> pd.DataFrame:
    x = df["ISM Manufacturing"].diff()
    out = []
    for name in ETF_TICKERS:
        y = df[name].pct_change()
        z = pd.concat([x.rename("x"), y.rename("y")], axis=1).dropna()
        if z.empty or z["x"].var() == 0:
            corr = np.nan
            beta = np.nan
        else:
            corr = z["y"].corr(z["x"])
            beta = z["y"].cov(z["x"]) / z["x"].var()
        out.append({"sector": name, "corr": corr, "beta": beta})
    result = pd.DataFrame(out).dropna()
    return result.sort_values("corr")


def build_chart(trend_metrics: dict[str, pd.DataFrame]) -> go.Figure:
    fig = go.Figure()
    dot_styles = {
        "3Y": dict(color="#22c55e", symbol="circle"),
        "5Y": dict(color="#60a5fa", symbol="diamond"),
        "10Y": dict(color="#f59e0b", symbol="square"),
    }
    line_styles = {
        "3Y": dict(color="#22c55e", width=2, dash="solid"),
        "5Y": dict(color="#60a5fa", width=2, dash="dash"),
        "10Y": dict(color="#f59e0b", width=2, dash="dot"),
    }
    regressions = []
    x_min, x_max = np.inf, -np.inf

    for label, mdf in trend_metrics.items():
        if len(mdf) < 2:
            continue
        dstyle = dot_styles.get(label, dict(color="#22d3ee", symbol="circle"))
        fig.add_trace(
            go.Scatter(
                x=mdf["corr"],
                y=mdf["beta"],
                mode="markers",
                marker=dict(
                    size=10,
                    symbol=dstyle["symbol"],
                    color=dstyle["color"],
                    line=dict(color="rgba(255,255,255,0.55)", width=1),
                ),
                customdata=np.stack([mdf["sector"]], axis=-1),
                hovertemplate="%{customdata[0]}<br>%{fullData.name}<br>corr: %{x:.3f}<br>beta: %{y:.3f}<extra></extra>",
                name=f"{label} Dots",
            )
        )
        x = mdf["corr"].to_numpy(dtype=float)
        y = mdf["beta"].to_numpy(dtype=float)
        slope, intercept = np.polyfit(x, y, 1)
        regressions.append((label, slope, intercept))
        x_min = min(x_min, float(np.min(x)))
        x_max = max(x_max, float(np.max(x)))

    if len(regressions) >= 2 and np.isfinite(x_min) and np.isfinite(x_max):
        xgrid = np.linspace(x_min, x_max, 150)
        ys = np.array([(m * xgrid + b) for _, m, b in regressions])
        y_low = ys.min(axis=0)
        y_high = ys.max(axis=0)
        fig.add_trace(
            go.Scatter(
                x=xgrid,
                y=y_low,
                mode="lines",
                line=dict(width=0, color="rgba(0,0,0,0)"),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=xgrid,
                y=y_high,
                mode="lines",
                fill="tonexty",
                fillcolor="rgba(148,163,184,0.18)",
                line=dict(width=0, color="rgba(0,0,0,0)"),
                hovertemplate="Range Channel<extra></extra>",
                name="Range Channel",
            )
        )

    for label, slope, intercept in regressions:
        xline = np.linspace(x_min, x_max, 100)
        yline = slope * xline + intercept
        fig.add_trace(
            go.Scatter(
                x=xline,
                y=yline,
                mode="lines",
                line=line_styles.get(label, dict(color="#94a3b8", width=2)),
                hovertemplate=f"{label} trend<extra></extra>",
                name=f"{label} Trend",
            )
        )

    fig.add_vline(x=0, line_width=1, line_color="rgba(255,255,255,0.25)")
    fig.add_hline(y=0, line_width=1, line_color="rgba(255,255,255,0.25)")

    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=0.68,
        y=0.90,
        text="Sectors that are more sensitive<br>to the business cycle",
        showarrow=False,
        font=dict(color="#4ade80", size=16),
    )

    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=0.60,
        y=0.78,
        text="↗",
        showarrow=False,
        font=dict(color="#4ade80", size=40),
    )

    fig.update_layout(
        template=None,
        paper_bgcolor="#050913",
        plot_bgcolor="#070d1a",
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title="Correlation to ISM Manufacturing PMI",
        yaxis_title="Beta to ISM Manufacturing PMI",
        font=dict(family="Ubuntu", size=13, color="#dbeafe"),
        legend=dict(
            orientation="h",
            y=1.02,
            x=0.01,
            bgcolor="rgba(15,23,42,0.7)",
            bordercolor="rgba(148,163,184,0.4)",
            borderwidth=1,
        ),
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(148,163,184,0.16)",
        zeroline=False,
        showline=True,
        linecolor="rgba(226,232,240,0.6)",
        mirror=True,
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(148,163,184,0.16)",
        zeroline=False,
        showline=True,
        linecolor="rgba(226,232,240,0.6)",
        mirror=True,
    )

    return fig


def main():
    st.set_page_config(
        page_title="ISM PMI Sector Sensitivity",
        layout="wide",
    )
    st.title("ISM PMI Sector Sensitivity Map")
    st.caption("Dark-cycle view: sector sensitivity to ISM Manufacturing PMI.")

    freq = st.selectbox("Frequency", options=["ME", "W-FRI", "B"], index=0)

    data = load_data(freq=freq)
    last_dt = data.index.max()

    trend_metrics = {}
    for years, label in [(3, "3Y"), (5, "5Y"), (10, "10Y")]:
        sub = data[data.index >= (last_dt - pd.DateOffset(years=years))]
        trend_metrics[label] = compute_sensitivity(sub)

    st.plotly_chart(build_chart(trend_metrics), use_container_width=True)
    table = (
        pd.concat(trend_metrics, names=["lookback"])
        .reset_index(level=0)
        .rename(columns={"lookback": "window"})
    )
    st.dataframe(table, use_container_width=True)


if __name__ == "__main__":
    main()
