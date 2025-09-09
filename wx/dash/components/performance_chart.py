"""
Universal Performance Chart Component for all universe sections
"""
import pandas as pd
import plotly.graph_objects as go
from ix import Series
from datetime import datetime, timedelta


class PerformanceChart:
    """Universal Performance Chart Component"""

    def __init__(self):
        # Default colors for chart lines
        self.default_colors = [
            "#667eea", "#764ba2", "#10b981", "#ef4444", "#f59e0b",
            "#8b5cf6", "#06b6d4", "#84cc16", "#f97316", "#ec4899",
            "#6366f1", "#14b8a6", "#eab308", "#dc2626", "#7c3aed"
        ]

    def oneyearbefore(self):
        """Get date one year before today"""
        return (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

    def load_performance_data(self, universe_config):
        """Load and process performance data for a universe section"""
        try:
            print(f"Loading performance data for {len(universe_config)} assets...")

            performance_data = {}

            for i, asset in enumerate(universe_config):
                asset_code = asset["code"]
                asset_name = asset["name"]

                try:
                    print(f"Loading data for {asset_name} ({asset_code})")

                    # Determine the price field based on asset type
                    if "Index" in asset_code:
                        price_field = "PX_LAST"
                    elif "Equity" in asset_code:
                        price_field = "PX_LAST"
                    elif "Comdty" in asset_code or "Curncy" in asset_code:
                        price_field = "PX_LAST"
                    elif asset_code == "GOLDCOMP":  # Special case for gold
                        price_field = "PX_LAST"
                    else:
                        price_field = "PX_LAST"

                    # Get price data
                    series = Series(f'{asset_code}:{price_field}', freq='B')
                    if series.empty:
                        print(f"No data found for {asset_code}")
                        continue

                    # Calculate cumulative returns from one year ago
                    # Pattern: pct_change().loc[oneyearbefore():].add(1).cumprod()*100-100
                    one_year_ago = self.oneyearbefore()
                    series_from_year = series.loc[one_year_ago:]

                    if len(series_from_year) == 0:
                        print(f"No data from {one_year_ago} for {asset_code}")
                        continue

                    # Calculate cumulative returns
                    cumulative_returns = (
                        series_from_year.pct_change()
                        .add(1)
                        .cumprod()
                        .multiply(100)
                        .subtract(100)
                    ).dropna()

                    if len(cumulative_returns) > 0:
                        performance_data[asset_name] = cumulative_returns
                        print(f"Loaded {len(cumulative_returns)} points for {asset_name}")
                    else:
                        print(f"No valid returns data for {asset_name}")

                except Exception as e:
                    print(f"Error loading data for {asset_name}: {e}")

            if not performance_data:
                print("No performance data available")
                return None

            return performance_data

        except Exception as e:
            print(f"Error in load_performance_data: {e}")
            import traceback
            traceback.print_exc()
            return None

    def create_chart(self, performance_data, universe_name, universe_icon):
        """Create the Plotly chart with performance data"""
        fig = go.Figure()

        if not performance_data:
            return fig

        # Sort assets by latest performance (descending) - matching SORT=DESC
        latest_values = {}
        for name, data in performance_data.items():
            if len(data) > 0:
                latest_values[name] = data.iloc[-1]

        # Sort by latest value descending
        sorted_assets = sorted(latest_values.items(), key=lambda x: x[1], reverse=True)

        # Add lines for each asset
        for i, (name, latest_value) in enumerate(sorted_assets):
            data = performance_data[name]
            color = self.default_colors[i % len(self.default_colors)]
            legend_name = f"{name} ({latest_value:.2f}%)"

            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data.values,
                    mode="lines",
                    name=legend_name,
                    line=dict(color=color, width=2),
                    hovertemplate=f"{name}: %{{y:.2f}}% (%{{x}})<extra></extra>",
                )
            )

        # Update layout to match website theme
        fig.update_layout(
            title={
                "text": f"{universe_icon} {universe_name} - 1 Year Performance<br><sub style='color: #6b7280; font-size: 12px;'>Cumulative Returns (Sorted by Performance)</sub>",
                "x": 0.5,
                "xanchor": "center",
                "font": {
                    "size": 18,
                    "color": "#667eea",
                    "family": "Inter, sans-serif"
                },
            },
            xaxis_title="",
            yaxis_title="Cumulative Return (%)",
            xaxis=dict(
                title=dict(font=dict(color="#4b5563", family="Inter, sans-serif")),
                tickfont=dict(color="#6b7280", family="Inter, sans-serif", size=10),
                gridcolor="#f3f4f6",
                showgrid=True,
            ),
            yaxis=dict(
                title=dict(font=dict(color="#4b5563", family="Inter, sans-serif")),
                tickfont=dict(color="#6b7280", family="Inter, sans-serif", size=10),
                gridcolor="#f3f4f6",
                showgrid=True,
                zeroline=True,
                zerolinecolor="#d1d5db",
                zerolinewidth=2,
            ),
            hovermode="x unified",
            template="plotly_white",
            height=500,
            showlegend=True,
            # Let Plotly automatically determine optimal legend placement
            legend=dict(
                bgcolor="rgba(249, 250, 251, 0.95)",
                bordercolor="#e5e7eb",
                borderwidth=1,
                font=dict(
                    size=9,
                    color="#374151",
                    family="Inter, sans-serif"
                )
            ),
            margin=dict(l=60, r=40, t=80, b=60),  # Reduced bottom margin for auto-placement
            plot_bgcolor="rgba(249, 250, 251, 0.5)",
            paper_bgcolor="white",
        )

        # Add styled zero line
        fig.add_hline(
            y=0,
            line_dash="dash",
            line_color="#9ca3af",
            opacity=0.8,
            line_width=1.5
        )

        return fig

    def get_chart_data(self, universe_config, universe_name, universe_icon):
        """Main method to load data and create chart"""
        try:
            # Load data
            performance_data = self.load_performance_data(universe_config)

            if not performance_data:
                return None, None

            # Create chart
            fig = self.create_chart(performance_data, universe_name, universe_icon)

            return fig, performance_data

        except Exception as e:
            print(f"Error loading performance data for {universe_name}: {str(e)}")
            return None, None
