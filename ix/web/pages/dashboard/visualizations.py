"""
Visualization module for dashboard.
Handles heatmap generation and chart utilities.
"""

import pandas as pd
import plotly.graph_objects as go
from typing import List, Optional


class HeatmapGenerator:
    """Generates performance heatmaps for dashboard visualization."""

    # Default color scheme for heatmaps
    DEFAULT_COLORSCALE = [
        [0, "#374151"],
        [0.4, "#dc2626"],
        [0.5, "#374151"],
        [0.6, "#059669"],
        [1, "#059669"],
    ]

    @staticmethod
    def performance_heatmap_from_perf_data(
        perf_df: pd.DataFrame, title: str = ""
    ) -> go.Figure:
        """Generate performance heatmap from pre-calculated performance data - optimized version."""
        if perf_df.empty:
            return HeatmapGenerator._create_empty_heatmap(title)

        # Convert percentages to display format (optimized)
        perf_matrix = perf_df.copy()
        for col in perf_df.columns:
            if col != "Latest":
                perf_matrix[col] = perf_df[col] * 100

        # Prepare data arrays for faster rendering
        z_values = perf_matrix.values
        z_colors = z_values.copy()
        z_colors[:, 0] = 0  # Neutral color for latest values

        # Create text array efficiently
        text_array = []
        for i, row in enumerate(z_values):
            text_row = []
            for j, (col, val) in enumerate(zip(perf_matrix.columns, row)):
                if col == "Latest":
                    text_row.append(f"{val:.2f}")
                else:
                    text_row.append(f"{val:.1f}%")
            text_array.append(text_row)

        fig = go.Figure(
            data=go.Heatmap(
                z=z_colors,
                x=perf_matrix.columns,
                y=perf_df.index,
                colorscale=HeatmapGenerator.DEFAULT_COLORSCALE,
                zmid=0,
                text=text_array,
                texttemplate="%{text}",
                textfont=dict(size=9, color="white", family="monospace"),
                hovertemplate="<b>%{y}</b><br>%{x}: %{text}<extra></extra>",
                showscale=False,
            )
        )

        # Add grid lines efficiently
        shapes = HeatmapGenerator._generate_grid_shapes(perf_matrix.shape)

        return HeatmapGenerator._apply_heatmap_layout(fig, shapes, title)

    @staticmethod
    def performance_heatmap(
        pxs: pd.DataFrame, periods: List[int] = [1, 5, 21], title: str = ""
    ) -> go.Figure:
        """Generate performance heatmap for given price data."""
        if pxs.empty:
            return HeatmapGenerator._create_empty_heatmap(title)

        # Calculate performance metrics
        performance_data = {}
        latest_values = pxs.resample("B").last().ffill().iloc[-1]
        performance_data["Latest"] = latest_values

        for p in periods:
            pct = pxs.resample("B").last().ffill().pct_change(p).ffill().iloc[-1]
            performance_data[f"{p}D"] = pct

        perf_df = pd.DataFrame(performance_data)
        perf_matrix = perf_df.copy()

        # Convert percentages to display format
        for col in perf_df.columns:
            if col != "Latest":
                perf_matrix[col] = perf_df[col] * 100

        z_values = perf_matrix.values.copy()
        z_colors = perf_matrix.values.copy()
        z_colors[:, 0] = 0  # Neutral color for latest values

        fig = go.Figure(
            data=go.Heatmap(
                z=z_colors,
                x=perf_matrix.columns,
                y=perf_df.index,
                colorscale=HeatmapGenerator.DEFAULT_COLORSCALE,
                zmid=0,
                text=[
                    [
                        f"{val:.2f}" if col == "Latest" else f"{val:.1f}%"
                        for col, val in zip(perf_matrix.columns, row)
                    ]
                    for row in z_values
                ],
                texttemplate="%{text}",
                textfont=dict(size=9, color="white", family="monospace"),
                hovertemplate="<b>%{y}</b><br>%{x}: %{text}<extra></extra>",
                showscale=False,
            )
        )

        # Add grid lines
        shapes = HeatmapGenerator._generate_grid_shapes(perf_matrix.shape)

        return HeatmapGenerator._apply_heatmap_layout(fig, shapes, title)

    @staticmethod
    def _create_empty_heatmap(title: str) -> go.Figure:
        """Create an empty heatmap figure with 'No data available' message."""
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=12, color="#ef4444"),
        )

        fig.update_layout(
            title=dict(
                text=title, x=0.5, xanchor="center", font=dict(size=12, color="#f1f5f9")
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=0, r=0, t=25, b=0),
            height=200,
        )
        return fig

    @staticmethod
    def _generate_grid_shapes(shape: tuple) -> List[dict]:
        """Generate grid line shapes for heatmap."""
        nrows, ncols = shape
        shapes = []
        for i in range(nrows):
            for j in range(ncols):
                shapes.append(
                    {
                        "type": "rect",
                        "x0": j - 0.5,
                        "x1": j + 0.5,
                        "y0": i - 0.5,
                        "y1": i + 0.5,
                        "line": {"color": "white", "width": 1},
                        "layer": "above",
                    }
                )
        return shapes

    @staticmethod
    def _apply_heatmap_layout(
        fig: go.Figure, shapes: List[dict], title: str
    ) -> go.Figure:
        """Apply standard layout styling to heatmap figure."""
        fig.update_layout(
            shapes=shapes,
            title=dict(
                text=title, x=0.5, xanchor="center", font=dict(size=12, color="#f1f5f9")
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(
                tickfont=dict(size=9, color="#f1f5f9"), side="top", showgrid=False
            ),
            yaxis=dict(
                tickfont=dict(size=9, color="#f1f5f9"),
                autorange="reversed",
                showgrid=False,
            ),
            margin=dict(l=0, r=0, t=25, b=0),
            height=200,
        )
        return fig


class ChartUtilities:
    """Utility functions for chart generation and formatting."""

    @staticmethod
    def format_performance_value(
        value: float, is_percentage: bool = False, decimals: int = 2
    ) -> str:
        """Format performance values for display."""
        if is_percentage:
            return f"{value:.1f}%"
        return f"{value:.{decimals}f}"

    @staticmethod
    def get_color_for_performance(value: float, is_percentage: bool = True) -> str:
        """Get color based on performance value."""
        if not is_percentage:
            return "#374151"  # Neutral for absolute values

        if value > 0:
            return "#059669"  # Green for positive
        elif value < 0:
            return "#dc2626"  # Red for negative
        else:
            return "#374151"  # Neutral for zero

    @staticmethod
    def create_hover_template(asset_name: str, period: str, value: str) -> str:
        """Create hover template for heatmap cells."""
        return f"<b>{asset_name}</b><br>{period}: {value}<extra></extra>"
