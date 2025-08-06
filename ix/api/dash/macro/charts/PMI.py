import pandas as pd
import plotly.graph_objects as go
from ix.db.query import *


class _PMI_SP500_YoY:

    title_text = "S&P500"
    yaxis_title = "PMI Level"
    yaxis2_title = ""

    def __init__(self) -> None:
        fig = go.Figure()
        self.ism = (
            MultiSeries(
                Series("MPMIUSMA Index:PX_LAST"),
                Series("ISMPMI_M:PX_LAST"),
            )
            .mean(axis=1)
            .dropna()
        )
        fig.add_trace(
            go.Scatter(
                x=self.ism.index,
                y=self.ism.values,
                name="PMI",
                mode="lines",
                line=dict(width=1, color="#1f77b4"),
                hovertemplate="<b>Date</b>: %{x|%b %Y}"
                + f"<br><b>PMI</b>: %{{y:.2f}}<extra></extra>",
                hoverlabel=dict(bgcolor="#333333", font_color="white"),
            )
        )


import pandas as pd
import plotly.graph_objects as go
from ix.db.query import Series, MultiSeries


class PMI_SP500_YoYChart:
    """
    PMI vs. S&P500 YoY 차트를 생성하는 클래스.
    클래스 변수로 기본 설정을 두고, 인스턴스 생성 시 일부를 재정의할 수 있음.
    """

    # 기본 색상
    PMI_COLOR = "#1f77b4"
    BASE_COLOR = "#ff7f0e"

    # 기본 제목 및 축 제목
    TITLE_TEXT = "PMI vs. S&P500 YoY"
    XAXIS_TITLE = "Date"
    YAXIS_TITLE = "PMI Level"
    YAXIS2_TITLE = f"S&P500 YoY (RHS)"

    # y축 범위 (PMI 수준). None이면 autorange
    YAXIS_RANGE = [30, 70]

    # 기본 보여줄 과거 연도 (예: 20년)
    LOOKBACK_YEARS = 20

    # 레이아웃 관련 공통 설정
    TEMPLATE = "plotly_dark"
    PAPER_BGCOLOR = "rgba(0,0,0,0)"
    PLOT_BGCOLOR = "rgba(0,0,0,0)"
    HOVERLABEL_BG = "#333333"
    HOVERLABEL_FONT_COLOR = "white"

    RANGESELECTOR_BUTTONS = [
        dict(count=5, label="5Y", step="year", stepmode="backward"),
        dict(count=10, label="10Y", step="year", stepmode="backward"),
        dict(count=20, label="20Y", step="year", stepmode="backward"),
        dict(step="all", label="All"),
    ]

    def __init__(self):
        self.fig = go.Figure()

        self.ism = (
            MultiSeries(
                Series("MPMIUSMA Index:PX_LAST"),
                Series("ISMPMI_M:PX_LAST"),
            )
            .mean(axis=1)
            .dropna()
        )
        self.sp500 = (
            Series("SPX Index:PX_LAST").resample("ME").last().pct_change(12).dropna()
        )

        # PMI 선 차트
        self.fig.add_trace(
            go.Scatter(
                x=self.ism.index,
                y=self.ism.values,
                name="PMI",
                mode="lines",
                line=dict(width=1, color=self.PMI_COLOR),
                hovertemplate="<b>Date</b>: %{x|%b %Y}"
                + f"<br><b>PMI</b>: %{{y:.2f}}<extra></extra>",
                hoverlabel=dict(
                    bgcolor=self.HOVERLABEL_BG, font_color=self.HOVERLABEL_FONT_COLOR
                ),
            )
        )

        # 베이스 시리즈 Bar (우측 y축)
        self.fig.add_trace(
            go.Bar(
                x=self.sp500.index,
                y=self.sp500.values,
                name=f"{self.BASE_NAME} YoY",
                yaxis="y2",
                opacity=0.6,
                marker_color=self.BASE_COLOR,
                marker_line_width=0,
                hovertemplate="<b>Date</b>: %{x|%b %Y}"
                + f"<br><b>{self.BASE_NAME} YoY</b>: %{{y:.2%}}<extra></extra>",
                hoverlabel=dict(
                    bgcolor=self.HOVERLABEL_BG, font_color=self.HOVERLABEL_FONT_COLOR
                ),
            )
        )

        # 레이아웃 설정
        self.fig.update_layout(
            template=self.TEMPLATE,
            paper_bgcolor=self.PAPER_BGCOLOR,
            plot_bgcolor=self.PLOT_BGCOLOR,
            title=dict(
                text=self.TITLE_TEXT,
                x=0.5,
                xanchor="center",
                font=dict(size=18, color="white"),
            ),
            hoverlabel=dict(
                bgcolor=self.HOVERLABEL_BG, font_color=self.HOVERLABEL_FONT_COLOR
            ),
            xaxis=dict(
                title=dict(
                    text=self.XAXIS_TITLE, font=dict(size=14, color="lightgray")
                ),
                showgrid=False,
                tickangle=0,
                tickfont=dict(size=11, color="lightgray"),
                tickformat="%b %Y",
                rangeslider=dict(visible=False),
                rangeselector=dict(
                    buttons=self.RANGESELECTOR_BUTTONS,
                    bgcolor=self.HOVERLABEL_BG,
                    activecolor="#555555",
                    font=dict(color="white", size=10),
                    bordercolor="lightgray",
                    borderwidth=1,
                ),
                linecolor="lightgray",
                mirror=True,
            ),
            yaxis=dict(
                title=dict(
                    text=self.YAXIS_TITLE, font=dict(size=14, color="lightgray")
                ),
                showgrid=False,
                zeroline=False,
                tickfont=dict(size=11, color="lightgray"),
                linecolor="lightgray",
                mirror=True,
                range=self.YAXIS_RANGE if self.YAXIS_RANGE is not None else None,
                autorange=(self.YAXIS_RANGE is None),
            ),
            yaxis2=dict(
                title=dict(
                    text=self.YAXIS2_TITLE, font=dict(size=14, color="lightgray")
                ),
                overlaying="y",
                side="right",
                tickformat=".0%",
                showgrid=False,
                zeroline=False,
                tickfont=dict(size=11, color="lightgray"),
                linecolor="lightgray",
                mirror=True,
            ),
            barmode="overlay",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=11, color="white"),
                bgcolor="rgba(0,0,0,0)",
                bordercolor="rgba(255,255,255,0.2)",
                borderwidth=1,
            ),
            hovermode="x unified",
            margin=dict(l=50, r=50, t=80, b=50),
        )

        # 기본 x축 범위: LOOKBACK_YEARS 만큼 뒤부터 현재까지
        if not self.ism.index.empty:
            end_date = self.ism.index.max()
            try:
                start_date = end_date - pd.DateOffset(years=self.LOOKBACK_YEARS)
            except Exception:
                # DateOffset(years=...) 지원 안 될 때 월 단위로 환산
                start_date = end_date - pd.DateOffset(months=12 * self.LOOKBACK_YEARS)
            self.fig.update_xaxes(range=[start_date, end_date])

        # 매년 1월에 수직선 표시
        for dt in self.ism.index:
            # pandas Timestamp 기준 month 속성 사용
            if dt.month == 1:
                self.fig.add_vline(
                    x=dt,
                    line_width=1,
                    line_dash="dot",
                    line_color="gray",
                    opacity=0.3,
                )
        # 0 기준 수평선 표시 (주로 베이스 시리즈가 % 변화이므로 중립선)
        self.fig.add_hline(
            y=0,
            line_width=1,
            line_dash="dash",
            line_color="gray",
            opacity=0.3,
        )


# 차트별 Figure 생성 함수 1: PMI vs S&P500 YoY
def PMI_SP500_YoY():
    base_series = (
        Series("SPX Index:PX_LAST").resample("ME").last().pct_change(12).dropna()
    )
    base_name = "S&P500"
    ism = (
        MultiSeries(
            Series("MPMIUSMA Index:PX_LAST"),
            Series("ISMPMI_M:PX_LAST"),
        )
        .mean(axis=1)
        .dropna()
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ism.index,
            y=ism.values,
            name="PMI",
            mode="lines",
            line=dict(width=1, color="#1f77b4"),
            hovertemplate="<b>Date</b>: %{x|%b %Y}"
            + f"<br><b>PMI</b>: %{{y:.2f}}<extra></extra>",
            hoverlabel=dict(bgcolor="#333333", font_color="white"),
        )
    )
    fig.add_trace(
        go.Bar(
            x=base_series.index,
            y=base_series.values,
            name=f"{base_name} YoY",
            yaxis="y2",
            opacity=0.6,
            marker_color="#ff7f0e",
            marker_line_width=0,
            hovertemplate="<b>Date</b>: %{x|%b %Y}"
            + f"<br><b>{base_name} YoY</b>: %{{y:.2%}}<extra></extra>",
            hoverlabel=dict(bgcolor="#333333", font_color="white"),
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title=dict(
            text=f"PMI vs. {base_name} YoY",
            x=0.5,
            xanchor="center",
            font=dict(size=18, color="white"),
        ),
        hoverlabel=dict(bgcolor="#333333", font_color="white"),
        xaxis=dict(
            title=dict(text="Date", font=dict(size=14, color="lightgray")),
            showgrid=False,
            tickangle=0,
            tickfont=dict(size=11, color="lightgray"),
            tickformat="%b %Y",
            rangeslider=dict(visible=False),
            rangeselector=dict(
                buttons=list(
                    [
                        dict(count=5, label="5Y", step="year", stepmode="backward"),
                        dict(count=10, label="10Y", step="year", stepmode="backward"),
                        dict(count=20, label="20Y", step="year", stepmode="backward"),
                        dict(step="all", label="All"),
                    ]
                ),
                bgcolor="#333333",
                activecolor="#555555",
                font=dict(color="white", size=10),
                bordercolor="lightgray",
                borderwidth=1,
            ),
            linecolor="lightgray",
            mirror=True,
        ),
        yaxis=dict(
            title=dict(text="PMI level", font=dict(size=14, color="lightgray")),
            showgrid=False,
            zeroline=False,
            tickfont=dict(size=11, color="lightgray"),
            linecolor="lightgray",
            mirror=True,
            range=[30, 70],
            autorange=False,
        ),
        yaxis2=dict(
            title=dict(
                text=f"{base_name} YoY (RHS)", font=dict(size=14, color="lightgray")
            ),
            overlaying="y",
            side="right",
            tickformat=".0%",
            showgrid=False,
            zeroline=False,
            tickfont=dict(size=11, color="lightgray"),
            linecolor="lightgray",
            mirror=True,
        ),
        barmode="overlay",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color="white"),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(255,255,255,0.2)",
            borderwidth=1,
        ),
        hovermode="x unified",
        margin=dict(l=50, r=50, t=80, b=50),
    )

    if not ism.index.empty:
        end_date = ism.index.max()
        try:
            start_date = end_date - pd.DateOffset(years=20)
        except Exception:
            start_date = end_date - pd.DateOffset(months=240)
        fig.update_xaxes(range=[start_date, end_date])

    for dt in ism.index:
        if dt.month == 1:
            fig.add_vline(
                x=dt, line_width=1, line_dash="dot", line_color="gray", opacity=0.3
            )
    fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="gray", opacity=0.3)
    return fig


# 차트별 Figure 생성 함수 2: PMI vs Treasury 10Y YoY
def PMI_Treasury10Y_YoY():
    base_series = (
        Series("TRYUS10Y:PX_YTM").resample("ME").last().pct_change(12).dropna()
    )
    base_name = "Treasury 10Y"
    ism = (
        MultiSeries(
            Series("MPMIUSMA Index:PX_LAST"),
            Series("ISMPMI_M:PX_LAST"),
        )
        .mean(axis=1)
        .dropna()
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ism.index,
            y=ism.values,
            name="PMI",
            mode="lines",
            line=dict(width=2, color="#1f77b4"),
            hovertemplate="<b>Date</b>: %{x|%b %Y}"
            + f"<br><b>PMI</b>: %{{y:.2f}}<extra></extra>",
            hoverlabel=dict(bgcolor="#333333", font_color="white"),
        )
    )
    fig.add_trace(
        go.Bar(
            x=base_series.index,
            y=base_series.values,
            name=f"{base_name} YoY",
            yaxis="y2",
            opacity=0.6,
            marker_color="#2ca02c",
            marker_line_width=0,
            hovertemplate="<b>Date</b>: %{x|%b %Y}"
            + f"<br><b>{base_name} YoY</b>: %{{y:.2%}}<extra></extra>",
            hoverlabel=dict(bgcolor="#333333", font_color="white"),
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title=dict(
            text=f"PMI vs. {base_name} YoY",
            x=0.5,
            xanchor="center",
            font=dict(size=18, color="white"),
        ),
        hoverlabel=dict(bgcolor="#333333", font_color="white"),
        xaxis=dict(
            title=dict(text="Date", font=dict(size=14, color="lightgray")),
            showgrid=False,
            tickangle=0,
            tickfont=dict(size=11, color="lightgray"),
            tickformat="%b %Y",
            rangeslider=dict(visible=False),
            rangeselector=dict(
                buttons=list(
                    [
                        dict(count=5, label="5Y", step="year", stepmode="backward"),
                        dict(count=10, label="10Y", step="year", stepmode="backward"),
                        dict(count=20, label="20Y", step="year", stepmode="backward"),
                        dict(step="all", label="All"),
                    ]
                ),
                bgcolor="#333333",
                activecolor="#555555",
                font=dict(color="white", size=10),
                bordercolor="lightgray",
                borderwidth=1,
            ),
            linecolor="lightgray",
            mirror=True,
        ),
        yaxis=dict(
            title=dict(text="PMI level", font=dict(size=14, color="lightgray")),
            showgrid=False,
            zeroline=False,
            tickfont=dict(size=11, color="lightgray"),
            linecolor="lightgray",
            mirror=True,
            range=[30, 70],
            autorange=False,
        ),
        yaxis2=dict(
            title=dict(
                text=f"{base_name} YoY (RHS)", font=dict(size=14, color="lightgray")
            ),
            overlaying="y",
            side="right",
            tickformat=".0%",
            showgrid=False,
            zeroline=False,
            tickfont=dict(size=11, color="lightgray"),
            linecolor="lightgray",
            mirror=True,
        ),
        barmode="overlay",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color="white"),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(255,255,255,0.2)",
            borderwidth=1,
        ),
        hovermode="x unified",
        margin=dict(l=50, r=50, t=80, b=50),
    )

    if not ism.index.empty:
        end_date = ism.index.max()
        try:
            start_date = end_date - pd.DateOffset(years=20)
        except Exception:
            start_date = end_date - pd.DateOffset(months=240)
        fig.update_xaxes(range=[start_date, end_date])

    for dt in ism.index:
        if dt.month == 1:
            fig.add_vline(
                x=dt, line_width=1, line_dash="dot", line_color="gray", opacity=0.3
            )
    fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="gray", opacity=0.3)
    return fig


# 차트별 Figure 생성 함수 3: PMI vs WTI YoY
def PMI_WTI_YoY():
    base_series = (
        Series("CL1 Comdty:PX_LAST").resample("ME").last().pct_change(12).dropna()
    )
    base_name = "WTI"
    ism = (
        MultiSeries(
            Series("MPMIUSMA Index:PX_LAST"),
            Series("ISMPMI_M:PX_LAST"),
        )
        .mean(axis=1)
        .dropna()
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ism.index,
            y=ism.values,
            name="PMI",
            mode="lines",
            line=dict(width=2, color="#1f77b4"),
            hovertemplate="<b>Date</b>: %{x|%b %Y}"
            + f"<br><b>PMI</b>: %{{y:.2f}}<extra></extra>",
            hoverlabel=dict(bgcolor="#333333", font_color="white"),
        )
    )
    fig.add_trace(
        go.Bar(
            x=base_series.index,
            y=base_series.values,
            name=f"{base_name} YoY",
            yaxis="y2",
            opacity=0.6,
            marker_color="#2ca02c",
            marker_line_width=0,
            hovertemplate="<b>Date</b>: %{x|%b %Y}"
            + f"<br><b>{base_name} YoY</b>: %{{y:.2%}}<extra></extra>",
            hoverlabel=dict(bgcolor="#333333", font_color="white"),
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title=dict(
            text=f"PMI vs. {base_name} YoY",
            x=0.5,
            xanchor="center",
            font=dict(size=18, color="white"),
        ),
        hoverlabel=dict(bgcolor="#333333", font_color="white"),
        xaxis=dict(
            title=dict(text="Date", font=dict(size=14, color="lightgray")),
            showgrid=False,
            tickangle=0,
            tickfont=dict(size=11, color="lightgray"),
            tickformat="%b %Y",
            rangeslider=dict(visible=False),
            rangeselector=dict(
                buttons=list(
                    [
                        dict(count=5, label="5Y", step="year", stepmode="backward"),
                        dict(count=10, label="10Y", step="year", stepmode="backward"),
                        dict(count=20, label="20Y", step="year", stepmode="backward"),
                        dict(step="all", label="All"),
                    ]
                ),
                bgcolor="#333333",
                activecolor="#555555",
                font=dict(color="white", size=10),
                bordercolor="lightgray",
                borderwidth=1,
            ),
            linecolor="lightgray",
            mirror=True,
        ),
        yaxis=dict(
            title=dict(text="PMI level", font=dict(size=14, color="lightgray")),
            showgrid=False,
            zeroline=False,
            tickfont=dict(size=11, color="lightgray"),
            linecolor="lightgray",
            mirror=True,
            range=[30, 70],
            autorange=False,
        ),
        yaxis2=dict(
            title=dict(
                text=f"{base_name} YoY (RHS)", font=dict(size=14, color="lightgray")
            ),
            overlaying="y",
            side="right",
            tickformat=".0%",
            showgrid=False,
            zeroline=False,
            tickfont=dict(size=11, color="lightgray"),
            linecolor="lightgray",
            mirror=True,
        ),
        barmode="overlay",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color="white"),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(255,255,255,0.2)",
            borderwidth=1,
        ),
        hovermode="x unified",
        margin=dict(l=50, r=50, t=80, b=50),
    )

    if not ism.index.empty:
        end_date = ism.index.max()
        try:
            start_date = end_date - pd.DateOffset(years=20)
        except Exception:
            start_date = end_date - pd.DateOffset(months=240)
        fig.update_xaxes(range=[start_date, end_date])

    for dt in ism.index:
        if dt.month == 1:
            fig.add_vline(
                x=dt, line_width=1, line_dash="dot", line_color="gray", opacity=0.3
            )
    fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="gray", opacity=0.3)
    return fig


import pandas as pd
import plotly.graph_objects as go
from ix.db.query import *


def US_OECD_CLI_SP500():

    oecd_cli_rocc = MonthEndOffset(
        Diff(Diff(Series("USA.LOLITOAA.STSA:PX_LAST"), 1), 1), 1
    )
    base_series = (
        Series("SPX Index:PX_LAST").resample("ME").last().pct_change().dropna()
    )
    base_name = "S&P500"

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=oecd_cli_rocc.index,
            y=oecd_cli_rocc.values,
            name="PMI",
            mode="lines",
            line=dict(width=2, color="#1f77b4"),
            hovertemplate="<b>Date</b>: %{x|%b %Y}"
            + f"<br><b>PMI</b>: %{{y:.2f}}<extra></extra>",
            hoverlabel=dict(bgcolor="#333333", font_color="white"),
        )
    )
    fig.add_trace(
        go.Bar(
            x=base_series.index,
            y=base_series.values,
            name=f"{base_name} YoY",
            yaxis="y2",
            opacity=0.6,
            marker_color="#ff7f0e",
            marker_line_width=0,
            hovertemplate="<b>Date</b>: %{x|%b %Y}"
            + f"<br><b>{base_name} YoY</b>: %{{y:.2%}}<extra></extra>",
            hoverlabel=dict(bgcolor="#333333", font_color="white"),
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title=dict(
            text=f"PMI vs. {base_name} YoY",
            x=0.5,
            xanchor="center",
            font=dict(size=18, color="white"),
        ),
        hoverlabel=dict(bgcolor="#333333", font_color="white"),
        xaxis=dict(
            title=dict(text="Date", font=dict(size=14, color="lightgray")),
            showgrid=False,
            tickangle=0,
            tickfont=dict(size=11, color="lightgray"),
            tickformat="%b %Y",
            rangeslider=dict(visible=False),
            rangeselector=dict(
                buttons=list(
                    [
                        dict(count=5, label="5Y", step="year", stepmode="backward"),
                        dict(count=10, label="10Y", step="year", stepmode="backward"),
                        dict(count=20, label="20Y", step="year", stepmode="backward"),
                        dict(step="all", label="All"),
                    ]
                ),
                bgcolor="#333333",
                activecolor="#555555",
                font=dict(color="white", size=10),
                bordercolor="lightgray",
                borderwidth=1,
            ),
            linecolor="lightgray",
            mirror=True,
        ),
        yaxis=dict(
            title=dict(text="PMI level", font=dict(size=14, color="lightgray")),
            showgrid=False,
            zeroline=False,
            tickfont=dict(size=11, color="lightgray"),
            linecolor="lightgray",
            mirror=True,
            range=[-0.15, 0.15],
            autorange=False,
        ),
        yaxis2=dict(
            title=dict(
                text=f"{base_name} YoY (RHS)", font=dict(size=14, color="lightgray")
            ),
            overlaying="y",
            side="right",
            tickformat=".0%",
            showgrid=False,
            zeroline=False,
            tickfont=dict(size=11, color="lightgray"),
            linecolor="lightgray",
            mirror=True,
            range=[-0.2, 0.2],
            autorange=False,
        ),
        barmode="overlay",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color="white"),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(255,255,255,0.2)",
            borderwidth=1,
        ),
        hovermode="x unified",
        margin=dict(l=50, r=50, t=80, b=50),
    )

    if not oecd_cli_rocc.index.empty:
        end_date = oecd_cli_rocc.index.max()
        try:
            start_date = end_date - pd.DateOffset(years=20)
        except Exception:
            start_date = end_date - pd.DateOffset(months=240)
        fig.update_xaxes(range=[start_date, end_date])

    for dt in oecd_cli_rocc.index:
        if dt.month == 1:
            fig.add_vline(
                x=dt, line_width=1, line_dash="dot", line_color="gray", opacity=0.3
            )
    fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="gray", opacity=0.3)
    return fig
