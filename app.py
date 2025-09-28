import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from ix.db.query import Series
from ix.core.tech.regime import Regime1
from ix.core.tech.ma import MACD
from ix.misc.theme import theme


# Configure Streamlit page
st.set_page_config(
    page_title="Investment X - OECD CLI Regime Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


class OecdCliRegime:

    def __init__(self, country: str = "USA") -> None:
        self.country = country


    @property
    def cli(self) -> pd.Series:
        return Series(f"{self.country}.LOLITOAA.STSA:PX_LAST", name=self.country)


    @property
    def regime(self) -> pd.Series:
        return Regime1(MACD(self.cli).histogram).regime

    def plot(self) -> go.Figure:
        return MACD(self.cli).plot()



class OecdCliRegimeDistribution:
    """
    OECD Composite Leading Indicator (CLI) Regime Analyzer.
    Provides methods to fetch, clean, and classify CLI data for a set of countries
    into business cycle regimes using MACD and a four-phase regime model.
    """

    COUNTRIES = [
        "USA",
        "TUR",
        "IND",
        "IDN",
        "A5M",
        "CHN",
        "KOR",
        "BRA",
        "AUS",
        "CAN",
        "DEU",
        "ESP",
        "FRA",
        "G4E",
        "G7M",
        "GBR",
        "ITA",
        "JPN",
        "MEX",
    ]

    def __init__(self, min_valid_obs: int = 10):
        """
        Args:
            min_valid_obs: Minimum number of non-NA values required to keep a country series.
        """
        self.min_valid_obs = min_valid_obs
        self.data = self.get_data()
        self.regime = self.get_regime()
        self.regime_distribution = self.get_regime_distribution()

    def get_data(self) -> pd.DataFrame:
        """
        Fetches and returns the CLI data for all countries as a DataFrame.
        Drops countries with insufficient data.
        Returns:
            pd.DataFrame: CLI data, columns are country codes.
        """
        series_list = []
        for country in self.COUNTRIES:
            s = Series(f"{country}.LOLITOAA.STSA:PX_LAST", name=country)
            series_list.append(s)
        data = pd.concat(series_list, axis=1)
        # Drop columns with too many missing values
        data = data.dropna(thresh=self.min_valid_obs, axis=1)
        data.index = pd.to_datetime(data.index)
        return data.copy()

    def get_regime(self) -> pd.DataFrame:
        """
        Computes the business cycle regime for each country and date.
        Returns:
            pd.DataFrame: Regime for each country (columns) and date (index).
        """

        regimes = {}
        for country, series in self.data.items():
            # MACD histogram as oscillator input
            try:
                hist = MACD(series).histogram
            except Exception:
                # If MACD fails, fill with NaN
                hist = pd.Series(index=series.index, data=pd.NA)
            regime = Regime1(hist).regime
            regimes[country] = regime
        regimes_df = pd.DataFrame(regimes)
        return regimes_df.copy()

    def get_regime_distribution(self) -> pd.DataFrame:
        """
        Calculates the percentage of countries in each regime at each date.
        Returns:
            pd.DataFrame: Index is date, columns are regime names, values are percent.
        """

        # For each date, count the percent of countries in each regime
        def pct(row):
            counts = row.value_counts(normalize=True) * 100
            # Ensure all regimes are present
            for regime in ["Expansion", "Slowdown", "Contraction", "Recovery"]:
                if regime not in counts:
                    counts[regime] = 0.0
            return counts[["Expansion", "Slowdown", "Contraction", "Recovery"]]

        regime_pct = self.regime.apply(pct, axis=1)
        regime_pct = regime_pct.fillna(0).round(2)
        regime_pct.index = pd.to_datetime(regime_pct.index)
        # Ensure DataFrame output (not Series)
        if isinstance(regime_pct, pd.Series):
            regime_pct = regime_pct.to_frame().T
        return regime_pct.sort_index()

    def plot(self, start: str | None = None):
        """
        Create a styled plotly chart using the theme colors and styling.
        """
        # Use theme colors for the four regimes
        regime_colors = [
            theme.colors.blue[400],  # Expansion - Blue
            theme.colors.amber[400],  # Slowdown - Amber/Yellow
            theme.colors.red[400],  # Contraction - Red
            theme.colors.emerald[400],  # Recovery - Green
        ]

        fig = go.Figure()
        fig.update_layout(
            barmode="stack",
            title=dict(text="OECD CLI Regime Distribution"),
        )

        if start is not None:
            regime_dist = self.regime_distribution.loc[start:]
        else:
            regime_dist = self.regime_distribution

        # Debug: print overall data info
        print(f"Regime distribution shape: {regime_dist.shape}")
        print(f"Regime distribution columns: {list(regime_dist.columns)}")
        print(f"Date range: {regime_dist.index.min()} to {regime_dist.index.max()}")

        for i, (name, series) in enumerate(regime_dist.items()):
            color = regime_colors[i % len(regime_colors)]
            # Debug: print data info
            print(
                f"Adding {name}: {len(series)} points, range: {series.min():.2f} to {series.max():.2f}"
            )
            fig.add_trace(
                go.Bar(
                    x=series.index,
                    y=series.values,
                    name=name,
                    marker_color=color,
                    hovertemplate="%{y:.2f}",
                )
            )

        # Add SPY data on secondary y-axis with error handling
        spy_data_available = False
        try:
            spy = Series("SPX Index:PX_LAST", name="SPY", freq="W").pct_change(52) * 100

            # Filter SPY data to match the regime data date range
            if start is not None:
                spy = spy.loc[start:]

            # Only add SPY trace if we have valid data
            if not spy.empty and spy.notna().any():
                fig.add_trace(
                    go.Scatter(
                        x=spy.index,
                        y=spy.values,
                        name="S&P500 YoY",
                        yaxis="y2",
                        line=dict(color=theme.colors.indigo[900], width=2),
                        hovertemplate="%{y:.2f}",
                    )
                )
                spy_data_available = True
                print(f"SPY data added: {len(spy)} points")
        except Exception as e:
            # If SPY data fails to load, continue without it
            print(f"SPY data error: {e}")
            pass

        # Apply theme styling
        layout_config = {
            "title": dict(
                font=dict(size=16, color=theme.colors.text),
                y=0.90,
                x=0.5,
                xanchor="center",
                yanchor="bottom",
                yref="container",
            ),
            "font": dict(family=theme.fonts.base, size=12, color=theme.colors.text),
            "margin": dict(l=20, r=20, t=40, b=30),
            "hovermode": "x unified",
            "hoverlabel": dict(
                bgcolor=theme.colors.surface,
                bordercolor=theme.colors.border,
                font=dict(color=theme.colors.text, size=11),
            ),
            "legend": dict(
                x=0.5,
                y=-0.15,
                xanchor="center",
                yanchor="top",
                orientation="h",
                bgcolor="rgba(0,0,0,0)",
                bordercolor=theme.colors.border,
                borderwidth=1,
                font=dict(
                    color=theme.colors.text,
                    size=11,
                ),
                itemsizing="trace",
                itemwidth=30,
                yref="paper",
                traceorder="normal",
            ),
            "paper_bgcolor": theme.colors.background,
            "plot_bgcolor": theme.colors.background_subtle,
            "xaxis": dict(
                gridcolor=theme.colors.border,
                gridwidth=0.5,
                zeroline=False,
                showline=True,
                linecolor=theme.colors.border,
                tickformat="%b\n%Y",  # Month-Year
                automargin="height",
                tickfont=dict(color=theme.colors.text_muted, size=10),
            ),
            "yaxis": dict(
                gridcolor=theme.colors.border,
                gridwidth=0.5,
                zeroline=True,
                zerolinecolor=theme.colors.text_subtle,
                zerolinewidth=1,
                tickfont=dict(color=theme.colors.text_muted, size=10),
                domain=[0, 0.9],
                title=dict(
                    text="Percentage of Countries",
                    font=dict(color=theme.colors.text, size=12),
                ),
            ),
            "uniformtext": dict(minsize=10, mode="show"),
            "autosize": True,
            "height": 500,
        }

        # Only add yaxis2 if SPY data is available
        if spy_data_available:
            layout_config["yaxis2"] = dict(
                gridcolor=theme.colors.border,
                gridwidth=0.5,
                zeroline=True,
                zerolinecolor=theme.colors.text_subtle,
                zerolinewidth=1,
                tickfont=dict(color=theme.colors.text_muted, size=10),
                domain=[0, 0.9],
                overlaying="y",
                side="right",
                title=dict(
                    text="SPY 52W % Change",
                    font=dict(color=theme.colors.text, size=12),
                ),
            )

        return fig.update_layout(**layout_config)


def main():
    """Main Streamlit application"""

    # Header
    st.title("📊 OECD CLI Regime Analysis")
    st.markdown(
        "Analyzing business cycle regimes across OECD countries using Composite Leading Indicators"
    )

    # Sidebar controls
    st.sidebar.header("Controls")

    # Date range selector
    st.sidebar.subheader("Date Range")
    start_date = st.sidebar.date_input(
        "Start Date",
        value=None,
        help="Select start date for analysis (leave empty for all data)",
    )

    # Minimum observations selector
    min_obs = st.sidebar.slider(
        "Minimum Observations",
        min_value=5,
        max_value=50,
        value=10,
        help="Minimum number of observations required to include a country",
    )

    # Analysis parameters
    st.sidebar.subheader("Analysis Parameters")
    show_summary = st.sidebar.checkbox("Show Summary Statistics", value=True)
    show_data_table = st.sidebar.checkbox("Show Data Table", value=False)

    # Load data with progress indicator
    with st.spinner("Loading OECD CLI data and computing regimes..."):
        try:
            analyzer = OecdCliRegimeDistribution(min_valid_obs=min_obs)

            # Convert start_date to string if provided
            start_str = start_date.strftime("%Y-%m-%d") if start_date else None

            # Display summary metrics
            if show_summary:
                st.subheader("📈 Current Regime Distribution")

                # Get latest regime distribution
                latest_data = analyzer.regime_distribution.iloc[-1]

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(
                        "Expansion",
                        f"{latest_data['Expansion']:.1f}%",
                        delta=(
                            f"{latest_data['Expansion'] - analyzer.regime_distribution.iloc[-2]['Expansion']:.1f}%"
                            if len(analyzer.regime_distribution) > 1
                            else None
                        ),
                    )

                with col2:
                    st.metric(
                        "Slowdown",
                        f"{latest_data['Slowdown']:.1f}%",
                        delta=(
                            f"{latest_data['Slowdown'] - analyzer.regime_distribution.iloc[-2]['Slowdown']:.1f}%"
                            if len(analyzer.regime_distribution) > 1
                            else None
                        ),
                    )

                with col3:
                    st.metric(
                        "Contraction",
                        f"{latest_data['Contraction']:.1f}%",
                        delta=(
                            f"{latest_data['Contraction'] - analyzer.regime_distribution.iloc[-2]['Contraction']:.1f}%"
                            if len(analyzer.regime_distribution) > 1
                            else None
                        ),
                    )

                with col4:
                    st.metric(
                        "Recovery",
                        f"{latest_data['Recovery']:.1f}%",
                        delta=(
                            f"{latest_data['Recovery'] - analyzer.regime_distribution.iloc[-2]['Recovery']:.1f}%"
                            if len(analyzer.regime_distribution) > 1
                            else None
                        ),
                    )

            # Display the main chart
            st.subheader("📊 Regime Distribution Over Time")
            fig = analyzer.plot(start=start_str)
            st.plotly_chart(fig, use_container_width=True)

            # Display data table if requested
            if show_data_table:
                st.subheader("📋 Data Table")
                display_data = analyzer.regime_distribution.copy()
                if start_str:
                    display_data = display_data.loc[start_str:]

                st.dataframe(display_data, use_container_width=True, height=400)

            # Additional insights
            st.subheader("💡 Key Insights")

            # Calculate some basic insights
            latest_regime_dist = analyzer.regime_distribution.iloc[-1]
            dominant_regime = latest_regime_dist.idxmax()
            dominant_percentage = latest_regime_dist.max()

            st.info(
                f"**Current Dominant Regime:** {dominant_regime} ({dominant_percentage:.1f}% of countries)"
            )

            # Show trend over last 6 months if available
            if len(analyzer.regime_distribution) >= 6:
                recent_trend = analyzer.regime_distribution.tail(6)
                st.write("**Recent Trend (Last 6 Months):**")

                trend_col1, trend_col2 = st.columns(2)
                with trend_col1:
                    st.write(
                        "Expansion:", f"{recent_trend['Expansion'].mean():.1f}% avg"
                    )
                    st.write("Slowdown:", f"{recent_trend['Slowdown'].mean():.1f}% avg")

                with trend_col2:
                    st.write(
                        "Contraction:", f"{recent_trend['Contraction'].mean():.1f}% avg"
                    )
                    st.write("Recovery:", f"{recent_trend['Recovery'].mean():.1f}% avg")

        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            st.info("Please check your data connection and try again.")

    # Footer
    st.markdown("---")
    st.markdown(
        "**Data Source:** OECD Composite Leading Indicators | "
        "**Methodology:** MACD-based regime classification | "
        "**Theme:** Investment X Dark Theme"
    )


if __name__ == "__main__":
    main()
