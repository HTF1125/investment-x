import pandas as pd
from ix.db.query import Series
from ix.core.tech.regime import Regime1
from ix.core.tech.ma import MACD


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
        import plotly.graph_objects as go
        from ix.dash.settings import theme

        fig = go.Figure()
        fig.update_layout(
            barmode="stack",
            title=dict(text=f"OECD CLI Regime Distribution"),
        )
        # Use theme.chart_colors for bar colors
        colors = theme.chart_colors

        if start is not None:
            regime_dist = self.regime_distribution.loc[start:]
        else:
            regime_dist = self.regime_distribution

        for i, (name, series) in enumerate(regime_dist.items()):
            color = colors[i % len(colors)]
            fig.add_trace(
                go.Bar(
                    x=series.index,
                    y=series.values,
                    name=name,
                    marker_color=color,
                    hovertemplate="%{y:.2f}",
                )
            )

        return fig.update_layout(
            title=dict(
                font=dict(size=14, color=theme.text),
                y=0.90,
                x=0.5,
                xanchor="center",
                yanchor="bottom",
                yref="container",
            ),
            paper_bgcolor=theme.bg,
            plot_bgcolor=theme.bg_light,
            font=dict(color=theme.text, family="Roboto, Arial, sans-serif", size=12),
            margin=dict(l=20, r=20, t=30, b=30),
            hovermode="x unified",
            hoverlabel=dict(
                bgcolor=theme.bg_light,
                bordercolor=theme.border,
                font=dict(color=theme.text, size=11),
            ),
            legend=dict(
                x=0.5,
                y=-0.15,
                xanchor="center",
                yanchor="top",
                orientation="h",
                bgcolor="rgba(0,0,0,0)",
                bordercolor=theme.border,
                borderwidth=1,
                font=dict(
                    color=theme.text,
                    size=10,
                ),
                itemsizing="trace",
                itemwidth=30,
                yref="paper",
                traceorder="normal",
            ),
            xaxis=dict(
                gridcolor=theme.border,
                gridwidth=0.5,
                zeroline=False,
                showline=True,
                linecolor=theme.border,
                tickformat="%b\n%Y",  # Month-Year
                tickfont=dict(color=theme.text_light, size=10),
                automargin="height",
            ),
            yaxis=dict(
                gridcolor=theme.border,
                gridwidth=0.5,
                zeroline=True,
                zerolinecolor=theme.text_light,
                zerolinewidth=1,
                tickfont=dict(color=theme.text_light, size=10),
                domain=[0, 0.9],
            ),
            yaxis2=dict(
                gridcolor=theme.border,
                gridwidth=0.5,
                zeroline=True,
                zerolinecolor=theme.text_light,
                zerolinewidth=1,
                tickfont=dict(color=theme.text_light, size=10),
                domain=[0, 0.9],
                overlaying="y",
                side="right",
            ),
            uniformtext=dict(minsize=10, mode="show"),
            autosize=True,
        )
