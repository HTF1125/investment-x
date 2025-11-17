"""
Risk Management Dashboard Page
Converted from Streamlit app to Dash format
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import html, dcc, callback, Output, Input, State
import dash
from datetime import datetime, date
import os
from dash.exceptions import PreventUpdate
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from ix.web.pages.risk.gauge import make_gauge

# Register Page (will be called when app is instantiated)
try:
    dash.register_page(
        __name__, path="/risk", title="Risk Management", name="Risk Management"
    )
except dash.exceptions.PageError:
    # Page registration will be handled by the main app
    pass


from ix.db.query import NumOfOECDLeadingPositiveMoM


def create_oecd_chart():
    """Create OECD CLI chart"""
    # Get OECD CLI positive percentage (already calculated)
    positive_pct = NumOfOECDLeadingPositiveMoM()

    fig = go.Figure()

    # Determine color based on latest value
    latest_value = positive_pct.iloc[-1] if len(positive_pct) > 0 else 50

    if latest_value >= 75:
        line_color = "#10b981"  # Green
        fill_color = "rgba(16, 185, 129, 0.2)"
    elif latest_value >= 50:
        line_color = "#3b82f6"  # Blue
        fill_color = "rgba(59, 130, 246, 0.2)"
    elif latest_value >= 25:
        line_color = "#f59e0b"  # Yellow
        fill_color = "rgba(245, 158, 11, 0.2)"
    else:
        line_color = "#dc2626"  # Red
        fill_color = "rgba(220, 38, 38, 0.2)"

    # Add filled area chart for positive percentage
    fig.add_trace(
        go.Scatter(
            x=positive_pct.index,
            y=positive_pct.values,
            mode="lines+markers",
            name="OECD CLI 양수 비율 (%)",
            line=dict(color=line_color, width=3),
            marker=dict(size=8, color=line_color),
            fill="tonexty",
            fillcolor=fill_color,
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>"
            + "OECD CLI 양수 비율: %{y:.1f}%<br>"
            + "<extra></extra>",
        )
    )

    # Add horizontal reference lines with Korean labels
    fig.add_hline(
        y=50,
        line_dash="dash",
        line_color="#cbd5e0",
        line_width=2,
        annotation_text="50% (중립)",
        annotation_position="top right",
        annotation_font_size=12,
        annotation_font_color="#ffffff",
    )
    fig.add_hline(
        y=75,
        line_dash="dot",
        line_color="#10b981",
        line_width=2,
        annotation_text="75% (강한 긍정)",
        annotation_position="top right",
        annotation_font_size=12,
        annotation_font_color="#ffffff",
    )
    fig.add_hline(
        y=25,
        line_dash="dot",
        line_color="#dc2626",
        line_width=2,
        annotation_text="25% (강한 부정)",
        annotation_position="bottom right",
        annotation_font_size=12,
        annotation_font_color="#ffffff",
    )

    # Add current value annotation
    if len(positive_pct) > 0:
        fig.add_annotation(
            x=positive_pct.index[-1],
            y=latest_value,
            text=f"현재: {latest_value:.1f}%",
            showarrow=True,
            arrowhead=2,
            arrowcolor=line_color,
            bgcolor="rgba(30, 41, 59, 0.9)",
            bordercolor=line_color,
            borderwidth=1,
            font=dict(size=12, color="#ffffff"),
        )

    # Update layout with enhanced styling
    fig.update_layout(
        title={
            "text": "<b>OECD CLI 서브인덱스: 양수 비율</b><br>"
            + '<span style="font-size:14px; color:#cbd5e0">OECD CLI 서브인덱스 중 양수 모멘텀을 보이는 비율</span>',
            "x": 0.5,
            "xanchor": "center",
            "font": {"family": "Inter, sans-serif", "size": 18},
        },
        xaxis_title="날짜",
        yaxis_title="양수 비율 (%)",
        height=450,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(30, 41, 59, 0.9)",
            bordercolor="rgba(71, 85, 105, 0.5)",
            borderwidth=1,
            font=dict(size=12, color="#ffffff"),
        ),
        hovermode="x unified",
        plot_bgcolor="rgba(30, 41, 59, 0.3)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=12, color="#ffffff"),
        margin=dict(l=60, r=60, t=120, b=60),
    )

    # Update axes with better styling
    fig.update_xaxes(
        gridcolor="rgba(71, 85, 105, 0.3)",
        gridwidth=1,
        showgrid=True,
        title_font=dict(size=14, color="#ffffff"),
        tickfont=dict(size=12, color="#cbd5e0"),
    )
    fig.update_yaxes(
        gridcolor="rgba(71, 85, 105, 0.3)",
        gridwidth=1,
        showgrid=True,
        range=[0, 100],
        title_font=dict(size=14, color="#ffffff"),
        tickfont=dict(size=12, color="#cbd5e0"),
    )

    return fig


import pandas as pd
from ix.db import Series


def get_index():
    """Load and process index data"""
    try:
        data = pd.DataFrame(
            {
                "코스피": Series("KOSPI INDEX:PX_LAST", freq="W-Fri"),
                "S&P 500": Series("SPX INDEX:PX_LAST", freq="W-Fri"),
                "한국CD91": Series("BONDHANYLD920:PX_YTM", freq="W-Fri"),
                "한국 3년": Series("TRYKR3Y:PX_YTM", freq="W-Fri"),
                "한국 10년": Series("BONDAVG01@10Y:PX_YTM", freq="W-Fri"),
                "미국 10년": Series("GVO:TR10Y:PX_YTM", freq="W-Fri"),
                "미국 - 한국 10년": (
                    Series("GVO:TR10Y:PX_YTM", freq="W-Fri")
                    - Series("BONDAVG01@10Y:PX_YTM", freq="W-Fri")
                ),
                "한국회사채스프레드(AA-)": (
                    Series("BONDAVG57:PX_YTM", freq="W-Fri").ffill()
                    - Series("TRYKR3Y:PX_YTM", freq="W-Fri").ffill()
                ),
                "달러 - 원 환율": Series("USDKRW CURNCY:PX_LAST", freq="W-Fri"),
            }
        ).ffill()

        data = data[
            [
                "코스피",
                "S&P 500",
                "한국CD91",
                "한국 10년",
                "미국 10년",
                "미국 - 한국 10년",
                "한국회사채스프레드(AA-)",
                "달러 - 원 환율",
            ]
        ]

        return data
    except Exception as e:
        print(f"Error loading index data: {e}")
        return pd.DataFrame()


def create_risk_metrics():
    """Create risk metrics cards"""
    try:
        data = get_index().loc["2022":].ffill()

        if data.empty:
            return html.Div(
                "No data available",
                style={
                    "color": "#dc2626",
                    "background": "rgba(239, 68, 68, 0.1)",
                    "padding": "12px",
                    "borderRadius": "8px",
                    "borderLeft": "4px solid #dc2626",
                    "margin": "10px 0",
                },
            )

        latest_date = data.index[-1]
        today = date.today()
        if latest_date.date() > today:
            latest_date = today
        num_indices = len(data.columns)
        latest_values = data.iloc[-1]

        # Calculate sigma values for all indices
        sigma_values = []
        for name, series in data.items():
            if name in ["코스피", "S&P 500", "달러 - 원 환율"]:
                d = series.resample("W").last().pct_change(5).dropna().loc["2000":]
                if name == "달러 - 원 환율":
                    d = d * (-1)
            else:
                d = series.resample("W").last().diff(5).dropna().loc["2000":] * (-1)
            window = 52 * 2  # 104 weeks

            if len(d) < window:
                continue

            rolling_mean = d.rolling(window).mean()
            rolling_std = d.rolling(window).std()
            mean = rolling_mean.iloc[-1]
            std = rolling_std.iloc[-1]
            current = d.iloc[-1]

            if pd.notna(mean) and pd.notna(std) and pd.notna(current) and std != 0:
                z = (current - mean) / std
                if pd.notna(z):
                    sigma_values.append(z)

        # Calculate average sigma
        if sigma_values:
            avg_sigma = np.mean(sigma_values)
        else:
            avg_sigma = 0

        # Current Status Alert
        if len(sigma_values) > 0:
            if abs(avg_sigma) >= 2.7:
                alert_color = "#dc2626" if avg_sigma < 0 else "#1d4ed8"
                alert_text = "🔴 위험 경보" if avg_sigma < 0 else "🔵 위험 경보"
                alert_bg = (
                    "rgba(239, 68, 68, 0.1)"
                    if avg_sigma < 0
                    else "rgba(29, 78, 216, 0.1)"
                )
            elif abs(avg_sigma) >= 2:
                alert_color = "#f59e0b" if avg_sigma < 0 else "#3b82f6"
                alert_text = "🟡 주의 경보" if avg_sigma < 0 else "🔵 주의 경보"
                alert_bg = (
                    "rgba(245, 158, 11, 0.1)"
                    if avg_sigma < 0
                    else "rgba(59, 130, 246, 0.1)"
                )
            else:
                alert_color = "#10b981"
                alert_text = "🟢 정상 상태"
                alert_bg = "rgba(16, 185, 129, 0.1)"

            # Determine badge text and style
            if abs(avg_sigma) >= 2.7:
                badge_text = "위험 +" if avg_sigma > 0 else "위험 -"
                badge_color = "#1d4ed8" if avg_sigma > 0 else "#dc2626"
            elif abs(avg_sigma) >= 2:
                badge_text = "주의 +" if avg_sigma > 0 else "주의 -"
                badge_color = "#3b82f6" if avg_sigma > 0 else "#f59e0b"
            elif avg_sigma >= 0:
                badge_text = "중립 +"
                badge_color = "#10b981"
            else:
                badge_text = "중립 -"
                badge_color = "#cbd5e0"

            alert_component = html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Span(alert_text, style={"fontSize": "1.2rem"}),
                                    html.Span(
                                        f"현재 시그마: {avg_sigma:.2f}σ",
                                        style={
                                            "color": alert_color,
                                            "fontWeight": "600",
                                            "fontSize": "1.1rem",
                                            "marginLeft": "10px",
                                        },
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "gap": "10px",
                                },
                            ),
                            html.Div(
                                badge_text,
                                style={
                                    "background": badge_color,
                                    "color": "white",
                                    "padding": "6px 12px",
                                    "borderRadius": "20px",
                                    "fontWeight": "600",
                                    "fontSize": "0.8rem",
                                    "textTransform": "uppercase",
                                    "letterSpacing": "0.5px",
                                    "boxShadow": "0 2px 4px rgba(0,0,0,0.2)",
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "space-between",
                        },
                    )
                ],
                style={
                    "background": alert_bg,
                    "padding": "12px 20px",
                    "borderRadius": "8px",
                    "borderLeft": f"4px solid {alert_color}",
                    "margin": "10px 0",
                    "boxShadow": "0 2px 8px rgba(0,0,0,0.1)",
                },
            )
        else:
            alert_component = html.Div()

        # Calculate positive percentage
        positive_change = (data.pct_change().iloc[-1] > 0).sum()
        positive_pct = positive_change / num_indices if num_indices > 0 else 0

        # Determine state for positive percentage
        if positive_pct >= 0.75:
            positive_state = "Strong"
            positive_color = "#10b981"  # Green
        elif positive_pct >= 0.5:
            positive_state = "Moderate"
            positive_color = "#3b82f6"  # Blue
        elif positive_pct >= 0.25:
            positive_state = "Weak"
            positive_color = "#f59e0b"  # Yellow
        else:
            positive_state = "Critical"
            positive_color = "#dc2626"  # Red

        # Calculate OECD CLI positive percentage
        positive_pct_oecd = NumOfOECDLeadingPositiveMoM()
        latest_oecd_pct = (
            positive_pct_oecd.iloc[-1] if len(positive_pct_oecd) > 0 else 0
        )

        # Determine OECD CLI state
        if latest_oecd_pct >= 75:
            oecd_state = "Strong"
            oecd_color = "#10b981"  # Green
        elif latest_oecd_pct >= 50:
            oecd_state = "Moderate"
            oecd_color = "#3b82f6"  # Blue
        elif latest_oecd_pct >= 25:
            oecd_state = "Weak"
            oecd_color = "#f59e0b"  # Yellow
        else:
            oecd_state = "Critical"
            oecd_color = "#dc2626"  # Red

        return html.Div(
            [
                alert_component,
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Span(
                                            "📅",
                                            style={
                                                "fontSize": "1.2rem",
                                                "marginRight": "6px",
                                            },
                                        ),
                                        html.Span(
                                            "Latest Update",
                                            style={
                                                "fontSize": "0.8rem",
                                                "fontWeight": "600",
                                                "color": "#ffffff",
                                            },
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "marginBottom": "0.5rem",
                                    },
                                ),
                                html.Div(
                                    latest_date.strftime("%Y-%m-%d"),
                                    style={
                                        "fontSize": "1.1rem",
                                        "fontWeight": "700",
                                        "color": "#ffffff",
                                    },
                                ),
                            ],
                            style={
                                "background": "linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)",
                                "padding": "0.5rem",
                                "borderRadius": "0.5rem",
                                "border": "1px solid rgba(71, 85, 105, 0.5)",
                                "boxShadow": "0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)",
                                "transition": "all 0.3s ease",
                                "position": "relative",
                                "overflow": "hidden",
                                "height": "90px",
                                "display": "flex",
                                "flexDirection": "column",
                                "justifyContent": "flex-start",
                                "margin": "2px",
                                "backdropFilter": "saturate(180%) blur(20px)",
                            },
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Span(
                                            "📈",
                                            style={
                                                "fontSize": "1.2rem",
                                                "marginRight": "6px",
                                            },
                                        ),
                                        html.Span(
                                            "Total Indices",
                                            style={
                                                "fontSize": "0.8rem",
                                                "fontWeight": "600",
                                                "color": "#ffffff",
                                            },
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "marginBottom": "0.5rem",
                                    },
                                ),
                                html.Div(
                                    str(num_indices),
                                    style={
                                        "fontSize": "1.1rem",
                                        "fontWeight": "700",
                                        "color": "#ffffff",
                                    },
                                ),
                            ],
                            style={
                                "background": "linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)",
                                "padding": "0.5rem",
                                "borderRadius": "0.5rem",
                                "border": "1px solid rgba(71, 85, 105, 0.5)",
                                "boxShadow": "0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)",
                                "transition": "all 0.3s ease",
                                "position": "relative",
                                "overflow": "hidden",
                                "height": "90px",
                                "display": "flex",
                                "flexDirection": "column",
                                "justifyContent": "flex-start",
                                "margin": "2px",
                                "backdropFilter": "saturate(180%) blur(20px)",
                            },
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Span(
                                            "📊",
                                            style={
                                                "fontSize": "1.2rem",
                                                "marginRight": "6px",
                                            },
                                        ),
                                        html.Span(
                                            "Positive Today",
                                            style={
                                                "fontSize": "0.8rem",
                                                "fontWeight": "600",
                                                "color": "#ffffff",
                                            },
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "marginBottom": "0.5rem",
                                    },
                                ),
                                html.Div(
                                    [
                                        html.Span(
                                            f"{positive_change}/{num_indices}",
                                            style={
                                                "fontSize": "1.1rem",
                                                "fontWeight": "700",
                                                "color": "#ffffff",
                                            },
                                        ),
                                        html.Span(
                                            positive_state,
                                            style={
                                                "background": positive_color,
                                                "color": "white",
                                                "padding": "3px 6px",
                                                "borderRadius": "6px",
                                                "fontWeight": "600",
                                                "fontSize": "0.6rem",
                                                "textTransform": "uppercase",
                                                "marginLeft": "8px",
                                            },
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "gap": "8px",
                                    },
                                ),
                            ],
                            style={
                                "background": "linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)",
                                "padding": "0.5rem",
                                "borderRadius": "0.5rem",
                                "border": "1px solid rgba(71, 85, 105, 0.5)",
                                "boxShadow": "0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)",
                                "transition": "all 0.3s ease",
                                "position": "relative",
                                "overflow": "hidden",
                                "height": "90px",
                                "display": "flex",
                                "flexDirection": "column",
                                "justifyContent": "flex-start",
                                "margin": "2px",
                                "backdropFilter": "saturate(180%) blur(20px)",
                            },
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Span(
                                            "🌍",
                                            style={
                                                "fontSize": "1.2rem",
                                                "marginRight": "6px",
                                            },
                                        ),
                                        html.Span(
                                            "OECD CLI",
                                            style={
                                                "fontSize": "0.8rem",
                                                "fontWeight": "600",
                                                "color": "#ffffff",
                                            },
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "marginBottom": "0.5rem",
                                    },
                                ),
                                html.Div(
                                    [
                                        html.Span(
                                            f"{latest_oecd_pct:.1f}%",
                                            style={
                                                "fontSize": "1.1rem",
                                                "fontWeight": "700",
                                                "color": "#ffffff",
                                            },
                                        ),
                                        html.Span(
                                            oecd_state,
                                            style={
                                                "background": oecd_color,
                                                "color": "white",
                                                "padding": "3px 6px",
                                                "borderRadius": "6px",
                                                "fontWeight": "600",
                                                "fontSize": "0.6rem",
                                                "textTransform": "uppercase",
                                                "marginLeft": "8px",
                                            },
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "gap": "8px",
                                    },
                                ),
                            ],
                            style={
                                "background": "linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)",
                                "padding": "0.5rem",
                                "borderRadius": "0.5rem",
                                "border": "1px solid rgba(71, 85, 105, 0.5)",
                                "boxShadow": "0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)",
                                "transition": "all 0.3s ease",
                                "position": "relative",
                                "overflow": "hidden",
                                "height": "90px",
                                "display": "flex",
                                "flexDirection": "column",
                                "justifyContent": "flex-start",
                                "margin": "2px",
                                "backdropFilter": "saturate(180%) blur(20px)",
                            },
                        ),
                    ],
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "repeat(4, 1fr)",
                        "gap": "8px",
                        "margin": "20px 0",
                    },
                ),
            ]
        )

    except Exception as e:
        return html.Div(
            f"Error creating metrics: {str(e)}",
            style={
                "color": "#dc2626",
                "background": "rgba(239, 68, 68, 0.1)",
                "padding": "12px",
                "borderRadius": "8px",
                "borderLeft": "4px solid #dc2626",
                "margin": "10px 0",
            },
        )


def create_gauge_charts():
    """Create gauge charts for all indicators"""
    try:
        data = get_index().loc["2022":].ffill()

        if data.empty:
            return html.Div(
                "No data available for gauges",
                style={
                    "color": "#dc2626",
                    "background": "rgba(239, 68, 68, 0.1)",
                    "padding": "12px",
                    "borderRadius": "8px",
                    "borderLeft": "4px solid #dc2626",
                    "margin": "10px 0",
                },
            )

        # Define the desired order for gauges
        gauge_order = [
            "코스피",
            "S&P 500",
            "한국CD91",
            "한국 3년",
            "한국 10년",
            "미국 10년",
            "미국 - 한국 10년",
            "한국회사채스프레드(AA-)",
            "달러 - 원 환율",
        ]

        # Define indicator types for proper gauge calculation
        indicator_types = {
            "코스피": "stock",
            "S&P 500": "stock",
            "한국CD91": "rate",
            "한국 3년": "rate",
            "한국 10년": "rate",
            "미국 10년": "rate",
            "미국 - 한국 10년": "rate",
            "한국회사채스프레드(AA-)": "rate",
            "달러 - 원 환율": "fx",
        }

        # Collect all gauge figures with metadata
        gauge_data = []
        for name in gauge_order:
            if name in data.columns:
                series = data[name].copy()
                series.name = name  # Set the series name for display
                indicator_type = indicator_types.get(name, "rate")
                fig, current_state, state_color = make_gauge(
                    series, indicator_type=indicator_type
                )
                gauge_data.append(
                    {
                        "name": name,
                        "figure": fig,
                        "latest_value": series.iloc[-1],
                        "change": series.pct_change().iloc[-1],
                        "current_state": current_state,
                        "state_color": state_color,
                    }
                )

        # Create gauge components
        gauge_components = []
        for i in range(0, len(gauge_data), 2):
            row_components = []

            # First gauge
            row_components.append(
                html.Div(
                    [
                        dcc.Graph(
                            figure=gauge_data[i]["figure"],
                            config={"displayModeBar": False},
                        )
                    ],
                    style={"width": "48%", "display": "inline-block"},
                )
            )

            # Second gauge if exists
            if i + 1 < len(gauge_data):
                row_components.append(
                    html.Div(
                        [
                            dcc.Graph(
                                figure=gauge_data[i + 1]["figure"],
                                config={"displayModeBar": False},
                            )
                        ],
                        style={
                            "width": "48%",
                            "display": "inline-block",
                            "marginLeft": "4%",
                        },
                    )
                )

            gauge_components.append(
                html.Div(row_components, style={"marginBottom": "20px"})
            )

        return html.Div(gauge_components)

    except Exception as e:
        return html.Div(
            f"Error creating gauges: {str(e)}",
            style={
                "color": "#dc2626",
                "background": "rgba(239, 68, 68, 0.1)",
                "padding": "12px",
                "borderRadius": "8px",
                "borderLeft": "4px solid #dc2626",
                "margin": "10px 0",
            },
        )


# Main layout
layout = html.Div(
    [
        # Header Section
        html.H2(
            "📈 위험자산 리스크관리 프로세스 대시보드",
            style={
                "fontFamily": "'Inter', sans-serif",
                "fontSize": "2.2rem",
                "fontWeight": "700",
                "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                "backgroundClip": "text",
                "WebkitBackgroundClip": "text",
                "WebkitTextFillColor": "transparent",
                "textAlign": "center",
                "marginBottom": "0.1rem",
                "letterSpacing": "-0.02em",
                "textShadow": "0 2px 4px rgba(0, 0, 0, 0.3)",
            },
        ),
        html.P(
            "흥국생명 자산운용본부 투자기획팀",
            style={
                "fontFamily": "'Inter', sans-serif",
                "fontSize": "0.9rem",
                "fontWeight": "400",
                "color": "#a0aec0",
                "textAlign": "center",
                "marginBottom": "0.5rem",
                "lineHeight": "1.3",
            },
        ),
        # Background section
        html.H3(
            "📋 배경 및 목적",
            style={
                "fontFamily": "'Inter', sans-serif",
                "fontSize": "1.3rem",
                "fontWeight": "600",
                "color": "#ffffff",
                "margin": "0.75rem 0 0.5rem 0",
                "paddingBottom": "0.3rem",
                "borderBottom": "2px solid #475569",
                "position": "relative",
                "textShadow": "0 2px 4px rgba(0, 0, 0, 0.3)",
            },
        ),
        html.P(
            [
                "- 크레딧 및 주식자산의 리스크 요인을 사전 식별하기 위한 핵심 시장지표 모니터링. ",
                html.Br(),
                "- 지표별 변동을 정량화하여 위험 수준을 단계별(Yellow/Red)로 구분하여 자산배분 및 한도 관리 체계의 조기경보 기능을 강화.",
            ],
            style={"color": "#cbd5e0", "fontSize": "0.95rem", "lineHeight": "1.6"},
        ),
        # Implications and Guidelines section
        html.H3(
            "💡 시사점 및 리스크 가이드라인",
            style={
                "fontFamily": "'Inter', sans-serif",
                "fontSize": "1.3rem",
                "fontWeight": "600",
                "color": "#ffffff",
                "margin": "0.75rem 0 0.5rem 0",
                "paddingBottom": "0.3rem",
                "borderBottom": "2px solid #475569",
                "position": "relative",
                "textShadow": "0 2px 4px rgba(0, 0, 0, 0.3)",
            },
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.H4(
                            "시사점:",
                            style={
                                "color": "#ffffff",
                                "fontSize": "1.1rem",
                                "marginBottom": "10px",
                            },
                        ),
                        html.P(
                            "• 리스크 조기감지: 통계적 유의성 기반 계량적 접근",
                            style={"color": "#cbd5e0", "marginBottom": "5px"},
                        ),
                        html.P(
                            "• 자산배분 최적화: 정량화된 지표 기반 리밸런싱",
                            style={"color": "#cbd5e0", "marginBottom": "5px"},
                        ),
                    ],
                    style={
                        "width": "50%",
                        "display": "inline-block",
                        "verticalAlign": "top",
                    },
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.P(
                                    "💳 크레딧 자산",
                                    style={
                                        "color": "#92400e",
                                        "fontWeight": "600",
                                        "marginBottom": "8px",
                                        "fontSize": "0.9rem",
                                    },
                                ),
                                html.P(
                                    "🟡 Yellow: 신규매수금지",
                                    style={
                                        "color": "#ffffff",
                                        "marginBottom": "4px",
                                        "fontSize": "0.8rem",
                                        "fontWeight": "600",
                                    },
                                ),
                                html.P(
                                    "🔴 Red: 현금화 고민",
                                    style={
                                        "color": "#ffffff",
                                        "marginBottom": "0",
                                        "fontSize": "0.8rem",
                                        "fontWeight": "600",
                                    },
                                ),
                            ],
                            style={
                                "background": "rgba(245, 158, 11, 0.15)",
                                "padding": "12px",
                                "borderRadius": "8px",
                                "borderLeft": "4px solid #f59e0b",
                                "margin": "5px 0",
                                "border": "1px solid rgba(245, 158, 11, 0.3)",
                            },
                        )
                    ],
                    style={
                        "width": "25%",
                        "display": "inline-block",
                        "verticalAlign": "top",
                    },
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.P(
                                    "📈 주식 자산",
                                    style={
                                        "color": "#991b1b",
                                        "fontWeight": "600",
                                        "marginBottom": "8px",
                                        "fontSize": "0.9rem",
                                    },
                                ),
                                html.P(
                                    "🟡 Yellow: 10%이상 현금화",
                                    style={
                                        "color": "#ffffff",
                                        "marginBottom": "4px",
                                        "fontSize": "0.8rem",
                                        "fontWeight": "600",
                                    },
                                ),
                                html.P(
                                    "🔴 Red: 40%이상 현금화",
                                    style={
                                        "color": "#ffffff",
                                        "marginBottom": "0",
                                        "fontSize": "0.8rem",
                                        "fontWeight": "600",
                                    },
                                ),
                            ],
                            style={
                                "background": "rgba(239, 68, 68, 0.15)",
                                "padding": "12px",
                                "borderRadius": "8px",
                                "borderLeft": "4px solid #ef4444",
                                "margin": "5px 0",
                                "border": "1px solid rgba(239, 68, 68, 0.3)",
                            },
                        )
                    ],
                    style={
                        "width": "25%",
                        "display": "inline-block",
                        "verticalAlign": "top",
                    },
                ),
            ]
        ),
        html.Hr(),
        # Key Metrics Section with Refresh Button
        html.Div(
            [
                html.H3(
                    "📊 종합 리스크 지표",
                    style={
                        "fontFamily": "'Inter', sans-serif",
                        "fontSize": "1.3rem",
                        "fontWeight": "600",
                        "color": "#ffffff",
                        "margin": "0.75rem 0 0.5rem 0",
                        "paddingBottom": "0.3rem",
                        "borderBottom": "2px solid #475569",
                        "position": "relative",
                        "textShadow": "0 2px 4px rgba(0, 0, 0, 0.3)",
                        "flex": "1",
                    },
                ),
                dmc.Button(
                    [
                        DashIconify(icon="mdi:refresh", width=18),
                        html.Span("새로고침", style={"marginLeft": "8px"}),
                    ],
                    id="refresh-risk-data",
                    variant="light",
                    color="blue",
                    size="sm",
                    style={
                        "marginTop": "0.5rem",
                        "backgroundColor": "rgba(59, 130, 246, 0.1)",
                        "border": "1px solid rgba(59, 130, 246, 0.3)",
                        "color": "#60a5fa",
                    },
                ),
            ],
            style={
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "flex-start",
                "gap": "16px",
            },
        ),
        dcc.Loading(
            id="loading-risk-metrics",
            type="default",
            children=html.Div(id="risk-metrics"),
            style={"minHeight": "200px"},
        ),
        html.Hr(),
        # OECD CLI Chart Section
        html.H3(
            "📈 OECD CLI Analysis",
            style={
                "fontFamily": "'Inter', sans-serif",
                "fontSize": "1.3rem",
                "fontWeight": "600",
                "color": "#ffffff",
                "margin": "0.75rem 0 0.5rem 0",
                "paddingBottom": "0.3rem",
                "borderBottom": "2px solid #475569",
                "position": "relative",
                "textShadow": "0 2px 4px rgba(0, 0, 0, 0.3)",
            },
        ),
        dcc.Loading(
            id="loading-oecd-chart",
            type="default",
            children=dcc.Graph(id="oecd-chart", config={"displayModeBar": False}),
            style={"minHeight": "450px"},
        ),
        # Gauge Charts Section
        html.H3(
            "🎯 개별 지표 상세 분석",
            style={
                "fontFamily": "'Inter', sans-serif",
                "fontSize": "1.3rem",
                "fontWeight": "600",
                "color": "#ffffff",
                "margin": "0.75rem 0 0.5rem 0",
                "paddingBottom": "0.3rem",
                "borderBottom": "2px solid #475569",
                "position": "relative",
                "textShadow": "0 2px 4px rgba(0, 0, 0, 0.3)",
            },
        ),
        # Indicator explanations
        html.Div(
            [
                html.H4(
                    "📊 지표별 의미",
                    style={
                        "color": "#ffffff",
                        "marginBottom": "12px",
                        "fontFamily": "'Inter', sans-serif",
                        "fontSize": "1.1rem",
                        "fontWeight": "600",
                    },
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.P(
                                    [
                                        html.B("📈 코스피:"),
                                        " 한국 주식시장 대표지수 (5주 하락율)",
                                    ],
                                    style={"marginBottom": "6px"},
                                ),
                                html.P(
                                    [
                                        html.B("🇺🇸 S&P 500:"),
                                        " 미국 주식시장 대표지수 (5주 하락율)",
                                    ],
                                    style={"marginBottom": "6px"},
                                ),
                                html.P(
                                    [
                                        html.B("🏦 한국CD91:"),
                                        " 한국 91일 만기 양도성예금증서 금리 (5주 상승폭)",
                                    ],
                                    style={"marginBottom": "6px"},
                                ),
                                html.P(
                                    [
                                        html.B("📊 한국 10년:"),
                                        " 한국 10년 국채 금리 (5주 상승폭)",
                                    ],
                                    style={"marginBottom": "6px"},
                                ),
                            ],
                            style={
                                "width": "50%",
                                "display": "inline-block",
                                "verticalAlign": "top",
                            },
                        ),
                        html.Div(
                            [
                                html.P(
                                    [
                                        html.B("🇺🇸 미국 10년:"),
                                        " 미국 10년 국채 금리 (5주 상승폭)",
                                    ],
                                    style={"marginBottom": "6px"},
                                ),
                                html.P(
                                    [
                                        html.B("💱 미국-한국 10년:"),
                                        " 미국-한국 10년 국채 금리차 (5주 상승폭)",
                                    ],
                                    style={"marginBottom": "6px"},
                                ),
                                html.P(
                                    [
                                        html.B("🏢 한국회사채 스프레드:"),
                                        " AA- 등급 회사채와 국채 금리차 (5주 상승폭)",
                                    ],
                                    style={"marginBottom": "6px"},
                                ),
                                html.P(
                                    [
                                        html.B("💵 달러-원 환율:"),
                                        " USD/KRW 환율 (5주 상승율)",
                                    ],
                                    style={"marginBottom": "0px"},
                                ),
                            ],
                            style={
                                "width": "50%",
                                "display": "inline-block",
                                "verticalAlign": "top",
                            },
                        ),
                    ],
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "1fr 1fr",
                        "gap": "16px",
                        "fontSize": "0.9rem",
                    },
                ),
            ],
            style={
                "background": "rgba(30, 41, 59, 0.7)",
                "padding": "16px",
                "borderRadius": "12px",
                "border": "1px solid rgba(71, 85, 105, 0.5)",
                "marginBottom": "1rem",
                "backdropFilter": "saturate(180%) blur(20px)",
                "boxShadow": "0 4px 20px rgba(0,0,0,0.15)",
            },
        ),
        # Gauge explanation
        html.Div(
            [
                html.H4(
                    "📊 게이지 작동 방식",
                    style={
                        "color": "#ffffff",
                        "marginBottom": "12px",
                        "fontFamily": "'Inter', sans-serif",
                        "fontSize": "1.1rem",
                        "fontWeight": "600",
                    },
                ),
                html.Div(
                    [
                        html.P(
                            [
                                html.B("• 통계적 유의성:"),
                                " 현재 값을 3년간 롤링 통계(104주 윈도우)와 비교",
                            ],
                            style={"marginBottom": "8px"},
                        ),
                        html.P(
                            [
                                html.B("• 색상 구분:"),
                                " 빨간색/노란색은 음의 편차, 초록색/파란색은 양의 편차를 나타냄",
                            ],
                            style={"marginBottom": "8px"},
                        ),
                        html.P(
                            [
                                html.B("• 상태 배지:"),
                                " 우상단 모서리에 현재 통계적 상태(위험, 주의, 중립)를 표시",
                            ],
                            style={"marginBottom": "0px"},
                        ),
                    ],
                    style={
                        "color": "#cbd5e0",
                        "fontSize": "0.9rem",
                        "lineHeight": "1.5",
                    },
                ),
            ],
            style={
                "background": "rgba(30, 41, 59, 0.7)",
                "padding": "16px",
                "borderRadius": "12px",
                "border": "1px solid rgba(71, 85, 105, 0.5)",
                "marginBottom": "1rem",
                "backdropFilter": "saturate(180%) blur(20px)",
                "boxShadow": "0 4px 20px rgba(0,0,0,0.15)",
            },
        ),
        # State Legend
        html.Div(
            [
                html.Span(
                    "위험 -",
                    style={
                        "padding": "6px 12px",
                        "borderRadius": "12px",
                        "fontSize": "0.75rem",
                        "fontWeight": "600",
                        "letterSpacing": "0.5px",
                        "color": "white",
                        "background": "#dc2626",
                        "margin": "2px",
                    },
                ),
                html.Span(
                    "주의 -",
                    style={
                        "padding": "6px 12px",
                        "borderRadius": "12px",
                        "fontSize": "0.75rem",
                        "fontWeight": "600",
                        "letterSpacing": "0.5px",
                        "color": "white",
                        "background": "#f59e0b",
                        "margin": "2px",
                    },
                ),
                html.Span(
                    "중립 -",
                    style={
                        "padding": "6px 12px",
                        "borderRadius": "12px",
                        "fontSize": "0.75rem",
                        "fontWeight": "600",
                        "letterSpacing": "0.5px",
                        "color": "white",
                        "background": "#6b7280",
                        "margin": "2px",
                    },
                ),
                html.Span(
                    "중립 +",
                    style={
                        "padding": "6px 12px",
                        "borderRadius": "12px",
                        "fontSize": "0.75rem",
                        "fontWeight": "600",
                        "letterSpacing": "0.5px",
                        "color": "white",
                        "background": "#10b981",
                        "margin": "2px",
                    },
                ),
                html.Span(
                    "주의 +",
                    style={
                        "padding": "6px 12px",
                        "borderRadius": "12px",
                        "fontSize": "0.75rem",
                        "fontWeight": "600",
                        "letterSpacing": "0.5px",
                        "color": "white",
                        "background": "#3b82f6",
                        "margin": "2px",
                    },
                ),
                html.Span(
                    "위험 +",
                    style={
                        "padding": "6px 12px",
                        "borderRadius": "12px",
                        "fontSize": "0.75rem",
                        "fontWeight": "600",
                        "letterSpacing": "0.5px",
                        "color": "white",
                        "background": "#1d4ed8",
                        "margin": "2px",
                    },
                ),
            ],
            style={
                "display": "flex",
                "justifyContent": "center",
                "flexWrap": "wrap",
                "gap": "6px",
                "marginBottom": "1rem",
                "padding": "8px",
                "background": "rgba(30, 41, 59, 0.7)",
                "borderRadius": "12px",
                "border": "1px solid rgba(71, 85, 105, 0.5)",
                "backdropFilter": "saturate(180%) blur(20px)",
                "boxShadow": "0 4px 20px rgba(0,0,0,0.15)",
            },
        ),
        # Gauge Charts
        dcc.Loading(
            id="loading-gauge-charts",
            type="default",
            children=html.Div(id="gauge-charts"),
            style={"minHeight": "400px"},
        ),
        # Footer
        html.Hr(),
        html.Div(
            [
                html.P(
                    "📊 Financial Index Dashboard • Real-time analysis with statistical significance indicators",
                    style={
                        "marginBottom": "0.25rem",
                        "textAlign": "center",
                        "color": "#94a3b8",
                        "fontSize": "0.875rem",
                        "fontWeight": "500",
                    },
                ),
                html.P(
                    "Data source: RawData.xlsx • Updated automatically • Built by 흥국생명 자산운용본부 투자기획팀",
                    style={
                        "marginBottom": "0",
                        "textAlign": "center",
                        "color": "#94a3b8",
                        "fontSize": "0.875rem",
                        "fontWeight": "500",
                    },
                ),
            ],
            style={
                "marginTop": "1rem",
                "paddingTop": "1rem",
                "borderTop": "1px solid #475569",
                "background": "rgba(30, 41, 59, 0.3)",
                "borderRadius": "8px",
                "padding": "16px",
            },
        ),
        # Data stores for caching
        dcc.Store(id="risk-data-store"),
        dcc.Store(id="oecd-data-store"),
        # Auto-refresh interval (5 minutes)
        dcc.Interval(
            id="risk-interval-component",
            interval=5 * 60 * 1000,  # 5 minutes in milliseconds
            n_intervals=0,
        ),
    ],
    style={
        "marginTop": "80px",
        "padding": "20px",
        "background": "linear-gradient(135deg, #0c1623 0%, #1a2332 50%, #2d3748 100%)",
        "minHeight": "100vh",
        "color": "#ffffff",
    },
)


# Callbacks to populate dynamic content with caching and refresh
@callback(
    Output("risk-data-store", "data"),
    Output("oecd-data-store", "data"),
    Input("refresh-risk-data", "n_clicks"),
    Input("risk-interval-component", "n_intervals"),
    State("risk-data-store", "data"),
    State("oecd-data-store", "data"),
    prevent_initial_call=False,
)
def update_data_stores(refresh_clicks, n_intervals, cached_risk_data, cached_oecd_data):
    """Update data stores when refresh button is clicked or interval triggers"""
    ctx = dash.callback_context
    if not ctx.triggered:
        # Initial load
        try:
            risk_data = get_index().loc["2022":].ffill()
            oecd_data = NumOfOECDLeadingPositiveMoM()
            # Serialize with index preserved
            risk_serialized = (
                risk_data.reset_index().to_dict("records")
                if not risk_data.empty
                else None
            )
            oecd_serialized = (
                oecd_data.reset_index().to_dict("records")
                if not oecd_data.empty
                else None
            )
            return risk_serialized, oecd_serialized
        except Exception as e:
            print(f"Error loading initial data: {e}")
            return None, None

    # Always refresh on button click, or every interval
    try:
        risk_data = get_index().loc["2022":].ffill()
        oecd_data = NumOfOECDLeadingPositiveMoM()
        # Serialize with index preserved
        risk_serialized = (
            risk_data.reset_index().to_dict("records") if not risk_data.empty else None
        )
        oecd_serialized = (
            oecd_data.reset_index().to_dict("records") if not oecd_data.empty else None
        )
        return risk_serialized, oecd_serialized
    except Exception as e:
        print(f"Error refreshing data: {e}")
        return cached_risk_data, cached_oecd_data


@callback(
    Output("risk-metrics", "children"),
    Input("risk-data-store", "data"),
    prevent_initial_call=False,
)
def update_risk_metrics(risk_data_dict):
    """Update risk metrics from cached data"""
    if risk_data_dict is None:
        return html.Div(
            [
                DashIconify(
                    icon="mdi:alert-circle", width=24, style={"marginRight": "8px"}
                ),
                "데이터를 불러올 수 없습니다. 새로고침 버튼을 클릭하세요.",
            ],
            style={
                "color": "#f59e0b",
                "background": "rgba(245, 158, 11, 0.1)",
                "padding": "16px",
                "borderRadius": "8px",
                "borderLeft": "4px solid #f59e0b",
                "margin": "10px 0",
                "display": "flex",
                "alignItems": "center",
            },
        )

    try:
        # Reconstruct DataFrame from dict (index was reset during serialization)
        risk_data = pd.DataFrame(risk_data_dict)
        if "index" in risk_data.columns:
            risk_data.index = pd.to_datetime(risk_data["index"])
            risk_data = risk_data.drop(columns=["index"])

        # Use the existing create_risk_metrics function but with data parameter
        return create_risk_metrics_from_data(risk_data)
    except Exception as e:
        return html.Div(
            [
                DashIconify(
                    icon="mdi:alert-circle", width=24, style={"marginRight": "8px"}
                ),
                f"오류 발생: {str(e)}",
            ],
            style={
                "color": "#dc2626",
                "background": "rgba(239, 68, 68, 0.1)",
                "padding": "16px",
                "borderRadius": "8px",
                "borderLeft": "4px solid #dc2626",
                "margin": "10px 0",
                "display": "flex",
                "alignItems": "center",
            },
        )


@callback(
    Output("oecd-chart", "figure"),
    Input("oecd-data-store", "data"),
    prevent_initial_call=False,
)
def update_oecd_chart(oecd_data_dict):
    """Update OECD chart from cached data"""
    if oecd_data_dict is None:
        # Return empty figure with error message
        fig = go.Figure()
        fig.add_annotation(
            text="데이터를 불러올 수 없습니다",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#f59e0b"),
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=450,
        )
        return fig

    try:
        return create_oecd_chart()
    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(
            text=f"오류 발생: {str(e)}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14, color="#dc2626"),
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=450,
        )
        return fig


@callback(
    Output("gauge-charts", "children"),
    Input("risk-data-store", "data"),
    prevent_initial_call=False,
)
def update_gauge_charts(risk_data_dict):
    """Update gauge charts from cached data"""
    if risk_data_dict is None:
        return html.Div(
            [
                DashIconify(
                    icon="mdi:alert-circle", width=24, style={"marginRight": "8px"}
                ),
                "데이터를 불러올 수 없습니다. 새로고침 버튼을 클릭하세요.",
            ],
            style={
                "color": "#f59e0b",
                "background": "rgba(245, 158, 11, 0.1)",
                "padding": "16px",
                "borderRadius": "8px",
                "borderLeft": "4px solid #f59e0b",
                "margin": "10px 0",
                "display": "flex",
                "alignItems": "center",
            },
        )

    try:
        # Reconstruct DataFrame from dict (index was reset during serialization)
        data = pd.DataFrame(risk_data_dict)
        if "index" in data.columns:
            data.index = pd.to_datetime(data["index"])
            data = data.drop(columns=["index"])

        return create_gauge_charts_from_data(data)
    except Exception as e:
        return html.Div(
            [
                DashIconify(
                    icon="mdi:alert-circle", width=24, style={"marginRight": "8px"}
                ),
                f"오류 발생: {str(e)}",
            ],
            style={
                "color": "#dc2626",
                "background": "rgba(239, 68, 68, 0.1)",
                "padding": "16px",
                "borderRadius": "8px",
                "borderLeft": "4px solid #dc2626",
                "margin": "10px 0",
                "display": "flex",
                "alignItems": "center",
            },
        )


def create_risk_metrics_from_data(data):
    """Create risk metrics cards from provided data"""
    try:
        if data.empty:
            return html.Div(
                [
                    DashIconify(
                        icon="mdi:database-off", width=24, style={"marginRight": "8px"}
                    ),
                    "데이터가 없습니다",
                ],
                style={
                    "color": "#dc2626",
                    "background": "rgba(239, 68, 68, 0.1)",
                    "padding": "16px",
                    "borderRadius": "8px",
                    "borderLeft": "4px solid #dc2626",
                    "margin": "10px 0",
                    "display": "flex",
                    "alignItems": "center",
                },
            )

        latest_date = data.index[-1]
        today_date = date.today()
        if isinstance(latest_date, pd.Timestamp):
            latest_date = latest_date.date()
        if latest_date > today_date:
            latest_date = today_date
        num_indices = len(data.columns)

        # Calculate sigma values for all indices
        sigma_values = []
        for name, series in data.items():
            if name in ["코스피", "S&P 500", "달러 - 원 환율"]:
                d = series.resample("W").last().pct_change(5).dropna().loc["2000":]
                if name == "달러 - 원 환율":
                    d = d * (-1)
            else:
                d = series.resample("W").last().diff(5).dropna().loc["2000":] * (-1)
            window = 52 * 2  # 104 weeks

            if len(d) < window:
                continue

            rolling_mean = d.rolling(window).mean()
            rolling_std = d.rolling(window).std()
            mean = rolling_mean.iloc[-1]
            std = rolling_std.iloc[-1]
            current = d.iloc[-1]

            if pd.notna(mean) and pd.notna(std) and pd.notna(current) and std != 0:
                z = (current - mean) / std
                if pd.notna(z):
                    sigma_values.append(z)

        # Calculate average sigma
        if sigma_values:
            avg_sigma = np.mean(sigma_values)
        else:
            avg_sigma = 0

        # Current Status Alert
        if len(sigma_values) > 0:
            if abs(avg_sigma) >= 2.7:
                alert_color = "#dc2626" if avg_sigma < 0 else "#1d4ed8"
                alert_text = "🔴 위험 경보" if avg_sigma < 0 else "🔵 위험 경보"
                alert_bg = (
                    "rgba(239, 68, 68, 0.1)"
                    if avg_sigma < 0
                    else "rgba(29, 78, 216, 0.1)"
                )
            elif abs(avg_sigma) >= 2:
                alert_color = "#f59e0b" if avg_sigma < 0 else "#3b82f6"
                alert_text = "🟡 주의 경보" if avg_sigma < 0 else "🔵 주의 경보"
                alert_bg = (
                    "rgba(245, 158, 11, 0.1)"
                    if avg_sigma < 0
                    else "rgba(59, 130, 246, 0.1)"
                )
            else:
                alert_color = "#10b981"
                alert_text = "🟢 정상 상태"
                alert_bg = "rgba(16, 185, 129, 0.1)"

            # Determine badge text and style
            if abs(avg_sigma) >= 2.7:
                badge_text = "위험 +" if avg_sigma > 0 else "위험 -"
                badge_color = "#1d4ed8" if avg_sigma > 0 else "#dc2626"
            elif abs(avg_sigma) >= 2:
                badge_text = "주의 +" if avg_sigma > 0 else "주의 -"
                badge_color = "#3b82f6" if avg_sigma > 0 else "#f59e0b"
            elif avg_sigma >= 0:
                badge_text = "중립 +"
                badge_color = "#10b981"
            else:
                badge_text = "중립 -"
                badge_color = "#cbd5e0"

            alert_component = html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Span(alert_text, style={"fontSize": "1.2rem"}),
                                    html.Span(
                                        f"현재 시그마: {avg_sigma:.2f}σ",
                                        style={
                                            "color": alert_color,
                                            "fontWeight": "600",
                                            "fontSize": "1.1rem",
                                            "marginLeft": "10px",
                                        },
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "gap": "10px",
                                },
                            ),
                            html.Div(
                                badge_text,
                                style={
                                    "background": badge_color,
                                    "color": "white",
                                    "padding": "6px 12px",
                                    "borderRadius": "20px",
                                    "fontWeight": "600",
                                    "fontSize": "0.8rem",
                                    "textTransform": "uppercase",
                                    "letterSpacing": "0.5px",
                                    "boxShadow": "0 2px 4px rgba(0,0,0,0.2)",
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "space-between",
                        },
                    )
                ],
                style={
                    "background": alert_bg,
                    "padding": "12px 20px",
                    "borderRadius": "8px",
                    "borderLeft": f"4px solid {alert_color}",
                    "margin": "10px 0",
                    "boxShadow": "0 2px 8px rgba(0,0,0,0.1)",
                },
            )
        else:
            alert_component = html.Div()

        # Calculate positive percentage
        positive_change = (data.pct_change().iloc[-1] > 0).sum()
        positive_pct = positive_change / num_indices if num_indices > 0 else 0

        # Determine state for positive percentage
        if positive_pct >= 0.75:
            positive_state = "Strong"
            positive_color = "#10b981"  # Green
        elif positive_pct >= 0.5:
            positive_state = "Moderate"
            positive_color = "#3b82f6"  # Blue
        elif positive_pct >= 0.25:
            positive_state = "Weak"
            positive_color = "#f59e0b"  # Yellow
        else:
            positive_state = "Critical"
            positive_color = "#dc2626"  # Red

        # Calculate OECD CLI positive percentage
        try:
            positive_pct_oecd = NumOfOECDLeadingPositiveMoM()
            latest_oecd_pct = (
                positive_pct_oecd.iloc[-1] if len(positive_pct_oecd) > 0 else 0
            )
        except Exception as e:
            print(f"Error calculating OECD CLI: {e}")
            latest_oecd_pct = 0

        # Determine OECD CLI state
        if latest_oecd_pct >= 75:
            oecd_state = "Strong"
            oecd_color = "#10b981"  # Green
        elif latest_oecd_pct >= 50:
            oecd_state = "Moderate"
            oecd_color = "#3b82f6"  # Blue
        elif latest_oecd_pct >= 25:
            oecd_state = "Weak"
            oecd_color = "#f59e0b"  # Yellow
        else:
            oecd_state = "Critical"
            oecd_color = "#dc2626"  # Red

        # Format latest_date for display
        if isinstance(latest_date, date):
            latest_date_str = latest_date.strftime("%Y-%m-%d")
        else:
            latest_date_str = str(latest_date)

        return html.Div(
            [
                alert_component,
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Span(
                                            "📅",
                                            style={
                                                "fontSize": "1.2rem",
                                                "marginRight": "6px",
                                            },
                                        ),
                                        html.Span(
                                            "Latest Update",
                                            style={
                                                "fontSize": "0.8rem",
                                                "fontWeight": "600",
                                                "color": "#ffffff",
                                            },
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "marginBottom": "0.5rem",
                                    },
                                ),
                                html.Div(
                                    latest_date_str,
                                    style={
                                        "fontSize": "1.1rem",
                                        "fontWeight": "700",
                                        "color": "#ffffff",
                                    },
                                ),
                            ],
                            style={
                                "background": "linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)",
                                "padding": "0.5rem",
                                "borderRadius": "0.5rem",
                                "border": "1px solid rgba(71, 85, 105, 0.5)",
                                "boxShadow": "0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)",
                                "transition": "all 0.3s ease",
                                "position": "relative",
                                "overflow": "hidden",
                                "height": "90px",
                                "display": "flex",
                                "flexDirection": "column",
                                "justifyContent": "flex-start",
                                "margin": "2px",
                                "backdropFilter": "saturate(180%) blur(20px)",
                            },
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Span(
                                            "📈",
                                            style={
                                                "fontSize": "1.2rem",
                                                "marginRight": "6px",
                                            },
                                        ),
                                        html.Span(
                                            "Total Indices",
                                            style={
                                                "fontSize": "0.8rem",
                                                "fontWeight": "600",
                                                "color": "#ffffff",
                                            },
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "marginBottom": "0.5rem",
                                    },
                                ),
                                html.Div(
                                    str(num_indices),
                                    style={
                                        "fontSize": "1.1rem",
                                        "fontWeight": "700",
                                        "color": "#ffffff",
                                    },
                                ),
                            ],
                            style={
                                "background": "linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)",
                                "padding": "0.5rem",
                                "borderRadius": "0.5rem",
                                "border": "1px solid rgba(71, 85, 105, 0.5)",
                                "boxShadow": "0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)",
                                "transition": "all 0.3s ease",
                                "position": "relative",
                                "overflow": "hidden",
                                "height": "90px",
                                "display": "flex",
                                "flexDirection": "column",
                                "justifyContent": "flex-start",
                                "margin": "2px",
                                "backdropFilter": "saturate(180%) blur(20px)",
                            },
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Span(
                                            "📊",
                                            style={
                                                "fontSize": "1.2rem",
                                                "marginRight": "6px",
                                            },
                                        ),
                                        html.Span(
                                            "Positive Today",
                                            style={
                                                "fontSize": "0.8rem",
                                                "fontWeight": "600",
                                                "color": "#ffffff",
                                            },
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "marginBottom": "0.5rem",
                                    },
                                ),
                                html.Div(
                                    [
                                        html.Span(
                                            f"{positive_change}/{num_indices}",
                                            style={
                                                "fontSize": "1.1rem",
                                                "fontWeight": "700",
                                                "color": "#ffffff",
                                            },
                                        ),
                                        html.Span(
                                            positive_state,
                                            style={
                                                "background": positive_color,
                                                "color": "white",
                                                "padding": "3px 6px",
                                                "borderRadius": "6px",
                                                "fontWeight": "600",
                                                "fontSize": "0.6rem",
                                                "textTransform": "uppercase",
                                                "marginLeft": "8px",
                                            },
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "gap": "8px",
                                    },
                                ),
                            ],
                            style={
                                "background": "linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)",
                                "padding": "0.5rem",
                                "borderRadius": "0.5rem",
                                "border": "1px solid rgba(71, 85, 105, 0.5)",
                                "boxShadow": "0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)",
                                "transition": "all 0.3s ease",
                                "position": "relative",
                                "overflow": "hidden",
                                "height": "90px",
                                "display": "flex",
                                "flexDirection": "column",
                                "justifyContent": "flex-start",
                                "margin": "2px",
                                "backdropFilter": "saturate(180%) blur(20px)",
                            },
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Span(
                                            "🌍",
                                            style={
                                                "fontSize": "1.2rem",
                                                "marginRight": "6px",
                                            },
                                        ),
                                        html.Span(
                                            "OECD CLI",
                                            style={
                                                "fontSize": "0.8rem",
                                                "fontWeight": "600",
                                                "color": "#ffffff",
                                            },
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "marginBottom": "0.5rem",
                                    },
                                ),
                                html.Div(
                                    [
                                        html.Span(
                                            f"{latest_oecd_pct:.1f}%",
                                            style={
                                                "fontSize": "1.1rem",
                                                "fontWeight": "700",
                                                "color": "#ffffff",
                                            },
                                        ),
                                        html.Span(
                                            oecd_state,
                                            style={
                                                "background": oecd_color,
                                                "color": "white",
                                                "padding": "3px 6px",
                                                "borderRadius": "6px",
                                                "fontWeight": "600",
                                                "fontSize": "0.6rem",
                                                "textTransform": "uppercase",
                                                "marginLeft": "8px",
                                            },
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "gap": "8px",
                                    },
                                ),
                            ],
                            style={
                                "background": "linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)",
                                "padding": "0.5rem",
                                "borderRadius": "0.5rem",
                                "border": "1px solid rgba(71, 85, 105, 0.5)",
                                "boxShadow": "0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)",
                                "transition": "all 0.3s ease",
                                "position": "relative",
                                "overflow": "hidden",
                                "height": "90px",
                                "display": "flex",
                                "flexDirection": "column",
                                "justifyContent": "flex-start",
                                "margin": "2px",
                                "backdropFilter": "saturate(180%) blur(20px)",
                            },
                        ),
                    ],
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "repeat(auto-fit, minmax(200px, 1fr))",
                        "gap": "8px",
                        "margin": "20px 0",
                    },
                ),
            ]
        )

    except Exception as e:
        return html.Div(
            [
                DashIconify(
                    icon="mdi:alert-circle", width=24, style={"marginRight": "8px"}
                ),
                f"오류 발생: {str(e)}",
            ],
            style={
                "color": "#dc2626",
                "background": "rgba(239, 68, 68, 0.1)",
                "padding": "16px",
                "borderRadius": "8px",
                "borderLeft": "4px solid #dc2626",
                "margin": "10px 0",
                "display": "flex",
                "alignItems": "center",
            },
        )


def create_gauge_charts_from_data(data):
    """Create gauge charts from provided data"""
    try:
        if data.empty:
            return html.Div(
                [
                    DashIconify(
                        icon="mdi:database-off", width=24, style={"marginRight": "8px"}
                    ),
                    "게이지 데이터가 없습니다",
                ],
                style={
                    "color": "#dc2626",
                    "background": "rgba(239, 68, 68, 0.1)",
                    "padding": "16px",
                    "borderRadius": "8px",
                    "borderLeft": "4px solid #dc2626",
                    "margin": "10px 0",
                    "display": "flex",
                    "alignItems": "center",
                },
            )

        # Define the desired order for gauges
        gauge_order = [
            "코스피",
            "S&P 500",
            "한국CD91",
            "한국 3년",
            "한국 10년",
            "미국 10년",
            "미국 - 한국 10년",
            "한국회사채스프레드(AA-)",
            "달러 - 원 환율",
        ]

        # Define indicator types for proper gauge calculation
        indicator_types = {
            "코스피": "stock",
            "S&P 500": "stock",
            "한국CD91": "rate",
            "한국 3년": "rate",
            "한국 10년": "rate",
            "미국 10년": "rate",
            "미국 - 한국 10년": "rate",
            "한국회사채스프레드(AA-)": "rate",
            "달러 - 원 환율": "fx",
        }

        # Collect all gauge figures with metadata
        gauge_data = []
        for name in gauge_order:
            if name in data.columns:
                series = data[name].copy()
                series.name = name  # Set the series name for display
                indicator_type = indicator_types.get(name, "rate")
                fig, current_state, state_color = make_gauge(
                    series, indicator_type=indicator_type
                )
                gauge_data.append(
                    {
                        "name": name,
                        "figure": fig,
                        "latest_value": series.iloc[-1],
                        "change": series.pct_change().iloc[-1],
                        "current_state": current_state,
                        "state_color": state_color,
                    }
                )

        # Create gauge components with responsive grid
        gauge_components = []
        for i in range(0, len(gauge_data), 2):
            row_components = []

            # First gauge
            row_components.append(
                html.Div(
                    [
                        dcc.Graph(
                            figure=gauge_data[i]["figure"],
                            config={"displayModeBar": False},
                        )
                    ],
                    style={
                        "width": "100%",
                        "maxWidth": "600px",
                        "margin": "0 auto 20px auto",
                    },
                )
            )

            # Second gauge if exists
            if i + 1 < len(gauge_data):
                row_components.append(
                    html.Div(
                        [
                            dcc.Graph(
                                figure=gauge_data[i + 1]["figure"],
                                config={"displayModeBar": False},
                            )
                        ],
                        style={
                            "width": "100%",
                            "maxWidth": "600px",
                            "margin": "0 auto 20px auto",
                        },
                    )
                )

            gauge_components.append(
                html.Div(
                    row_components,
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "repeat(auto-fit, minmax(300px, 1fr))",
                        "gap": "20px",
                        "marginBottom": "20px",
                    },
                )
            )

        return html.Div(gauge_components)

    except Exception as e:
        return html.Div(
            [
                DashIconify(
                    icon="mdi:alert-circle", width=24, style={"marginRight": "8px"}
                ),
                f"오류 발생: {str(e)}",
            ],
            style={
                "color": "#dc2626",
                "background": "rgba(239, 68, 68, 0.1)",
                "padding": "16px",
                "borderRadius": "8px",
                "borderLeft": "4px solid #dc2626",
                "margin": "10px 0",
                "display": "flex",
                "alignItems": "center",
            },
        )
