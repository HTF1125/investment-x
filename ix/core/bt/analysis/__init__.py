from typing import Optional
import pandas as pd
import plotly.graph_objects as go
from ix.db.client import get_timeseries


class UsDollarAndFed:
    def __init__(self) -> None:
        self.dollar = get_timeseries(code="DXY Index", field="PX_LAST", name="Dollar")
        self.ff1 = get_timeseries(code="FF1 Comdty", field="PX_LAST", name="FF1")
        self.ff12 = get_timeseries(code="FF12 Comdty", field="PX_LAST", name="FF12")

    def to_dataframe(
        self, start: Optional[str] = None, end: Optional[str] = None
    ) -> pd.DataFrame:
        """Converts the time series data into a DataFrame with a calculated rate spread."""
        df = pd.DataFrame({"Dollar": self.dollar, "FF1": self.ff1, "FF12": self.ff12})
        df["FF12_FF1"] = (
            df["FF1"] - df["FF12"]
        )  # Calculate rate spread (tightening/easing)
        df.dropna(inplace=True)  # Drop NaN values for clean data

        # Ensure the index is datetime for proper filtering
        df.index = pd.to_datetime(df.index)

        if start:
            df = df.loc[start:]
        if end:
            df = df.loc[:end]

        return df

    def plot(self, start: Optional[str] = None, end: Optional[str] = None) -> go.Figure:
        """Plots the Dollar Index and rate spread for the given time range with dual Y-axes and dynamic annotations."""
        df = self.to_dataframe(start, end)
        fig = go.Figure()

        # Compute latest values for the legend labels
        latest_dollar = df["Dollar"].iloc[-1]
        latest_spread = df["FF12_FF1"].iloc[-1]

        # Dollar Index (DXY) as a line trace on the primary y-axis
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["Dollar"],
                mode="lines",
                name=f"Dollar Index (DXY) : {latest_dollar:.2f}",
                line=dict(color="black", width=2),
                yaxis="y1",
                hovertemplate="Date: %{x|%Y-%m-%d}<br>Dollar Index: %{y:.2f}<extra></extra>",
            )
        )

        # FF12 - FF1 as a bar trace on the secondary y-axis
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["FF12_FF1"],
                name=f"FF12 - FF1 : {latest_spread:.2f}",
                marker=dict(color="blue", opacity=0.7),
                yaxis="y2",
                hovertemplate="Date: %{x|%Y-%m-%d}<br>Rate Spread: %{y:.2f}<extra></extra>",
            )
        )

        # Determine the dynamic annotation points for rate spread peaks
        peak_tightening = df["FF12_FF1"].idxmax()
        peak_easing = df["FF12_FF1"].idxmin()

        # Annotation for Peak Easing
        fig.add_annotation(
            x=peak_easing,
            y=df.loc[peak_easing, "FF12_FF1"],
            xref="x",
            yref="y2",
            text=f"Peak Easing {df.loc[peak_easing, 'FF12_FF1']:.2f}",
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=20,
            font=dict(color="black", size=12),
            align="center",
        )

        # Annotation for Peak Tightening
        fig.add_annotation(
            x=peak_tightening,
            y=df.loc[peak_tightening, "FF12_FF1"],
            xref="x",
            yref="y2",
            text=f"Peak Tightening {df.loc[peak_tightening, 'FF12_FF1']:.2f}",
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-20,
            font=dict(color="black", size=12),
            align="center",
        )

        # Update layout for dual y-axes and enhanced interactivity
        fig.update_layout(
            xaxis=dict(title="Date"),
            yaxis=dict(title="Dollar Index (DXY)", showgrid=True, zeroline=True),
            yaxis2=dict(
                title="FF12 - FF1 (Rate Spread)",
                overlaying="y",
                side="right",
                showgrid=False,
                zeroline=True,
            ),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5
            ),
            template="plotly_white",
            hovermode="x unified",
            font=dict(family="Roboto", size=12),
            margin=dict(l=60, r=60, t=40, b=40),
        )

        return fig


from typing import Optional
import pandas as pd
import plotly.graph_objects as go
from ix.db.client import get_timeseries


class PMIs_US:
    def __init__(self) -> None:
        # Retrieve the two PMI series.
        self.us_manu = get_timeseries(
            code="NAPMPMI Index",
            field="PX_LAST",
            name="US Manufacturing PMI",
        )
        self.us_serv = get_timeseries(
            code="NAPMNMI Index",
            field="PX_LAST",
            name="US Services PMI",
        )

    def to_dataframe(
        self, start: Optional[str] = None, end: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Combines the PMI time series into a DataFrame.
        Optionally filters the data between start and end dates.
        """
        df = pd.DataFrame(
            {"US Manufacturing PMI": self.us_manu, "US Services PMI": self.us_serv}
        )
        df.dropna(inplace=True)  # Remove any rows with missing data

        # Ensure the index is datetime for proper filtering
        df.index = pd.to_datetime(df.index)

        if start:
            df = df.loc[start:]
        if end:
            df = df.loc[:end]

        return df

    def plot(self, start: Optional[str] = None, end: Optional[str] = None) -> go.Figure:
        """
        Plots the U.S. Manufacturing and Services PMIs as line traces.
        The legend labels are appended with the latest value from each series.
        Dynamic annotations are added to highlight key points:
          - The highest value for each PMI series.
          - A crossover point if the two PMIs are very close.
        A horizontal base line is added at PMI = 50.
        """
        df = self.to_dataframe(start, end)
        fig = go.Figure()

        # Compute the latest values for each series for legend labels
        latest_us_manu = df["US Manufacturing PMI"].iloc[-1]
        latest_us_serv = df["US Services PMI"].iloc[-1]

        # U.S. Manufacturing PMI as a line trace
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["US Manufacturing PMI"],
                mode="lines",
                name=f"US Manufacturing PMI : {latest_us_manu:.2f}",
                line=dict(color="#2ca02c", width=2),
                hovertemplate="Date: %{x|%Y-%m-%d}<br>US Manufacturing PMI: %{y:.2f}<extra></extra>",
            )
        )

        # U.S. Services PMI as a line trace
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["US Services PMI"],
                mode="lines",
                name=f"US Services PMI : {latest_us_serv:.2f}",
                line=dict(color="#d62728", width=2),
                hovertemplate="Date: %{x|%Y-%m-%d}<br>US Services PMI: %{y:.2f}<extra></extra>",
            )
        )

        # --- Dynamic Annotations ---

        # 1. Annotation for the Peak in US Manufacturing PMI
        peak_manu = df["US Manufacturing PMI"].idxmax()
        peak_manu_val = df.loc[peak_manu, "US Manufacturing PMI"]
        fig.add_annotation(
            x=peak_manu,
            y=peak_manu_val,
            xref="x",
            yref="y",
            text=f"High Manufacturing: {peak_manu_val:.2f}",
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=20,
            font=dict(color="#2ca02c", size=12),
            align="center",
        )

        # 2. Annotation for the Peak in US Services PMI
        peak_serv = df["US Services PMI"].idxmax()
        peak_serv_val = df.loc[peak_serv, "US Services PMI"]
        fig.add_annotation(
            x=peak_serv,
            y=peak_serv_val,
            xref="x",
            yref="y",
            text=f"High Services: {peak_serv_val:.2f}",
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=20,
            font=dict(color="#d62728", size=12),
            align="center",
        )

        # --- Add a horizontal base line at PMI = 50 ---
        fig.add_shape(
            type="line",
            x0=df.index.min(),
            x1=df.index.max(),
            y0=50,
            y1=50,
            line=dict(dash="dash", color="blue", width=1),
            xref="x",
            yref="y",
        )

        # Annotate the base line
        fig.add_annotation(
            x=df.index.min(),
            y=50,
            xref="x",
            yref="y",
            text="50 (Base)",
            showarrow=False,
            xanchor="left",
            yanchor="bottom",
            font=dict(color="blue", size=12),
        )

        # Update layout for a clean and interactive chart
        fig.update_layout(
            xaxis=dict(title="Date"),
            yaxis=dict(title="PMI Value", showgrid=True, zeroline=True),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5
            ),
            template="plotly_white",
            hovermode="x unified",
            font=dict(family="Roboto", size=12),
            margin=dict(l=60, r=60, t=40, b=40),
        )

        return fig
