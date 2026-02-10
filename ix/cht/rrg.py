import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, Optional
from ix.db.query import Series, MultiSeries
from .style import apply_academic_style


def _get_quadrant_style(x: float, y: float) -> Dict[str, str]:
    """Determines the quadrant and associated institutional color palette (0-centered)."""
    if x >= 0 and y >= 0:
        return {
            "name": "Leading",
            "color": "#22c55e",
            "bg": "rgba(34, 197, 94, 0.05)",
        }
    elif x >= 0 and y < 0:
        return {
            "name": "Weakening",
            "color": "#f59e0b",
            "bg": "rgba(245, 158, 11, 0.05)",
        }
    elif x < 0 and y < 0:
        return {
            "name": "Lagging",
            "color": "#ef4444",
            "bg": "rgba(239, 68, 68, 0.05)",
        }
    else:
        return {
            "name": "Improving",
            "color": "#3b82f6",
            "bg": "rgba(59, 130, 246, 0.05)",
        }


def _create_rrg_chart(
    title: str,
    freq: str,
    window: int,
    trail_len: int,
    tickers: Dict[str, str],
    benchmark_ticker: str,
) -> go.Figure:
    """
    Generates a Relative Rotation Graph (RRG).
    Handles data fetching, JdK-style normalization, and visualization.
    """
    try:
        # 1. Fetch Data
        ms = (
            MultiSeries(**{label: Series(ticker) for label, ticker in tickers.items()})
            .resample(freq)
            .ffill()
        )

        # Identify benchmark key dynamically
        benchmark_key = next(k for k, v in tickers.items() if v == benchmark_ticker)
        benchmark = ms[benchmark_key]
        assets = ms.drop(columns=[benchmark_key])

        smooth = 10

        # RS Ratio: Standardized Relative Strength
        rs = (assets.div(benchmark, axis=0)) * 100
        rs_mean = rs.rolling(window).mean()
        rs_std = rs.rolling(window).std()
        rs_z = (rs - rs_mean) / rs_std
        rs_ratio = (rs_z + 100).ewm(span=smooth).mean()

        # RS Momentum: Normalized ROC of RS Ratio
        rs_ratio_roc = rs_ratio.pct_change(1) * 100
        roc_mean = rs_ratio_roc.rolling(window).mean()
        roc_std = rs_ratio_roc.rolling(window).std()
        mom_z = (rs_ratio_roc - roc_mean) / roc_std
        rs_mom = (mom_z + 100).ewm(span=smooth).mean()

        # Transform to 0-centered basis points
        rs_ratio = (rs_ratio - 100) * 100
        rs_mom = (rs_mom - 100) * 100

        combined = pd.DataFrame()
        stats_list = []

        for col in assets.columns:
            x = rs_ratio[col]
            y = rs_mom[col]

            # Vector Velocity and Acceleration metrics (now in relative units)
            velocity = np.sqrt(x.diff() ** 2 + y.diff() ** 2)
            acceleration = velocity.diff()

            combined[f"{col}_X"] = x
            combined[f"{col}_Y"] = y

            if not x.dropna().empty and not y.dropna().empty:
                style = _get_quadrant_style(x.iloc[-1], y.iloc[-1])
                stats_list.append(
                    {
                        "Asset": col,
                        "Ratio": x.iloc[-1],
                        "Momentum": y.iloc[-1],
                        "Quadrant": style["name"],
                        "Color": style["color"],
                        "BG": style["bg"],
                        "Velocity": velocity.iloc[-1],
                        "Acceleration": acceleration.iloc[-1],
                    }
                )

        df = combined.dropna().tail(120)

        if df.empty:
            summary_stats = pd.DataFrame()
            latest_date = None
        else:
            summary_stats = pd.DataFrame(stats_list).sort_values(
                "Velocity", ascending=False
            )
            latest_date = df.index[-1]

    except Exception as e:
        raise Exception(f"RRG Data Error: {str(e)}")

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", showarrow=False)
        return fig

    # 2. Plotting
    fig = make_subplots(
        rows=1,
        cols=2,
        column_widths=[0.70, 0.30],
        specs=[[{"type": "scatter"}, {"type": "table"}]],
        horizontal_spacing=0.04,
    )

    asset_names = [c.replace("_X", "") for c in df.columns if "_X" in c]
    active_data = df.tail(trail_len)
    all_vals = active_data.values.flatten()

    # Dynamic axis scaling (0-centered)
    # Ensure a minimum range if data is flat, else fit to data
    if len(all_vals) > 0:
        max_deviation = max(abs(np.nanmax(all_vals)), abs(np.nanmin(all_vals)), 150)
    else:
        max_deviation = 150

    axis_limit = max_deviation * 1.2
    axis_range = [-axis_limit, axis_limit]

    for asset in asset_names:
        x_trail = df[f"{asset}_X"].tail(trail_len)
        y_trail = df[f"{asset}_Y"].tail(trail_len)

        if x_trail.empty or y_trail.empty:
            continue

        style = _get_quadrant_style(x_trail.iloc[-1], y_trail.iloc[-1])

        # 1. Trail Segments with Gradient
        # We draw segments with increasing opacity
        for i in range(len(x_trail) - 1):
            opacity = (i + 1) / len(x_trail) * 0.6
            fig.add_trace(
                go.Scatter(
                    x=x_trail.iloc[i : i + 2],
                    y=y_trail.iloc[i : i + 2],
                    mode="lines",
                    line=dict(width=2.5, color=style["color"]),
                    opacity=opacity,
                    hoverinfo="skip",
                    showlegend=False,
                    line_shape="spline",  # Smoother trails
                    line_smoothing=1.3,
                ),
                row=1,
                col=1,
            )

        # 2. Add Directional Arrows
        # Last segment arrow
        dx_last = x_trail.iloc[-1] - x_trail.iloc[-2]
        dy_last = y_trail.iloc[-1] - y_trail.iloc[-2]
        norm_last = np.sqrt(dx_last**2 + dy_last**2)

        if norm_last > 0:
            # Main arrowhead at the tip
            fig.add_annotation(
                x=x_trail.iloc[-1],
                y=y_trail.iloc[-1],
                ax=x_trail.iloc[-1] - dx_last * 12 / norm_last,
                ay=y_trail.iloc[-1] - dy_last * 12 / norm_last,
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                showarrow=True,
                arrowhead=2,
                arrowsize=1.2,
                arrowwidth=2.5,
                arrowcolor=style["color"],
                opacity=1.0,
                row=1,
                col=1,
            )

        # Intermediate arrow (at 1/2 of trail length)
        mid_idx = len(x_trail) // 2
        if mid_idx > 1:
            dx_mid = x_trail.iloc[mid_idx] - x_trail.iloc[mid_idx - 1]
            dy_mid = y_trail.iloc[mid_idx] - y_trail.iloc[mid_idx - 1]
            norm_mid = np.sqrt(dx_mid**2 + dy_mid**2)
            if norm_mid > 0:
                fig.add_annotation(
                    x=x_trail.iloc[mid_idx],
                    y=y_trail.iloc[mid_idx],
                    ax=x_trail.iloc[mid_idx] - dx_mid * 10 / norm_mid,
                    ay=y_trail.iloc[mid_idx] - dy_mid * 10 / norm_mid,
                    xref="x",
                    yref="y",
                    axref="x",
                    ayref="y",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1.0,
                    arrowwidth=1.5,
                    arrowcolor=style["color"],
                    opacity=0.3,
                    row=1,
                    col=1,
                )

        # 3. Label logic (Asset name)
        if "(" in asset:
            ticker_label = asset.split("(")[0].strip()
        else:
            ticker_label = asset

        fig.add_trace(
            go.Scatter(
                x=[x_trail.iloc[-1]],
                y=[y_trail.iloc[-1]],
                mode="text",
                text=[ticker_label],
                textposition="top center",
                textfont=dict(
                    size=10, color=style["color"], family="Inter, sans-serif"
                ),
                name=asset,
                hovertemplate=f"{asset}<br>Ratio: %{{x:.2f}}<br>Mom: %{{y:.2f}}<extra></extra>",
            ),
            row=1,
            col=1,
        )

    # Updated Quadrant positions (towards corners for clarity)
    offset = axis_limit * 0.8
    quad_config = [
        (offset, offset, "LEADING", "#22c55e"),
        (offset, -offset, "WEAKENING", "#f59e0b"),
        (-offset, -offset, "LAGGING", "#ef4444"),
        (-offset, offset, "IMPROVING", "#3b82f6"),
    ]

    for x_pos, y_pos, label, color in quad_config:
        fig.add_annotation(
            x=x_pos,
            y=y_pos,
            text=f"<b>{label}</b>",
            showarrow=False,
            font=dict(color=color, size=24, family="Outfit, sans-serif"),
            opacity=0.08,  # Maintain subtle background feel
            row=1,
            col=1,
        )

    # Simplified Quadrant Dividers
    fig.add_shape(
        type="line",
        x0=axis_range[0],
        y0=0,
        x1=axis_range[1],
        y1=0,
        line=dict(color="#cbd5e1", width=1, dash="dot"),
        row=1,
        col=1,
    )
    fig.add_shape(
        type="line",
        x0=0,
        y0=axis_range[0],
        x1=0,
        y1=axis_range[1],
        line=dict(color="#cbd5e1", width=1, dash="dot"),
        row=1,
        col=1,
    )

    # Summary Metrics Table (Sleeker design)
    if not summary_stats.empty:
        table_df = summary_stats.head(12)
        fig.add_trace(
            go.Table(
                header=dict(
                    values=["<b>Asset</b>", "<b>Quad</b>", "<b>Vel</b>", "<b>Acc</b>"],
                    fill_color="#1e293b",
                    align="left",
                    font=dict(size=12, color="#f8fafc", family="Inter"),
                    line_color="rgba(0,0,0,0)",
                ),
                cells=dict(
                    values=[
                        table_df["Asset"],
                        table_df["Quadrant"],
                        table_df["Velocity"].round(2),
                        table_df["Acceleration"].round(2),
                    ],
                    fill_color=[
                        ["rgba(255,255,255,0.05)"] * len(table_df),
                        table_df["BG"],
                    ],
                    align="left",
                    font=dict(size=11, color="#f1f5f9"),
                    line_color="rgba(255,255,255,0.05)",
                    height=28,
                ),
            ),
            row=1,
            col=2,
        )

    # Apply Academic Style
    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>"),
        showlegend=False,
        hovermode="closest",  # Override x unified for scatter plots
    )

    # Add Metadata Subtitle
    bench_name = next(k for k, v in tickers.items() if v == benchmark_ticker)
    as_of_str = latest_date.strftime("%B %d, %Y")

    # Manually add subtitle annotation since academic style might override or we want specific placement
    fig.add_annotation(
        text=f"Benchmark: {bench_name} | Horizon: {freq} | As of {as_of_str}",
        xref="paper",
        yref="paper",
        x=1.0,
        y=1.02,
        showarrow=False,
        font=dict(size=12, color="#64748b"),
        xanchor="right",
        yanchor="bottom",
    )

    grid_params = dict(
        showgrid=True,
        gridwidth=1,
        gridcolor="#f1f5f9",
        zeroline=True,
        zerolinewidth=2,
        zerolinecolor="#94a3b8",
        range=axis_range,
    )
    fig.update_xaxes(title="Relative Strength (RS-Ratio)", **grid_params, row=1, col=1)
    fig.update_yaxes(title="Momentum (RS-Momentum)", **grid_params, row=1, col=1)

    return fig


def RelativeRotation_UsSectors_Dynamic() -> go.Figure:
    """Dynamic RRG for US Sectors (Weekly data / 14-week window)."""
    tickers = {
        "SPY": "SPY US EQUITY:PX_LAST",
        "Tech (XLK)": "XLK US EQUITY:PX_LAST",
        "Energy (XLE)": "XLE US EQUITY:PX_LAST",
        "Health (XLV)": "XLV US EQUITY:PX_LAST",
        "Financials (XLF)": "XLF US EQUITY:PX_LAST",
        "Cons Disc (XLY)": "XLY US EQUITY:PX_LAST",
        "Cons Staples (XLP)": "XLP US EQUITY:PX_LAST",
        "Industrials (XLI)": "XLI US EQUITY:PX_LAST",
        "Utilities (XLU)": "XLU US EQUITY:PX_LAST",
        "Materials (XLB)": "XLB US EQUITY:PX_LAST",
        "Real Estate (XLRE)": "XLRE US EQUITY:PX_LAST",
        "Comm Svcs (XLC)": "XLC US EQUITY:PX_LAST",
    }
    return _create_rrg_chart(
        title="Relative Rotation - US Sectors (Dynamic)",
        freq="B",
        window=14,
        trail_len=12,
        tickers=tickers,
        benchmark_ticker="SPY US EQUITY:PX_LAST",
    )


def RelativeRotation_UsSectors_Tactical() -> go.Figure:
    """Tactical RRG for US Sectors (Weekly data / 14-week window)."""
    tickers = {
        "SPY": "SPY US EQUITY:PX_LAST",
        "Tech (XLK)": "XLK US EQUITY:PX_LAST",
        "Energy (XLE)": "XLE US EQUITY:PX_LAST",
        "Health (XLV)": "XLV US EQUITY:PX_LAST",
        "Financials (XLF)": "XLF US EQUITY:PX_LAST",
        "Cons Disc (XLY)": "XLY US EQUITY:PX_LAST",
        "Cons Staples (XLP)": "XLP US EQUITY:PX_LAST",
        "Industrials (XLI)": "XLI US EQUITY:PX_LAST",
        "Utilities (XLU)": "XLU US EQUITY:PX_LAST",
        "Materials (XLB)": "XLB US EQUITY:PX_LAST",
        "Real Estate (XLRE)": "XLRE US EQUITY:PX_LAST",
        "Comm Svcs (XLC)": "XLC US EQUITY:PX_LAST",
    }
    return _create_rrg_chart(
        title="Relative Rotation - US Sectors (Tactical)",
        freq="W-Fri",
        window=14,
        trail_len=12,
        tickers=tickers,
        benchmark_ticker="SPY US EQUITY:PX_LAST",
    )


def RelativeRotation_GlobalEquities_Dynamic() -> go.Figure:
    """Dynamic RRG for Global Equities (Weekly data / 14-week window)."""
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
    return _create_rrg_chart(
        title="Relative Rotation - Global Equities (Dynamic)",
        freq="B",
        window=14,
        trail_len=12,
        tickers=tickers,
        benchmark_ticker="ACWI US EQUITY:PX_LAST",
    )


def RelativeRotation_GlobalEquities_Tactical() -> go.Figure:
    """Tactical RRG for Global Equities (Weekly data / 14-week window)."""
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
    return _create_rrg_chart(
        title="Relative Rotation - Global Equities (Tactical)",
        freq="W-Fri",
        window=14,
        trail_len=12,
        tickers=tickers,
        benchmark_ticker="ACWI US EQUITY:PX_LAST",
    )


def RelativeRotation_KrSectors_Dynamic() -> go.Figure:
    """Dynamic RRG for KR Sectors (KOSPI) (Weekly data / 14-week window)."""
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
        "Utils (Elec/Gas)": "A017:PX_LAST",
        "Manufacturing": "A027:PX_LAST",
        "Metals": "A011:PX_LAST",
        "Machinery": "A012:PX_LAST",
        "Non-Metallic": "A010:PX_LAST",
        "Textile": "A006:PX_LAST",
        "Transp Equip": "A015:PX_LAST",
        "Food & Bev": "A005:PX_LAST",
        "Med & Precision": "A014:PX_LAST",
        "Elec & Electronics": "A013:PX_LAST",
        "Pharma": "A009:PX_LAST",
        "Paper & Wood": "A007:PX_LAST",
        "Chemicals": "A008:PX_LAST",
        "Telecom": "A020:PX_LAST",
    }
    return _create_rrg_chart(
        title="Relative Rotation - KR Sectors (Dynamic)",
        freq="B",
        window=14,
        trail_len=12,
        tickers=tickers,
        benchmark_ticker="KOSPI INDEX:PX_LAST",
    )


def RelativeRotation_KrSectors_Tactical() -> go.Figure:
    """Tactical RRG for KR Sectors (KOSPI) (Weekly data / 14-week window)."""
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
        "Utils (Elec/Gas)": "A017:PX_LAST",
        "Manufacturing": "A027:PX_LAST",
        "Metals": "A011:PX_LAST",
        "Machinery": "A012:PX_LAST",
        "Non-Metallic": "A010:PX_LAST",
        "Textile": "A006:PX_LAST",
        "Transp Equip": "A015:PX_LAST",
        "Food & Bev": "A005:PX_LAST",
        "Med & Precision": "A014:PX_LAST",
        "Elec & Electronics": "A013:PX_LAST",
        "Pharma": "A009:PX_LAST",
        "Paper & Wood": "A007:PX_LAST",
        "Chemicals": "A008:PX_LAST",
        "Telecom": "A020:PX_LAST",
    }
    return _create_rrg_chart(
        title="Relative Rotation - KR Sectors (Tactical)",
        freq="W-Fri",
        window=14,
        trail_len=12,
        tickers=tickers,
        benchmark_ticker="KOSPI INDEX:PX_LAST",
    )
