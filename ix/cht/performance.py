from typing import Dict, List, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from ix.db.query import Series, MultiSeries

# Investment-X / Antigravity Premium Palette
ANTIGRAVITY_PALETTE = [
    "#38bdf8",  # Sky (Primary)
    "#a855f7",  # Purple (Secondary)
    "#f472b6",  # Pink
    "#10b981",  # Emerald
    "#fbbf24",  # Amber
    "#6366f1",  # Indigo
    "#f43f5e",  # Rose
    "#2dd4bf",  # Teal
    "#f97316",  # Orange
]


def get_color(name: str, index: int = 0) -> str:
    """Returns a consistent color for common names, or from palette by index."""
    fixed = {
        "America": ANTIGRAVITY_PALETTE[0],
        "US": ANTIGRAVITY_PALETTE[0],
        "Primary": ANTIGRAVITY_PALETTE[0],
        "S&P 500": ANTIGRAVITY_PALETTE[0],
        "SPY": ANTIGRAVITY_PALETTE[0],
        "Europe": ANTIGRAVITY_PALETTE[1],
        "EU": ANTIGRAVITY_PALETTE[1],
        "Japan": ANTIGRAVITY_PALETTE[2],
        "JP": ANTIGRAVITY_PALETTE[2],
        "Apac": ANTIGRAVITY_PALETTE[3],
        "Emerald": ANTIGRAVITY_PALETTE[3],
        "China": ANTIGRAVITY_PALETTE[3],
        "CN": ANTIGRAVITY_PALETTE[3],
        "KR": ANTIGRAVITY_PALETTE[4],  # Korea
        "Korea": ANTIGRAVITY_PALETTE[4],
        "UK": ANTIGRAVITY_PALETTE[5],
        "GB": ANTIGRAVITY_PALETTE[5],
        "World": "#f8fafc",
        "Aggregate": "#f8fafc",
        "Total": "#f8fafc",
        "Neutral": "#94a3b8",
        "Secondary": ANTIGRAVITY_PALETTE[6],  # Rose
    }
    # Clean name for matching
    cleaned = name.split("(")[0].strip()
    if cleaned in fixed:
        return fixed[cleaned]
    return ANTIGRAVITY_PALETTE[index % len(ANTIGRAVITY_PALETTE)]


def apply_academic_style(fig: go.Figure, force_dark: bool = True) -> go.Figure:
    """
    Applies a clean, academic/Goldman Sachs-style theme to the Plotly figure.
    Features:
    - Adaptive background (defaults to Dark for premium look)
    - Boxed axes (mirror=True)
    - Modern Inter/Outfit fonts
    - Top-left align title and legend
    """
    # Detect background theme or use force_dark
    bg = fig.layout.paper_bgcolor
    if bg in ["#0d0f12", "black", "#000000"] or force_dark:
        is_dark = True
    else:
        is_dark = False

    # 1. Base Template
    fig.update_layout(template="plotly_dark" if is_dark else "simple_white")

    # 2. Fonts & Colors
    font_family = "Inter, sans-serif"
    header_font = "Outfit, sans-serif"
    font_color = "#f8fafc" if is_dark else "#0f172a"
    bg_color = "#0d0f12" if is_dark else "white"
    grid_line_color = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0,0,0,0.05)"
    plot_bg = "rgba(255, 255, 255, 0.01)" if is_dark else "white"

    # 3. Layout General
    fig.update_layout(
        font=dict(family=font_family, color=font_color, size=12),
        margin=dict(l=70, r=40, t=90, b=60),  # More breathing room
        plot_bgcolor=plot_bg,
        paper_bgcolor=bg_color,
        hovermode="x unified",
        dragmode="pan",
        hoverlabel=dict(
            bgcolor="#1e293b" if is_dark else "white",
            font_color=font_color,
            bordercolor="rgba(255,255,255,0.1)" if is_dark else "#e2e8f0",
            font=dict(family=font_family, size=13),
        ),
    )

    # 4. Title Styling
    fig.update_layout(
        title=dict(
            x=0.02,
            y=0.96,
            xanchor="left",
            yanchor="top",
            font=dict(size=18, color=font_color, family=header_font, weight="bold"),
        )
    )

    # 5. Legend Styling (Horizontal at bottom or top-left)
    fig.update_layout(
        legend=dict(
            orientation="h",
            y=1.02,
            x=0.02,
            xanchor="left",
            yanchor="bottom",
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=12, color=font_color),
        )
    )

    # 6. Axis Styling (The "Boxed" look)
    axis_style = dict(
        showline=True,
        linewidth=1.5,
        linecolor="rgba(255,255,255,0.15)" if is_dark else "rgba(0,0,0,0.15)",
        mirror=True,
        ticks="outside",
        ticklen=6,
        tickcolor="rgba(255,255,255,0.3)" if is_dark else "rgba(0,0,0,0.3)",
        tickfont=dict(
            color=sub_color if "sub_color" in locals() else font_color,
            family=font_family,
            size=11,
        ),
        title_font=dict(color=font_color, family=header_font, size=13, weight="normal"),
        showgrid=True,
        gridcolor=grid_line_color,
        zeroline=True,
        zerolinecolor="rgba(255,255,255,0.2)" if is_dark else "rgba(0,0,0,0.2)",
        zerolinewidth=1,
    )

    fig.update_xaxes(**axis_style)
    fig.update_yaxes(**axis_style)

    # Secondary Axis handling
    for i in range(2, 11):
        fig.update_layout(
            {f"yaxis{i}": axis_style} if hasattr(fig.layout, f"yaxis{i}") else {}
        )
        fig.update_layout(
            {f"xaxis{i}": axis_style} if hasattr(fig.layout, f"xaxis{i}") else {}
        )

    # Ensure title and legend fonts are explicitly set
    fig.update_layout(
        title_font_color=font_color,
        legend_font_color=font_color,
    )

    # 7. Apply Standard Palette to traces for consistency
    for i, trace in enumerate(fig.data):
        color = ANTIGRAVITY_PALETTE[i % len(ANTIGRAVITY_PALETTE)]

        # Determine if we should override the color
        # We generally do, unless it's specifically a multi-color trace like a heatmap
        if trace.type in ["scatter", "bar"]:
            if hasattr(trace, "marker") and trace.marker.color is None:
                trace.marker.color = color
            if hasattr(trace, "line") and trace.line.color is None:
                trace.line.color = color

            # For Bar charts, we often want to force the color if it's the standard categorical view
            if trace.type == "bar" and (
                not hasattr(trace, "marker") or trace.marker.color is None
            ):
                trace.update(marker=dict(color=color))
            elif trace.type == "scatter" and (
                not hasattr(trace, "line") or trace.line.color is None
            ):
                trace.update(line=dict(color=color))

    return fig


def _create_error_fig(msg: str) -> go.Figure:
    """Helper to create error figure."""
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False)
    return fig


def _create_performance_bar_chart(
    tickers: Dict[str, str], title: str, period_days: int, resample_freq: str = "B"
) -> go.Figure:
    """Helper to create sorted horizontal performance bar charts."""
    try:
        df = (
            MultiSeries(**{label: Series(ticker) for label, ticker in tickers.items()})
            .resample(resample_freq)
            .ffill()
            .pct_change(period_days)
            .mul(100)
            .iloc[-50:]  # Fetch adequate history
            .copy()
        ).dropna(axis=1, how="all")

        latest_date = df.index[-1]

        # Latest snapshot
        latest = df.iloc[-1].sort_values(ascending=True)

    except Exception as e:
        # Instead of failing silently or printing, we return an error chart or re-raise
        # Ideally we log, but for now let's return an empty chart with message
        fig = go.Figure()
        fig.add_annotation(text=f"Data error: {str(e)}", showarrow=False)
        return fig

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", showarrow=False)
        return fig

    fig = make_subplots(specs=[[{"secondary_y": False}]])

    # Color logic: Emerald for > 0, Rose for < 0
    colors = ["#10b981" if x >= 0 else "#f43f5e" for x in latest.values]

    apply_academic_style(fig)
    is_dark = fig.layout.paper_bgcolor in ["#0d0f12", "black", "#000000"]
    font_color = "#e2e8f0" if is_dark else "#000000"
    as_of_color = "#94a3b8" if is_dark else "#475569"

    fig.add_trace(
        go.Bar(
            x=latest.values,
            y=latest.index,
            orientation="h",
            text=[f"{v:.1f}%" for v in latest.values],
            textposition="auto",
            textfont=dict(size=14, color="white" if is_dark else "black"),
            marker=dict(color=colors),
            hovertemplate="%{y}: %{x:.2f}%<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>",
            font=dict(size=22, color=font_color, family="Outfit"),
        ),
        xaxis=dict(
            title="Return (%)",
            title_font=dict(size=16, color=font_color, family="Outfit"),
            tickfont=dict(size=14, color=font_color),
        ),
        yaxis=dict(title="", tickfont=dict(size=14, color=font_color)),
        showlegend=False,
        hovermode="closest",
        margin=dict(t=100, l=160, r=40),  # Adjusted for longer labels
    )

    as_of_str = latest_date.strftime("%B %d, %Y")

    fig.add_annotation(
        text=f"As of {as_of_str}",
        xref="paper",
        yref="paper",
        x=1.0,
        y=1.05,
        showarrow=False,
        font=dict(size=14, color=as_of_color),
        xanchor="right",
        yanchor="bottom",
    )

    if not df.empty:
        fig.add_vline(
            x=0, line_width=1, line_color=font_color, opacity=0.3, layer="below"
        )

    return fig


def _create_multi_performance_bar_chart(
    tickers: Dict[str, str],
    title: str,
    periods: Dict[str, int],
    resample_freq: str = "B",
) -> go.Figure:
    """Helper to create grouped horizontal performance bar charts for multiple periods."""
    try:
        ms = MultiSeries(**{label: Series(ticker) for label, ticker in tickers.items()})
        df_base = ms.resample(resample_freq).ffill().copy()

        results = {}
        for period_label, days in periods.items():
            sdf = df_base.pct_change(days).mul(100).iloc[-1]
            results[period_label] = sdf

        df_perf = pd.DataFrame(results)
        if df_perf.empty:
            return _create_error_fig("No performance data calculated")

        # Sort by the 20D period for consistent ordering
        sort_col = "20D" if "20D" in df_perf.columns else list(periods.keys())[-1]
        df_perf = df_perf.sort_values(by=sort_col, ascending=True)

        latest_date = df_base.index[-1]

    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(text=f"Data error: {str(e)}", showarrow=False)
        return fig

    if df_perf.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", showarrow=False)
        return fig

    fig = go.Figure()

    # Distinct colors for periods
    # 20D (Cyan), 5D (Orange), 1D (Emerald)
    colors = {
        "20D": get_color("Sky", 0),
        "5D": get_color("Amber", 4),
        "1D": get_color("Emerald", 3),
    }

    apply_academic_style(fig)
    is_dark = fig.layout.paper_bgcolor in ["#0d0f12", "black", "#000000"]
    font_color = "#e2e8f0" if is_dark else "#000000"
    as_of_color = "#94a3b8" if is_dark else "#475569"

    for period_label in periods.keys():
        perf_values = df_perf[period_label]
        # Hide 1D and 5D by default, keep 20D visible
        visibility = True if period_label == "20D" else "legendonly"

        fig.add_trace(
            go.Bar(
                x=perf_values,
                y=df_perf.index,
                name=period_label,
                orientation="h",
                text=[f"{v:.1f}%" for v in perf_values],
                textposition="auto",
                textfont=dict(size=12, color="white" if is_dark else font_color),
                marker=dict(color=colors.get(period_label, "#94a3b8")),
                visible=visibility,
                hovertemplate=f"{period_label} - %{{y}}: %{{x:.2f}}%<extra></extra>",
            )
        )

    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>",
            font=dict(size=22, color=font_color, family="Outfit"),
        ),
        xaxis=dict(
            title="Return (%)",
            title_font=dict(size=16, color=font_color, family="Outfit"),
            tickfont=dict(size=14, color=font_color),
        ),
        yaxis=dict(title="", tickfont=dict(size=14, color=font_color)),
        barmode="group",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255,255,255,0)",
            font=dict(size=14, color=font_color),
        ),
        hovermode="closest",
        margin=dict(t=100, l=160, r=40),
    )

    as_of_str = latest_date.strftime("%B %d, %Y")
    fig.add_annotation(
        text=f"As of {as_of_str}",
        xref="paper",
        yref="paper",
        x=0.0,
        y=1.05,
        showarrow=False,
        font=dict(size=14, color=as_of_color),
        xanchor="left",
        yanchor="bottom",
    )

    fig.add_vline(x=0, line_width=1, line_color=font_color, opacity=0.3, layer="below")

    return fig


def _create_performance_heatmap(
    tickers: Dict[str, str],
    title: str,
    periods: Dict[str, int],
    resample_freq: str = "B",
) -> go.Figure:
    """Helper to create a high-density performance heatmap 'Pulse View'."""
    try:
        ms = MultiSeries(**{label: Series(ticker) for label, ticker in tickers.items()})
        df_base = ms.resample(resample_freq).ffill().copy()

        results = {}
        for period_label, days in periods.items():
            sdf = df_base.pct_change(days).mul(100).iloc[-1]
            results[period_label] = sdf

        df_perf = pd.DataFrame(results)
        # Sort by the longest period provided
        sort_col = list(periods.keys())[-1]
        df_perf = df_perf.sort_values(by=sort_col, ascending=True)
        latest_date = df_base.index[-1]
        as_of_str = latest_date.strftime("%b %d, %Y")

    except Exception as e:
        return _create_error_fig(f"Data error: {str(e)}")

    if df_perf.empty:
        return _create_error_fig("No data available")

    # Layout dimensions
    x_labels = list(periods.keys())
    y_labels = df_perf.index.tolist()
    z_values = df_perf.values

    # Absolute max for symmetric color scaling
    vmax = max(abs(df_perf.values.min()), abs(df_perf.values.max()), 5.0)

    # Value formatting for annotations
    text_values = [
        [f"{v:+.1f}%" if abs(v) >= 0.1 else "" for v in row] for row in z_values
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=z_values,
            x=x_labels,
            y=y_labels,
            zmin=-vmax,
            zmax=vmax,
            zmid=0,
            text=text_values,
            texttemplate="%{text}",
            xgap=2,
            ygap=2,
            colorscale=[
                [0, "#f43f5e"],  # Rose-500
                [0.25, "#fb7185"],  # Rose-400
                [0.4, "#fecdd3"],  # Rose-200
                [0.5, "#1e293b"],  # Slate-800 (Neutral)
                [0.6, "#d1fae5"],  # Emerald-100
                [0.75, "#34d399"],  # Emerald-400
                [1.0, "#10b981"],  # Emerald-500
            ],
            showscale=True,
            colorbar=dict(
                title=dict(text="Return %", font=dict(size=10)),
                thickness=12,
                len=0.8,
                tickfont=dict(size=10),
                outlinewidth=0,
                x=1.02,
            ),
            hovertemplate="<b>%{y}</b><br>Period: %{x}<br>Return: %{z:.2f}%<extra></extra>",
        )
    )

    apply_academic_style(fig)

    # Theme detection
    is_dark = fig.layout.paper_bgcolor in ["#0d0f12", "black", "#000000"]
    font_color = "#f8fafc" if is_dark else "#0f172a"
    sub_color = "#94a3b8" if is_dark else "#64748b"

    # Dynamic height calculation to prevent squashing (min 400px, 30px per row)
    dynamic_height = max(450, len(y_labels) * 32 + 150)

    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>",
            font=dict(size=22, color=font_color, family="Outfit"),
            x=0.01,
            y=0.98,
            xanchor="left",
            yanchor="top",
        ),
        xaxis=dict(
            side="top",
            tickfont=dict(size=13, color=font_color, family="Outfit"),
            showgrid=False,
            zeroline=False,
            constrain="domain",
        ),
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(size=12, color=font_color, family="Inter"),
            showgrid=False,
            zeroline=False,
        ),
        height=dynamic_height,
        margin=dict(t=130, b=40, l=160, r=80),
        plot_bgcolor="rgba(0,0,0,0)",
    )

    # Secondary title / Meta info
    fig.add_annotation(
        text=f"<b>PERFORMANCE PULSE</b> <span style='color:{sub_color}'>| {as_of_str}</span>",
        xref="paper",
        yref="paper",
        x=0.0,
        y=1.08,
        showarrow=False,
        font=dict(size=13, color=font_color),
        xanchor="left",
        yanchor="bottom",
    )

    # Critical: Set text font color for HEATMAP annotations specifically
    # Plotly doesn't apply layout.font to heatmap text automatically in a way that contrasts well
    fig.update_traces(
        textfont=dict(
            size=11,
            family="Inter, sans-serif",
            color="white",  # Always white for better contrast on Rose/Emerald
        )
    )

    return fig


def Performance_GlobalEquity() -> go.Figure:
    """Global Equity Market Performance Pulse (Heatmap)"""
    tickers = {
        "ACWI": "ACWI US EQUITY:PX_LAST",
        "US": "SPY US EQUITY:PX_LAST",
        "DM ex US": "IDEV US EQUITY:PX_LAST",
        "U.K.": "EWU US EQUITY:PX_LAST",
        "EAFE": "EFA US EQUITY:PX_LAST",
        "Europe": "FEZ US EQUITY:PX_LAST",
        "Germany": "EWG US EQUITY:PX_LAST",
        "Japan": "EWJ US EQUITY:PX_LAST",
        "Korea": "EWY US EQUITY:PX_LAST",
        "Australia": "EWA US EQUITY:PX_LAST",
        "Emerging": "VWO US EQUITY:PX_LAST",
        "China": "MCHI US EQUITY:PX_LAST",
        "India": "INDA US EQUITY:PX_LAST",
        "Brazil": "EWZ US EQUITY:PX_LAST",
        "Taiwan": "EWT US EQUITY:PX_LAST",
        "Vietnam": "VNM US EQUITY:PX_LAST",
    }
    return _create_performance_heatmap(
        tickers=tickers,
        title="Global Equity Performance Pulse",
        periods={"1D": 1, "5D": 5, "20D": 20, "60D": 60, "250D": 250},
        resample_freq="B",
    )


def Performance_UsSectors() -> go.Figure:
    """US Sector Performance Pulse (Heatmap)"""
    tickers = {
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
        "S&P 500": "SPY US EQUITY:PX_LAST",
    }
    return _create_performance_heatmap(
        tickers=tickers,
        title="US Sector Performance Pulse",
        periods={"1D": 1, "5D": 5, "20D": 20, "60D": 60, "250D": 250},
        resample_freq="B",
    )


def Performance_KrSectors() -> go.Figure:
    """KR Sector Performance Pulse (Heatmap)"""
    tickers = {
        "KOSPI": "KOSPI INDEX:PX_LAST",
        "IT Service": "A046:PX_LAST",
        "Construction": "A018:PX_LAST",
        "Finance": "A021:PX_LAST",
        "Insurance": "A025:PX_LAST",
        "Securities": "A024:PX_LAST",
        "Real Estate": "A045:PX_LAST",
        "Ent & Culture": "A047:PX_LAST",
        "Transp & Storage": "A019:PX_LAST",
        "Distribution": "A016:PX_LAST",
        "Gen Services": "A026:PX_LAST",
        "Utils": "A017:PX_LAST",
        "Manufacturing": "A027:PX_LAST",
        "Metals": "A011:PX_LAST",
        "Machinery": "A012:PX_LAST",
        "Textile": "A006:PX_LAST",
        "Transp Equip": "A015:PX_LAST",
        "Food & Bev": "A005:PX_LAST",
        "Elec & Elec": "A013:PX_LAST",
        "Pharma": "A009:PX_LAST",
        "Chemicals": "A008:PX_LAST",
        "Telecom": "A020:PX_LAST",
    }
    return _create_performance_heatmap(
        tickers=tickers,
        title="KR Sector Performance Pulse",
        periods={"1D": 1, "5D": 5, "20D": 20, "60D": 60, "250D": 250},
        resample_freq="B",
    )
