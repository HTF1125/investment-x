import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from ix.db.query import Series, MultiSeries, Offset
from ix.cht.style import apply_academic_style, add_zero_line, get_value_label, get_color


def US_CreditImpulse() -> go.Figure:
    """US Credit Impulse"""
    try:
        df = (
            MultiSeries(
                **{
                    "Bank Loans": Series("FRBBCABLBA@US:PX_LAST", scale=1)
                    .resample("W-Fri")
                    .last()
                    .ffill(),
                    "Commercial Paper": Series("USBC0311522:PX_LAST", scale=1)
                    .resample("W-Fri")
                    .last()
                    .ffill(),
                    "IG Corp": Series("MLC0AB:FACE_VAL", scale=1)
                    .resample("W-Fri")
                    .last()
                    .ffill(),
                    "HY Corp": Series("MLH0A0:FACE_VAL", scale=1)
                    .resample("W-Fri")
                    .last()
                    .ffill(),
                }
            )
            .ffill()
            .div(10**9)
            .diff(52)
            .diff(52)
            .iloc[-52 * 5 :]
        )
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": False}]])

    for idx, col in enumerate(df.columns):

        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df[col],
                name=get_value_label(df[col], col, ".2f"),
                hovertemplate=f"{col}: %{{y:.2f}}B<extra></extra>",
            )
        )

    # Total Line
    total = df.sum(axis=1)
    fig.add_trace(
        go.Scatter(
            x=total.index,
            y=total,
            name=get_value_label(total, "Total Impulse", ".2f"),
            mode="lines",
            line=dict(color=get_color("Neutral"), width=2, dash="dot"),
            hovertemplate="Total Impulse: %{y:.2f}B<extra></extra>",
            connectgaps=True,
        )
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>US Credit Impulse</b>"),
        yaxis_title="Impulse (Bn USD)",
        barmode="relative",
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        add_zero_line(fig)

    return fig


def US_CreditImpulseToGDP() -> go.Figure:
    """US Credit Impulse (% GDP)"""
    try:
        raw_impulse = (
            MultiSeries(
                **{
                    "Bank Loans": Series("FRBBCABLBA@US:PX_LAST", scale=1)
                    .resample("W-Fri")
                    .last()
                    .ffill(),
                    "Commercial Paper": Series("USBC0311522:PX_LAST", scale=1)
                    .resample("W-Fri")
                    .last()
                    .ffill(),
                    "IG Corp": Series("MLC0AB:FACE_VAL", scale=1)
                    .resample("W-Fri")
                    .last()
                    .ffill(),
                    "HY Corp": Series("MLH0A0:FACE_VAL", scale=1)
                    .resample("W-Fri")
                    .last()
                    .ffill(),
                }
            )
            .ffill()
            .div(10**9)
            .diff(52)
            .diff(52)
        )

        gdp = Series("US.GDPN:PX_LAST", freq="W-Fri", scale=10**9).ffill()
        gdp = gdp.reindex(raw_impulse.index).ffill()

        df = raw_impulse.div(gdp, axis=0).mul(100)
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": False}]])

    # Bars
    for idx, col in enumerate(df.columns):

        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df[col],
                name=get_value_label(df[col], col, ".2f"),
                hovertemplate=f"{col}: %{{y:.2f}}%<extra></extra>",
            )
        )

    # Total Line
    total = df.sum(axis=1)
    fig.add_trace(
        go.Scatter(
            x=total.index,
            y=total,
            name=get_value_label(total, "Total Impulse", ".2f"),
            mode="lines",
            line=dict(color=get_color("Neutral"), width=2, dash="dot"),
            hovertemplate="Total Impulse: %{y:.2f}%<extra></extra>",
            connectgaps=True,
        )
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>US Credit Impulse (% GDP)</b>"),
        yaxis_title="Impulse (% GDP)",
        barmode="relative",
    )

    if not df.empty:
        from datetime import datetime

        latest_date = df.index.max()
        start_date = datetime(latest_date.year - 10, 1, 1)
        fig.update_xaxes(range=[start_date, latest_date])
    return fig


def BankCreditOutlook() -> go.Figure:
    """Bank Credit Outlook"""
    try:
        credit_yoy = (
            Series("FRBBCABLBA@US:PX_LAST")
            .resample("W-Fri")
            .ffill()
            .pct_change(52)
            .mul(100)
        )
        standards = Series("USSU0486263:PX_LAST").resample("W-Fri").ffill()
        # Shift 12 months forward
        standards_lead = Offset(standards, days=52 * 7)

        df = MultiSeries(
            **{
                "Bank Credit YoY (%)": credit_yoy,
                "Bank Lending Standards (12M Lead)": standards_lead,
            }
        )
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Credit YoY (Left)
    col1 = "Bank Credit YoY (%)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col1],
            name=get_value_label(df[col1], col1, ".2f"),
            mode="lines",
            line=dict(width=2.5),
            hovertemplate=f"{col1}: %{{y:.2f}}%<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=False,
    )

    # 2. Lending Standards (Right)
    col2 = "Bank Lending Standards (12M Lead)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col2],
            name=get_value_label(df[col2], col2, ".2f"),
            mode="lines",
            line=dict(width=2.5),
            hovertemplate=f"{col2}: %{{y:.2f}}<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=True,
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>Bank Credit Outlook</b>"),
        yaxis=dict(title="Credit Growth (%)"),
        yaxis2=dict(
            title="Standards (Net % Tightening)",
            autorange="reversed",
            showgrid=False,
        ),
    )

    if not df.empty:
        from datetime import datetime

        latest_date = df.index.max()
        start_date = datetime(latest_date.year - 10, 1, 1)
        fig.update_xaxes(range=[start_date, latest_date])
    return fig


def _first_available_series(candidates: list[str], freq: str = "ME") -> tuple[str | None, pd.Series]:
    for code in candidates:
        s = Series(code, freq=freq).ffill().dropna()
        if not s.empty:
            return code, s
    return None, pd.Series(dtype=float)


def China_CreditImpulse() -> go.Figure:
    """
    China Credit Impulse (proxy):
    second difference of a broad credit/liquidity stock, scaled by nominal GDP.
    """
    credit_candidates = [
        "CN.CBASSET:PX_LAST",  # China central bank assets
        "CN.MAM2:PX_LAST",  # China M2
    ]
    gdp_candidates = [
        "CN.GDPN:PX_LAST",  # China nominal GDP
        "CN.NGDP:PX_LAST",
    ]

    credit_code, credit = _first_available_series(credit_candidates, freq="ME")
    gdp_code, gdp = _first_available_series(gdp_candidates, freq="ME")

    if credit.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Data Unavailable: no China credit proxy series found.",
            showarrow=False,
        )
        return fig

    # Proxy impulse: d(12m change of stock) / GDP * 100
    impulse_raw = credit.diff(12).diff(12)
    if not gdp.empty:
        gdp_aligned = gdp.reindex(impulse_raw.index).ffill()
        impulse = impulse_raw.div(gdp_aligned).mul(100)
        y_title = "Impulse (% GDP)"
        hover_suffix = "%"
    else:
        impulse = impulse_raw
        y_title = "Impulse (Level)"
        hover_suffix = ""

    impulse = impulse.dropna()
    impulse.name = "China Credit Impulse"

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=impulse.index,
            y=impulse,
            name=get_value_label(impulse, "China Credit Impulse", ".2f"),
            hovertemplate=f"China Credit Impulse: %{{y:.2f}}{hover_suffix}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=impulse.index,
            y=impulse.rolling(6).mean(),
            mode="lines",
            name=get_value_label(impulse.rolling(6).mean(), "6M Avg", ".2f"),
            line=dict(color=get_color("Neutral"), width=2, dash="dot"),
            hovertemplate=f"6M Avg: %{{y:.2f}}{hover_suffix}<extra></extra>",
            connectgaps=True,
        )
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>China Credit Impulse (Proxy)</b>"),
        yaxis_title=y_title,
        barmode="relative",
    )
    add_zero_line(fig)

    src_text = f"Credit: {credit_code}" if credit_code else "Credit: N/A"
    if gdp_code:
        src_text = f"{src_text} | GDP: {gdp_code}"
    else:
        src_text = f"{src_text} | GDP: N/A (unscaled)"
    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=0.01,
        y=0.01,
        xanchor="left",
        yanchor="bottom",
        text=src_text,
        showarrow=False,
        font=dict(size=10, color="#94a3b8"),
    )
    return fig


def _ytd_to_monthly_flow(ytd: pd.Series) -> pd.Series:
    s = ytd.dropna().sort_index().copy()
    if s.empty:
        return s
    out = s.diff()
    # January in YTD series is already one-month flow.
    jan_mask = s.index.month == 1
    out.loc[jan_mask] = s.loc[jan_mask]
    out = out.replace([pd.NA], float("nan"))
    return out


def China_CreditImpulse_GDPTracker(
    tracker_code: str = "CN.GDPNNSA:PX_LAST",
) -> go.Figure:
    """
    Chart style:
    - LHS: China Credit Impulse (Advanced 9 months)
    - RHS: China GDP Tracker (% y/y)
    """
    tsf_ytd = Series("CNBC6873725", freq="ME").ffill().dropna()
    if tsf_ytd.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Data Unavailable: CNBC6873725 not found.",
            showarrow=False,
        )
        return fig

    # TSF YTD flow (100mn CNY) -> monthly flow -> 12m flow
    tsf_monthly = _ytd_to_monthly_flow(tsf_ytd)
    tsf_12m = tsf_monthly.rolling(12).sum()

    # Quarterly nominal GDP -> annualized GDP (4Q sum) -> monthly aligned
    tracker_q = Series(tracker_code).ffill().dropna()
    if tracker_q.empty:
        tracker_q = Series("CN.FTEXP", freq="ME").ffill().dropna()
        gdp_tracker = tracker_q.pct_change(12).mul(100)
        # Fallback impulse when GDP level is unavailable: keep lower-volatility scale
        credit_impulse = tsf_12m.pct_change(12).mul(100).div(4.0)
    else:
        gdp_annual = tracker_q.rolling(4).sum()
        gdp_annual_m = gdp_annual.resample("ME").last().ffill()
        tsf_12m_aligned = tsf_12m.reindex(gdp_annual_m.index).ffill()
        credit_to_gdp = tsf_12m_aligned.div(gdp_annual_m).mul(100)
        # Standard credit impulse: YoY change in credit flow as share of GDP (pp).
        credit_impulse = credit_to_gdp.diff(12)
        gdp_tracker_q_yoy = tracker_q.pct_change(4).mul(100)
        gdp_tracker = gdp_tracker_q_yoy.resample("ME").last().ffill()

    credit_impulse = Offset(credit_impulse, months=9)
    credit_impulse.name = "Credit Impulse (Adv 9m), lhs"
    gdp_tracker.name = "China GDP Tracker (% y/y)"

    df = MultiSeries(
        **{
            credit_impulse.name: credit_impulse,
            gdp_tracker.name: gdp_tracker,
        }
    ).dropna(how="all")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    c1 = "#0b2f66"
    c2 = "#59b82f"

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[credit_impulse.name],
            name=get_value_label(df[credit_impulse.name], credit_impulse.name, ".2f"),
            mode="lines",
            line=dict(color=c1, width=3),
            hovertemplate="Credit Impulse (Adv 9m): %{y:.2f}<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[gdp_tracker.name],
            name=get_value_label(df[gdp_tracker.name], gdp_tracker.name, ".2f"),
            mode="lines",
            line=dict(color=c2, width=3),
            hovertemplate="China GDP Tracker: %{y:.2f}%<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title=dict(text="<b>Near-term support from the credit impulse will fade</b>"),
        paper_bgcolor="#efefef",
        plot_bgcolor="#efefef",
        font=dict(family="Ubuntu", size=12, color="#0f172a"),
        margin=dict(l=40, r=40, t=60, b=20),
        legend=dict(
            orientation="h",
            y=-0.12,
            x=0.5,
            xanchor="center",
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=12),
        ),
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(
        title_text="",
        secondary_y=False,
        showgrid=True,
        gridcolor="rgba(0,0,0,0.15)",
        zeroline=False,
    )
    fig.update_yaxes(
        title_text="",
        secondary_y=True,
        showgrid=False,
        zeroline=False,
    )
    return fig
