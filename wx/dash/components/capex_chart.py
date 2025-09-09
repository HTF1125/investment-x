"""
Tech Companies CAPEX Chart Component
"""
import pandas as pd
import plotly.graph_objects as go
from ix import Series


class TechCapexChart:
    """Tech Companies CAPEX Chart Component"""

    def __init__(self):
        # Updated colors to match website theme
        self.colors = {
            "NVDA": "#667eea",  # Primary theme color
            "MSFT": "#764ba2",  # Secondary theme color
            "AMZN": "#10b981",  # Success color
            "META": "#ef4444",  # Danger color
            "GOOG": "#f59e0b",  # Warning color
            "Total": "#1f2937"  # Dark neutral for total line
        }

    def load_data(self):
        """Load and process CAPEX data"""
        try:
            print("Loading CAPEX data...")

            # Forward-looking CAPEX data
            ff_data = {}
            for code in ["NVDA", "MSFT", "AMZN", "META", "GOOG"]:
                try:
                    series_code = f"{code}:FF_CAPEX_Q"
                    print(f"Loading forward-looking data for {series_code}")
                    data = Series(series_code)
                    if data.empty:
                        print(f"No forward-looking data found for {series_code}")
                    else:
                        print(f"Loaded {len(data)} points for {series_code}")
                        ff_data[code] = data
                except Exception as e:
                    print(f"Error loading forward-looking data for {code}: {e}")

            if not ff_data:
                print("No forward-looking CAPEX data available")
                return None, None

            ff = (
                pd.DataFrame(ff_data)
                .resample("B")
                .last()
                .ffill()
                .dropna()
                .reindex(pd.date_range("2010-1-1", pd.Timestamp("today")))
                .ffill()
            )
            print(f"Forward-looking data processed: {ff.shape}")

            # Historical CAPEX data
            fe_data = {}
            for code in ["NVDA", "MSFT", "AMZN", "META", "GOOG"]:
                try:
                    series_code = f"{code}:FE_CAPEX_Q"
                    print(f"Loading historical data for {series_code}")
                    data = Series(series_code)
                    if data.empty:
                        print(f"No historical data found for {series_code}")
                    else:
                        print(f"Loaded {len(data)} points for {series_code}")
                        fe_data[code] = data
                except Exception as e:
                    print(f"Error loading historical data for {code}: {e}")

            if not fe_data:
                print("No historical CAPEX data available")
                return None, None

            fe = pd.DataFrame(fe_data).resample("B").last().ffill().dropna()
            print(f"Historical data processed: {fe.shape}")

            return ff, fe

        except Exception as e:
            print(f"Error in load_data: {e}")
            import traceback
            traceback.print_exc()
            return None, None

    def calculate_weekly_changes(self, fe):
        """Calculate weekly percentage changes for individual companies and total"""
        # Calculate the weekly percentage change for total
        weekly_pct_change = (
            fe.sum(axis=1).resample("W-Fri").last().pct_change(int(52)).loc["2007":]
        )

        # Calculate individual company weekly percentage changes
        individual_weekly_changes = {}
        for company in ["NVDA", "MSFT", "AMZN", "META", "GOOG"]:
            individual_weekly_changes[company] = (
                fe[company].resample("W-Fri").last().pct_change(int(52)).loc["2007":]
            )

        return weekly_pct_change, individual_weekly_changes

    def create_chart(self, weekly_pct_change, individual_weekly_changes):
        """Create the Plotly chart with individual companies and total"""
        fig = go.Figure()

        # Add individual company lines
        for company in ["NVDA", "MSFT", "AMZN", "META", "GOOG"]:
            if len(individual_weekly_changes[company]) > 0:
                # Get the latest value for legend
                latest_value = individual_weekly_changes[company].iloc[-1] * 100
                legend_name = f"{company}({latest_value:.2f}%)"

                fig.add_trace(
                    go.Scatter(
                        x=individual_weekly_changes[company].index,
                        y=individual_weekly_changes[company].values * 100,
                        mode="lines",
                        name=legend_name,
                        line=dict(color=self.colors[company], width=1.5),
                        hovertemplate=f"{company}: %{{y:.2f}}% (%{{x}})<extra></extra>",
                    )
                )

        # Add the total line (thicker and more prominent)
        # Get the latest value for total legend
        latest_total_value = weekly_pct_change.iloc[-1] * 100
        total_legend_name = f"Total({latest_total_value:.2f}%)"

        fig.add_trace(
            go.Scatter(
                x=weekly_pct_change.index,
                y=weekly_pct_change.values * 100,  # Convert to percentage
                mode="lines",
                name=total_legend_name,
                line=dict(color=self.colors["Total"], width=3),
                hovertemplate="Total: %{y:.2f}% (%{x})<extra></extra>",
            )
        )

        # Update layout to match website theme
        fig.update_layout(
            title={
                "text": "Tech Companies CAPEX - 52-Week Percentage Change<br><sub style='color: #6b7280; font-size: 14px;'>Individual Companies and Total</sub>",
                "x": 0.5,
                "xanchor": "center",
                "font": {
                    "size": 24,
                    "color": "#667eea",
                    "family": "Inter, sans-serif"
                },
            },
            xaxis_title="",
            yaxis_title="Percentage Change (%)",
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
            height=700,
            showlegend=True,
            # Let Plotly automatically determine optimal legend placement
            legend=dict(
                bgcolor="rgba(249, 250, 251, 0.95)",
                bordercolor="#e5e7eb",
                borderwidth=1,
                font=dict(
                    size=11,
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

    def get_chart_data(self):
        """Main method to load data and create chart"""
        try:
            # Load data
            ff, fe = self.load_data()

            # Calculate weekly changes
            weekly_pct_change, individual_weekly_changes = self.calculate_weekly_changes(fe)

            # Create chart
            fig = self.create_chart(weekly_pct_change, individual_weekly_changes)

            return fig, weekly_pct_change, individual_weekly_changes

        except Exception as e:
            print(f"Error loading CAPEX data: {str(e)}")
            return None, None, None

    def get_statistics(self, weekly_pct_change):
        """Get statistics for the chart"""
        if weekly_pct_change is None or len(weekly_pct_change) == 0:
            return None, None, None

        current_change = weekly_pct_change.iloc[-1] * 100
        max_change = weekly_pct_change.max() * 100
        min_change = weekly_pct_change.min() * 100

        return current_change, max_change, min_change
