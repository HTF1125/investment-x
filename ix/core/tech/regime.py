from typing import Optional, Union
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ix.db.client import get_timeseries
from ix.misc import get_logger

logger = get_logger(__name__)

class Regime1:
    """
    Classifies a centred-oscillator series into four business-cycle regimes:
        Expansion   : value ≥ 0 and rising
        Slowdown    : value ≥ 0 and falling
        Contraction : value < 0 and falling
        Recovery    : value < 0 and rising
    """

    def __init__(self, series: pd.Series, smooth_span: Optional[int] = None) -> None:
        self.raw = series.copy().dropna()
        self.smooth_span = smooth_span
        self._store: dict = {}
        self.df: pd.DataFrame = pd.DataFrame()
        self._calculate_regime()

    @classmethod
    def from_meta(
        cls,
        code: str,
        field: str = "PX_LAST",
        smooth_span: Optional[int] = None,
    ) -> "Regime1":
        src = get_timeseries(code=code).data
        return cls(series=src, smooth_span=smooth_span)

    # --------------------------- cached properties ------------------------- #
    @property
    def value(self) -> pd.Series:
        if "value" not in self._store:
            if self.smooth_span:
                self._store["value"] = self.raw.ewm(
                    span=self.smooth_span, adjust=False
                ).mean()
            else:
                self._store["value"] = self.raw.copy()
        return self._store["value"]

    @property
    def delta(self) -> pd.Series:
        if "delta" not in self._store:
            self._store["delta"] = self.value.diff().fillna(0.0)
        return self._store["delta"]

    @property
    def regime(self) -> pd.Series:
        if "regime" not in self._store:
            v, d = self.value, self.delta
            conds = [
                (v >= 0) & (d >= 0),
                (v >= 0) & (d < 0),
                (v < 0) & (d < 0),
                (v < 0) & (d >= 0),
            ]
            choices = ["Expansion", "Slowdown", "Contraction", "Recovery"]
            self._store["regime"] = pd.Series(
                np.select(conds, choices, default="Unknown"),
                index=v.index,
                name="regime",
            )
        return self._store["regime"]

    # ----------------------------- core compute ---------------------------- #
    def _calculate_regime(self) -> None:
        self.df = pd.DataFrame(
            {"value": self.value, "delta": self.delta, "regime": self.regime}
        )

    # ---------------------------- public helpers --------------------------- #
    def to_dataframe(
        self,
        start: Optional[Union[str, pd.Timestamp]] = None,
        end: Optional[Union[str, pd.Timestamp]] = None,
    ) -> pd.DataFrame:
        df = self.df.copy()
        if start is not None:
            df = df.loc[start:]
        if end is not None:
            df = df.loc[:end]
        return df

    def plot(
        self,
        start: Optional[Union[str, pd.Timestamp]] = None,
        end: Optional[Union[str, pd.Timestamp]] = None,
    ) -> go.Figure:
        df = self.to_dataframe(start=start, end=end)
        if df.empty:
            logger.warning("No data available for the selected date range.")
            return go.Figure()

        # Stronger and more visible colors
        color_map = {
            "Expansion": "rgba(0, 200, 0, 0.5)",  # green
            "Slowdown": "rgba(255, 165, 0, 0.5)",  # orange
            "Contraction": "rgba(200, 0, 0, 0.5)",  # red
            "Recovery": "rgba(0, 120, 255, 0.5)",  # blue
            "Unknown": "rgba(128, 128, 128, 0.3)",  # grey
        }

        fig = go.Figure()

        # 1. Value line
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["value"],
                name="Value",
                line=dict(color="white", width=1.5),
                hovertemplate="Date: %{x|%Y-%m-%d}<br>Value: %{y:.4f}",
            )
        )

        # 2. Regime backgrounds
        grouped = df["regime"] != df["regime"].shift()
        segment_id = grouped.cumsum()

        for _, seg in df.groupby(segment_id):
            regime = seg["regime"].iloc[0]
            x0 = seg.index[0]
            x1 = seg.index[-1]
            fillcolor = color_map.get(regime, "rgba(128,128,128,0.2)")

            fig.add_vrect(
                x0=x0,
                x1=x1,
                fillcolor=fillcolor,
                layer="below",
                line_width=0,
                opacity=1.0,  # we already control alpha in fillcolor
            )

        # 3. Manual dummy traces for legend
        for name, rgba in color_map.items():
            fig.add_trace(
                go.Scatter(
                    x=[None],
                    y=[None],
                    mode="markers",
                    marker=dict(size=10, color=rgba),
                    name=name,
                    showlegend=True,
                )
            )

        fig.update_layout(
            title=dict(
                text="Business-Cycle Regime Classification",
                x=0.05,
                y=0.95,
                xanchor="left",
                yanchor="top",
                font=dict(size=18, color="#ffffff"),
            ),
            xaxis=dict(
                title="Date",
                showgrid=True,
                gridcolor="lightgrey",
                type="date",
                range=[df.index.min(), df.index.max()],
            ),
            yaxis=dict(
                title="Value",
                showgrid=True,
                gridcolor="lightgrey",
                zeroline=True,
                zerolinecolor="lightgrey",
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.05,
                xanchor="left",
                x=0,
                bgcolor="rgba(0,0,0,0)",
                font=dict(color="white"),
            ),
            hovermode="x unified",
            hoverlabel=dict(bgcolor="black", font=dict(color="white")),
            margin=dict(l=50, r=50, t=80, b=50),
            template="plotly_dark",
        )

        return fig
