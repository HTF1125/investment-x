"""
Analytics logic for Risk Management Dashboard.
Refactored to be shared between Dash UI and FastAPI.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, datetime
from typing import Dict, Any, List, Tuple
from ix.db import Series
from ix.db.query import NumOfOECDLeadingPositiveMoM
from ix.web.pages.risk.gauge import make_gauge

def get_index_data():
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

    # Add horizontal reference lines
    fig.add_hline(y=50, line_dash="dash", line_color="#cbd5e0", line_width=2)
    fig.add_hline(y=75, line_dash="dot", line_color="#10b981", line_width=2)
    fig.add_hline(y=25, line_dash="dot", line_color="#dc2626", line_width=2)

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

    # Update layout
    fig.update_layout(
        title={
            "text": "<b>OECD CLI 서브인덱스: 양수 비율</b>",
            "x": 0.5,
            "xanchor": "center",
            "font": {"family": "Inter, sans-serif", "size": 18},
        },
        xaxis_title="날짜",
        yaxis_title="양수 비율 (%)",
        height=450,
        showlegend=False,
        hovermode="x unified",
        plot_bgcolor="rgba(30, 41, 59, 0.3)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=12, color="#ffffff"),
        margin=dict(l=60, r=60, t=80, b=60),
    )
    
    # Update axes
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


def calculate_risk_metrics() -> Dict[str, Any]:
    """Calculate all risk metrics and return as a dictionary."""
    data = get_index_data().loc["2022":].ffill()
    
    if data.empty:
        return {}

    latest_date = data.index[-1]
    today = date.today()
    if latest_date.date() > today:
        latest_date = today # Convert to date object if needed? No, keep as is for consistency
        
    num_indices = len(data.columns)
    
    # Calculate sigma values
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
        
        # Guard against empty rolling results
        if len(rolling_mean) == 0:
            continue
            
        mean = rolling_mean.iloc[-1]
        std = rolling_std.iloc[-1]
        current = d.iloc[-1]

        if pd.notna(mean) and pd.notna(std) and pd.notna(current) and std != 0:
            z = (current - mean) / std
            if pd.notna(z):
                sigma_values.append(z)

    # Average sigma
    if sigma_values:
        avg_sigma = np.mean(sigma_values)
    else:
        avg_sigma = 0

    # Determine Alert Status
    alert_status = {
        "level": "Normal",
        "color": "#10b981",
        "text": "정상 상태",
        "badge": "중립",
        "sigma": avg_sigma
    }
    
    if len(sigma_values) > 0:
        abs_sigma = abs(avg_sigma)
        if abs_sigma >= 2.7:
            alert_status["level"] = "Critical"
            alert_status["color"] = "#dc2626" if avg_sigma < 0 else "#1d4ed8"
            alert_status["text"] = "🔴 위험 경보" if avg_sigma < 0 else "🔵 위험 경보"
        elif abs_sigma >= 2:
            alert_status["level"] = "Warning"
            alert_status["color"] = "#f59e0b" if avg_sigma < 0 else "#3b82f6"
            alert_status["text"] = "🟡 주의 경보" if avg_sigma < 0 else "🔵 주의 경보"

    # Positive Percentage
    positive_change = (data.pct_change().iloc[-1] > 0).sum()
    positive_pct = positive_change / num_indices if num_indices > 0 else 0
    
    positive_status = {
        "count": positive_change,
        "total": num_indices,
        "pct": positive_pct,
        "state": "Critical",
        "color": "#dc2626"
    }
    
    if positive_pct >= 0.75:
        positive_status.update({"state": "Strong", "color": "#10b981"})
    elif positive_pct >= 0.5:
        positive_status.update({"state": "Moderate", "color": "#3b82f6"})
    elif positive_pct >= 0.25:
        positive_status.update({"state": "Weak", "color": "#f59e0b"})

    # OECD CLI
    positive_pct_oecd = NumOfOECDLeadingPositiveMoM()
    latest_oecd_pct = positive_pct_oecd.iloc[-1] if len(positive_pct_oecd) > 0 else 0
    
    oecd_status = {
        "pct": latest_oecd_pct,
        "state": "Critical",
        "color": "#dc2626"
    }
    
    if latest_oecd_pct >= 75:
        oecd_status.update({"state": "Strong", "color": "#10b981"})
    elif latest_oecd_pct >= 50:
        oecd_status.update({"state": "Moderate", "color": "#3b82f6"})
    elif latest_oecd_pct >= 25:
        oecd_status.update({"state": "Weak", "color": "#f59e0b"})

    return {
        "latest_date": latest_date,
        "alert": alert_status,
        "positive": positive_status,
        "oecd": oecd_status
    }


def get_gauge_charts_data() -> List[Dict[str, Any]]:
    """Get figures and metadata for all gauges."""
    data = get_index_data().loc["2022":].ffill()
    
    if data.empty:
        return []

    gauge_order = [
        "코스피", "S&P 500", "한국CD91", "한국 3년", "한국 10년",
        "미국 10년", "미국 - 한국 10년", "한국회사채스프레드(AA-)", "달러 - 원 환율"
    ]

    indicator_types = {
        "코스피": "stock", "S&P 500": "stock",
        "한국CD91": "rate", "한국 3년": "rate", "한국 10년": "rate",
        "미국 10년": "rate", "미국 - 한국 10년": "rate",
        "한국회사채스프레드(AA-)": "rate", "달러 - 원 환율": "fx",
    }

    gauge_data = []
    for name in gauge_order:
        if name in data.columns:
            series = data[name].copy()
            series.name = name
            indicator_type = indicator_types.get(name, "rate")
            fig, current_state, state_color = make_gauge(series, indicator_type=indicator_type)
            
            gauge_data.append({
                "name": name,
                "figure": fig,
                "latest_value": series.iloc[-1],
                "change": series.pct_change().iloc[-1],
                "state": current_state,
                "color": state_color
            })
            
    return gauge_data
