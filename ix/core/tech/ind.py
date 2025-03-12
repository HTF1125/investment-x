from typing import Optional, Union
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from ix.db import get_timeseries
from ix.misc import get_logger

logger = get_logger(__name__)


class EhlersLeadingIndicator:
    """
    Implements the Ehlers Leading Indicator (ELI) for financial time series analysis.
    This class computes the indicator values and provides visualization tools.
    """

    @classmethod
    def from_meta(
        cls,
        code: str,
        alpha1: float = 0.25,
        alpha2: float = 0.33,
    ) -> "EhlersLeadingIndicator":
        """
        Factory method to create an instance of EhlersLeadingIndicator using metadata.
        :param code: Identifier for fetching price data.
        :param alpha1: First smoothing factor (default: 0.25).
        :param alpha2: Second smoothing factor (default: 0.33).
        :return: An instance of EhlersLeadingIndicator.
        """
        try:
            px_high = get_timeseries(code=code, field="PX_HIGH")
            px_low = get_timeseries(code=code, field="PX_LOW")
            return cls(px_high=px_high, px_low=px_low, alpha1=alpha1, alpha2=alpha2)
        except Exception as e:
            logger.error(f"Error initializing EhlersLeadingIndicator: {e}")
            raise ValueError("Failed to fetch or process time series data.")

    def __init__(
        self,
        px_high: pd.Series,
        px_low: pd.Series,
        alpha1: float = 0.25,
        alpha2: float = 0.33,
    ):
        """
        Initializes the Ehlers Leading Indicator.
        :param px_high: Pandas Series of high prices.
        :param px_low: Pandas Series of low prices.
        :param alpha1: First smoothing factor (default: 0.25).
        :param alpha2: Second smoothing factor (default: 0.33).
        """
        if not isinstance(px_high, pd.Series) or not isinstance(px_low, pd.Series):
            raise TypeError("px_high and px_low must be pandas Series.")
        if px_high.empty or px_low.empty:
            raise ValueError("Input price series cannot be empty.")

        self.px_high = px_high.copy()
        self.px_low = px_low.copy()
        self.hl2 = (self.px_high + self.px_low) / 2  # Midpoint calculation
        self.alpha1 = alpha1
        self.alpha2 = alpha2
        self.df = pd.DataFrame(index=self.hl2.index)

        # Compute indicator values
        self._calculate_indicator()

    def _calculate_indicator(self) -> None:
        """
        Computes the Ehlers Leading Indicator components: Lead, EMA, Signal, and Bar Color.
        """
        lead = np.zeros(len(self.hl2))
        net_lead = np.zeros(len(self.hl2))
        ema = np.zeros(len(self.hl2))

        for i in range(1, len(self.hl2)):
            # Calculate Lead
            lead[i] = (
                (2 * self.hl2.iloc[i])
                + ((self.alpha1 - 2) * self.hl2.iloc[i - 1])
                + ((1 - self.alpha1) * lead[i - 1])
            )

            # Calculate Net Lead
            net_lead[i] = (self.alpha2 * lead[i]) + (
                (1 - self.alpha2) * net_lead[i - 1]
            )

            # Calculate EMA
            ema[i] = (0.5 * self.hl2.iloc[i]) + (0.5 * ema[i - 1])

        # Assign computed values to DataFrame
        self.df["lead"] = net_lead
        self.df["ema"] = ema
        self.df["signal"] = np.where(
            self.df["lead"] > self.df["ema"],
            1,
            np.where(self.df["lead"] < self.df["ema"], -1, 0),
        )

        # Assign bar colors for visualization
        prev_signal = self.df["signal"].shift(1)
        self.df["bar_color"] = np.select(
            [
                (self.df["signal"] > 0) & (self.df["signal"] > prev_signal),  # Lime
                (self.df["signal"] > 0) & ~(self.df["signal"] > prev_signal),  # Green
                (self.df["signal"] < 0) & (self.df["signal"] < prev_signal),  # Red
                (self.df["signal"] < 0) & ~(self.df["signal"] < prev_signal),  # Maroon
            ],
            ["lime", "green", "red", "maroon"],
            default="green",
        )

    def to_dataframe(
        self,
        start: Optional[Union[str, pd.Timestamp]] = None,
        end: Optional[Union[str, pd.Timestamp]] = None,
    ) -> pd.DataFrame:
        """
        Returns the computed indicator data as a DataFrame.
        :param start: Start date for filtering (optional).
        :param end: End date for filtering (optional).
        :return: Filtered DataFrame containing HL2, Lead, EMA, Signal, and Bar Color.
        """
        df = self.df.copy()
        df["hl2"] = self.hl2  # Add HL2 column for reference
        if start:
            df = df.loc[start:]
        if end:
            df = df.loc[:end]
        return df

    def plot(
        self,
        start: Optional[Union[str, pd.Timestamp]] = None,
        end: Optional[Union[str, pd.Timestamp]] = None,
    ) -> go.Figure:
        """
        Creates an interactive Plotly chart of the Ehlers Leading Indicator with color-coded HL2.
        :param start: Start date for filtering (optional).
        :param end: End date for filtering (optional).
        :return: Plotly Figure object.
        """
        df = self.to_dataframe(start=start, end=end)
        if df.empty:
            logger.warning("No data available for the selected date range.")
            return go.Figure()

        fig = go.Figure()

        # --- Color-coded HL2 Price Line ---
        for i in range(1, len(df)):
            fig.add_trace(
                go.Scatter(
                    x=[df.index[i - 1], df.index[i]],
                    y=[df["hl2"].iloc[i - 1], df["hl2"].iloc[i]],
                    mode="lines",
                    line=dict(color=df["bar_color"].iloc[i], width=2),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

        # --- EMA Line ---
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["ema"],
                mode="lines",
                name="EMA",
                line=dict(color="black", width=1, dash="dash"),
                hovertemplate="Date: %{x|%Y-%m-%d}<br>EMA: %{y:.2f}<extra></extra>",
            )
        )

        # --- Layout Configuration ---
        fig.update_layout(
            title="Ehlers Leading Indicator (ELI)",
            xaxis=dict(
                title="Date",
                showgrid=True,
                gridcolor="lightgrey",
                type="date",
                range=[df.index.min(), df.index.max()],
            ),
            yaxis=dict(
                title="Price",
                showgrid=True,
                gridcolor="lightgrey",
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
            ),
            hovermode="x unified",
            hoverlabel=dict(
                bgcolor="black",
                font=dict(color="white"),
            ),
            margin=dict(l=25, r=25, t=25, b=25),
            template="plotly_dark",
        )

        return fig
