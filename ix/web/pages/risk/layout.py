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

from ix.web.pages.risk.gauge import make_gauge

# Register Page (will be called when app is instantiated)
try:
    dash.register_page(
        __name__, path="/risk", title="Risk Management", name="Risk Management"
    )
except dash.exceptions.PageError:
    # Page registration will be handled by the main app
    pass


def get_oecd_cli():
    """Load OECD CLI data from RawData.xlsx"""
    try:
        data = pd.read_excel(
            os.path.join(os.path.dirname(__file__), "RawData.xlsx"),
            sheet_name="OECD CLI",
            index_col=[0],
            parse_dates=True,
        )
        return data
    except Exception as e:
        print(f"Error loading OECD CLI data: {e}")
        return pd.DataFrame()


def calculate_positive_percentage(df):
    """Calculate percentage of non-NaN values that are positive for each date"""
    positive_percentages = []
    dates = []

    for date in df.index:
        # Get values for this date, excluding NaN
        values = df.loc[date].dropna()

        if len(values) > 0:  # Only if we have valid data
            positive_count = (values > 0).sum()
            total_count = len(values)
            positive_pct = (positive_count / total_count) * 100
            positive_percentages.append(positive_pct)
            dates.append(date)

    return pd.Series(positive_percentages, index=dates)


def create_oecd_chart():
    """Create OECD CLI chart"""
    # Get OECD data and calculate positive percentage
    oecd = get_oecd_cli().diff()
    positive_pct = calculate_positive_percentage(oecd)

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


def get_index():
    """Load and process index data"""
    try:
        data = (
            pd.read_excel(
                os.path.join(os.path.dirname(__file__), "RawData.xlsx"),
                sheet_name="Index",
                index_col=[0],
                parse_dates=True,
            )
            .ffill()
            .resample("W")
            .last()
        )

        data["KCBAASS:YTM"] = data["KCBAAS:YTM"] - data["KTB3Y:YTM"]
        data["USKR10YS:YTM"] = data["UST10Y:YTM"] - data["KTB10Y:YTM"]

        for col in data.columns:
            if col.split(":", maxsplit=1)[1] == "PXR":
                data[col] = data[col].pct_change(5).dropna().mul(-100)
            elif col.split(":", maxsplit=1)[1] == "PX":
                data[col] = data[col].pct_change(5).dropna().mul(100)
            elif col.split(":", maxsplit=1)[1] == "YTM":
                data[col] = data[col].diff(5).dropna().mul(-100)

        data = data.rename(
            columns={
                "KTB10Y:YTM": "한국 10년",
                "KTB3Y:YTM": "한국 3년",
                "UST10Y:YTM": "미국 10년",
                "KCBAAS:YTM": "한국회사채(AA-)",
                "KCBAASS:YTM": "한국회사채스프레드(AA-)",
                "USKR10YS:YTM": "미국 - 한국 10년",
                "USDKRW:PXR": "달러 - 원 환율",
                "S&P500:PX": "S&P 500",
                "KOSPI:PX": "코스피",
                "KRCD91:YTM": "한국CD91",
            }
        )

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
            d = series.resample("W").last().pct_change(5).dropna().loc["2000":]
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
        oecd_data = get_oecd_cli().diff()
        positive_pct_oecd = calculate_positive_percentage(oecd_data)
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

        # Collect all gauge figures with metadata
        gauge_data = []
        for name in gauge_order:
            if name in data.columns:
                series = data[name]
                fig, current_state, state_color = make_gauge(series)
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
        # Key Metrics Section
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
            },
        ),
        html.Div(id="risk-metrics"),
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
        dcc.Graph(figure=create_oecd_chart(), config={"displayModeBar": False}),
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
        html.Div(id="gauge-charts"),
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
    ],
    style={
        "marginTop": "80px",
        "padding": "20px",
        "background": "linear-gradient(135deg, #0c1623 0%, #1a2332 50%, #2d3748 100%)",
        "minHeight": "100vh",
        "color": "#ffffff",
    },
)


# Callbacks to populate dynamic content
@callback(Output("risk-metrics", "children"), Input("risk-metrics", "id"))
def update_risk_metrics(_):
    return create_risk_metrics()


@callback(Output("gauge-charts", "children"), Input("gauge-charts", "id"))
def update_gauge_charts(_):
    return create_gauge_charts()
