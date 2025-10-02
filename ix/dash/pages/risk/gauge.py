import plotly.graph_objects as go
import numpy as np
import pandas as pd


def make_gauge(px: pd.Series):

    d = px.copy()

    # Rolling 3-year window length
    window = 52 * 2  # 156 weeks

    # Calculate rolling mean & std
    rolling_mean = d.rolling(window).mean()
    rolling_std = d.rolling(window).std()

    # Use the latest rolling window stats
    mean = rolling_mean.iloc[-1]
    std = rolling_std.iloc[-1]
    current = d.iloc[-1]
    z = (current - mean) / std

    # Custom thresholds (in sigma units, split at mean)
    sigma_thresholds = [-3.2, -2.7, -2, 0, 2, 2.7, 3.2]
    threshold_values = [mean + s * std for s in sigma_thresholds]

    # Enhanced color scheme with better state representation
    colors = [
        "#dc2626",  # < -2.7σ (red - critical negative)
        "#f59e0b",  # -2.7σ ~ -2σ (yellow - warning negative)
        "#6b7280",  # -2σ ~ 0 (grey - neutral negative)
        "#10b981",  # 0 ~ +2σ (green - neutral positive)
        "#3b82f6",  # +2σ ~ +2.7σ (blue - warning positive)
        "#1d4ed8",  # > +2.7σ (deep blue - critical positive)
    ]

    # Build gauge
    fig = go.Figure()

    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=current,
            number={
                "valueformat": ".2f",
                "font": {"family": "Inter, sans-serif", "size": 24, "color": "#ffffff"},
            },
            gauge={
                "axis": {
                    "range": [threshold_values[0], threshold_values[-1]],
                    "tickvals": threshold_values,
                    "ticktext": [f"{v:.2f}" for v in threshold_values],
                    "tickfont": {
                        "family": "Inter, sans-serif",
                        "size": 10,
                        "color": "#cbd5e0",
                    },
                    "tickcolor": "rgba(203, 213, 224, 0.8)",
                    "ticklabelstep": 1,
                },
                "bar": {
                    "color": "rgba(0,0,0,0)",
                    "line": {"color": "#ffffff", "width": 2},
                    "thickness": 1,
                },  # transparent needle with black border spanning full width
                "steps": [
                    {
                        "range": [threshold_values[i], threshold_values[i + 1]],
                        "color": colors[i],
                    }
                    for i in range(len(threshold_values) - 1)
                ],
            },
            domain={"x": [0, 1], "y": [0, 1]},
        )
    )

    # Determine color based on sigma value
    if abs(z) >= 2.7:
        title_color = "#1d4ed8" if z > 0 else "#dc2626"  # Deep blue or red
    elif abs(z) >= 2:
        title_color = "#3b82f6" if z > 0 else "#ef4444"  # Blue or red
    else:
        title_color = "#6b7280"  # Gray for neutral

    # Determine current state for badge
    if abs(z) >= 2.7:
        current_state = "위험 +" if z > 0 else "위험 -"
        state_color = "#1d4ed8" if z > 0 else "#dc2626"
    elif abs(z) >= 2:
        current_state = "주의 +" if z > 0 else "주의 -"
        state_color = "#3b82f6" if z > 0 else "#f59e0b"
    elif z >= 0:
        current_state = "중립 +"
        state_color = "#10b981"
    else:
        current_state = "중립 -"
        state_color = "#6b7280"

    # Add state badge as annotation in top right corner
    fig.add_annotation(
        x=0.95,
        y=0.95,
        xref="paper",
        yref="paper",
        text=current_state,
        showarrow=False,
        font=dict(family="Inter, sans-serif", size=10, color="white"),
        bgcolor=state_color,
        bordercolor=state_color,
        borderwidth=1,
        borderpad=4,
        ax=0,
        ay=0,
        xanchor="center",
        yanchor="middle",
    )

    fig.update_layout(
        title={
            "text": f"<b style='color: {title_color}; font-family: Inter, sans-serif; background: rgba(30, 41, 59, 0.9); padding: 6px 12px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.3); display: inline-block;'>{d.name}</b><br>"
            + f"<span style='font-size: 12px; color: #cbd5e0; background: rgba(30, 41, 59, 0.8); padding: 4px 8px; border-radius: 6px; margin: 2px 0; display: inline-block; box-shadow: 0 1px 4px rgba(0,0,0,0.2);'>5-Week Change: {current:.2f}</span>",
            "x": 0.5,
            "xanchor": "center",
            "font": {"family": "Inter, sans-serif", "size": 14},
        },
        height=250,
        autosize=True,
        margin=dict(l=30, r=30, t=80, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=10),
    )

    # Return both the figure and the current state information
    return fig, current_state, state_color
