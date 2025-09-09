"""
Major Indices Chart Component
"""
import pandas as pd
import plotly.graph_objects as go
from ix import Series
from ix.misc.date import oneyearbefore

class IndicesChart:
    """Major Indices Chart Component"""

    def __init__(self):
        # Colors for different indices
        self.colors = {
            "S&P500": "#667eea",    # Primary theme color
            "DJIA30": "#764ba2",    # Secondary theme color
            "NASDAQ": "#10b981",    # Success color
            "Russell2": "#ef4444",  # Danger color
        }

    def load_data(self):
        """Load and process indices data"""
        try:
            print("Loading indices data...")

            indices_data = {}
            indices_config = {
                "S&P500": "SPX Index",
                "DJIA30": "INDU Index",
                "NASDAQ": "CCMP Index",
                "Russell2": "RTY Index"
            }

            for name, code in indices_config.items():
                try:
                    print(f"Loading data for {name} ({code})")
                    # Get price data and calculate cumulative returns from one year ago
                    series = Series(f'{code}:PX_LAST', freq='B')
                    if series.empty:
                        print(f"No data found for {code}")
                        continue

                    # Calculate percentage change from one year ago
                    one_year_ago = oneyearbefore().strftime('%Y-%m-%d')
                    series_from_year = series.loc[one_year_ago:]

                    if len(series_from_year) == 0:
                        print(f"No data from {one_year_ago} for {code}")
                        continue

                    # Calculate cumulative returns: pct_change().add(1).cumprod()*100-100
                    cumulative_returns = (
                        series_from_year.pct_change()
                        .add(1)
                        .cumprod()
                        .multiply(100)
                        .subtract(100)
                    ).dropna()

                    if len(cumulative_returns) > 0:
                        indices_data[name] = cumulative_returns
                        print(f"Loaded {len(cumulative_returns)} points for {name}")
                    else:
                        print(f"No valid returns data for {name}")

                except Exception as e:
                    print(f"Error loading data for {name}: {e}")

            if not indices_data:
                print("No indices data available")
                return None

            return indices_data

        except Exception as e:
            print(f"Error in load_data: {e}")
            import traceback
            traceback.print_exc()
            return None

    def create_chart(self, indices_data):
        """Create the Plotly chart with indices performance"""
        fig = go.Figure()

        # Sort indices by latest performance (descending)
        latest_values = {}
        for name, data in indices_data.items():
            if len(data) > 0:
                latest_values[name] = data.iloc[-1]

        # Sort by latest value descending
        sorted_indices = sorted(latest_values.items(), key=lambda x: x[1], reverse=True)

        # Add lines for each index
        for name, latest_value in sorted_indices:
            data = indices_data[name]
            legend_name = f"{name} ({latest_value:.2f}%)"

            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data.values,
                    mode="lines",
                    name=legend_name,
                    line=dict(color=self.colors.get(name, "#6b7280"), width=2.5),
                    hovertemplate=f"{name}: %{{y:.2f}}% (%{{x}})<extra></extra>",
                )
            )

        # Update layout to match website theme
        fig.update_layout(
            title={
                "text": "Major Indices - 1 Year Cumulative Returns<br><sub style='color: #6b7280; font-size: 14px;'>S&P500, DJIA30, NASDAQ, Russell2000</sub>",
                "x": 0.5,
                "xanchor": "center",
                "font": {
                    "size": 20,
                    "color": "#667eea",
                    "family": "Inter, sans-serif"
                },
            },
            xaxis_title="Date",
            yaxis_title="Cumulative Return (%)",
            xaxis=dict(
                title=dict(font=dict(color="#4b5563", family="Inter, sans-serif")),
                tickfont=dict(color="#6b7280", family="Inter, sans-serif"),
                gridcolor="#f3f4f6",
                showgrid=True,
            ),
            yaxis=dict(
                title=dict(font=dict(color="#4b5563", family="Inter, sans-serif")),
                tickfont=dict(color="#6b7280", family="Inter, sans-serif"),
                gridcolor="#f3f4f6",
                showgrid=True,
                zeroline=True,
                zerolinecolor="#d1d5db",
                zerolinewidth=2,
            ),
            hovermode="x unified",
            template="plotly_white",
            height=400,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.12,
                xanchor="center",
                x=0.5,
                bgcolor="rgba(249, 250, 251, 0.95)",
                bordercolor="#e5e7eb",
                borderwidth=1,
                font=dict(
                    size=11,
                    color="#374151",
                    family="Inter, sans-serif"
                )
            ),
            margin=dict(l=60, r=40, t=80, b=120),
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

    def get_chart_data(self):
        """Main method to load data and create chart"""
        try:
            # Load data
            indices_data = self.load_data()

            if not indices_data:
                return None, None

            # Create chart
            fig = self.create_chart(indices_data)

            return fig, indices_data

        except Exception as e:
            print(f"Error loading indices data: {str(e)}")
            return None, None

    def get_statistics(self, indices_data):
        """Get statistics for the indices"""
        if not indices_data:
            return None

        stats = {}
        for name, data in indices_data.items():
            if len(data) > 0:
                current_return = data.iloc[-1]
                max_return = data.max()
                min_return = data.min()
                stats[name] = {
                    'current': current_return,
                    'max': max_return,
                    'min': min_return
                }

        return stats
