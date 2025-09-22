import plotly.graph_objects as go
from ix.dash.settings import theme


def _px_from_rem(rem: str) -> int:
    """theme.space(n) -> "Xrem" 문자열을 px 정수로 변환"""
    return int(str(rem).replace("rem", "")) * 16


def apply_layout(fig: go.Figure, title: str = None) -> go.Figure:

    fig.update_layout(
        paper_bgcolor=theme.bg,
        plot_bgcolor=theme.bg_light,
        font=dict(
            color=theme.text,
            family="SF Pro Display, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif",
            size=12,
        ),
        title=dict(
            text=f"<b>{title}</b>" if title else None,
            font=dict(size=20, color=theme.text),
            y=0.98,
            x=0.02,
            xanchor="left",
            yanchor="top",
        ),
        # legend=dict(
        #     orientation="h",
        #     yanchor="bottom",
        #     y=1.02,  # Keep legend position but ensure title is higher
        #     xanchor="left",
        #     x=0.02,
        #     bgcolor="rgba(0,0,0,0)",
        #     bordercolor=theme.border,
        #     borderwidth=0,
        #     font=dict(color=theme.text, size=11),
        #     itemsizing="trace",
        # ),
        legend=dict(x=0.01, y=0.99, bordercolor="gray", borderwidth=1),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor=theme.bg_light,
            bordercolor=theme.border,
            font=dict(color=theme.text, size=11),
        ),
        margin=dict(
            l=_px_from_rem(theme.space(16)),
            r=_px_from_rem(theme.space(12)),
            t=_px_from_rem(theme.space(24)),
            b=_px_from_rem(theme.space(8)),
        ),
        autosize=True,
    )
    # 공통 그리드/축 라인
    fig.update_xaxes(
        showgrid=True,
        gridcolor=theme.border,
        gridwidth=1,
        zeroline=False,
        showline=True,
        linecolor=theme.border,
        linewidth=1,
        tickfont=dict(color=theme.text_light, size=10),
        title_font=dict(color=theme.text_light, size=11),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=theme.border,
        gridwidth=1,
        zeroline=True,
        zerolinecolor=theme.text_light,
        zerolinewidth=1,
        showline=True,
        linecolor=theme.border,
        linewidth=1,
        tickfont=dict(color=theme.text_light, size=10),
        title_font=dict(color=theme.text_light, size=11),
    )
    return fig


from ix import Series
import pandas as pd
import plotly.graph_objects as go


def credit_impulse_us():
    data = pd.DataFrame(
        {
            "BACROUTP": Series("US.BACROUTP", freq="ME"),
            "FRBBCABLCCBA@US": Series("FRBBCABLCCBA@US", freq="ME"),
            "FRBBCABLCRCBA@US": Series("FRBBCABLCRCBA@US", freq="ME"),
            "GDPN": Series("US.GDPN"),
        }
    )
    data.ffill(inplace=True)
    ff = data["BACROUTP"].add(data["FRBBCABLCCBA@US"]).add(data["FRBBCABLCRCBA@US"])
    gg = data["GDPN"]
    return ff.diff().rolling(12).sum().diff(12) / gg


def credit_impulse_cn():
    data = pd.DataFrame(
        {
            "CN": Series("CNBC2252509", freq="ME"),
            "GDPN": Series("CN.GDPNNSA", freq="ME"),
        }
    )
    data.ffill(inplace=True)
    return data["CN"].rolling(12).sum().diff(12) / data["GDPN"]


def credit_impulse_us_vs_cn():
    ci_us = credit_impulse_us().dropna()
    ci_cn = credit_impulse_cn().dropna()

    # Get latest values for legend
    latest_us_val = ci_us.iloc[-1] if not ci_us.empty else float("nan")
    latest_cn_val = ci_cn.iloc[-1] if not ci_cn.empty else float("nan")

    us_legend = f"US Credit Impulse ({latest_us_val:.2%})"
    cn_legend = f"China Credit Impulse ({latest_cn_val:.2%})"

    fig = go.Figure()

    # US Credit Impulse on primary y-axis
    fig.add_trace(
        go.Scatter(
            x=ci_us.index,
            y=ci_us,
            mode="lines",
            name=f"US Credit Impulse ({latest_us_val:.2%})",
            line=dict(color="royalblue"),
            yaxis="y1",
            hovertemplate="US Credit Impulse: %{y:.2%}<extra></extra>",
        )
    )
    # China Credit Impulse on secondary y-axis
    fig.add_trace(
        go.Scatter(
            x=ci_cn.index,
            y=ci_cn,
            mode="lines",
            name=cn_legend,
            line=dict(color="firebrick"),
            yaxis="y2",
            hovertemplate="China Credit Impulse: %{y:.2%}<extra></extra>",
        )
    )
    fig.update_layout(
        xaxis_title="Date",
        yaxis=dict(
            title="US Credit Impulse (YoY, % GDP)",
            tickformat=".0%",
        ),
        yaxis2=dict(
            title="China Credit Impulse (YoY, % GDP)",
            overlaying="y",
            side="right",
            tickformat=".0%",
        ),
        hovermode="x unified",
    )

    fig = apply_layout(fig, title = "Credit Impulse: US vs China")
    return fig


from ix import InvestorPositions
from ix.cht import apply_layout
import plotly.graph_objects as go


def investor_positions():

    investor_positions = InvestorPositions()

    # Create a new plotly figure and add traces from investor_positions data
    fig = go.Figure()

    for name, series in investor_positions.items():
        fig.add_trace(
            go.Scatter(x=series.index, y=series.values, mode="lines", name=name)
        )

    # Apply layout and show the plotly figure
    fig = apply_layout(fig, "Investor Positions")
    return fig
