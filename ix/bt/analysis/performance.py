from cachetools import TTLCache, cached
import ix
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

cache = TTLCache(maxsize=128, ttl=300)

@cached(cache)
def get_perforamnces(universe: str = "LocalIndices", period: str = "1D") -> pd.Series:
    """
    Retrieve performance data for a given universe.
    """
    universe_obj = ix.db.Universe.find_one({"code": universe}).run()
    if not universe_obj:
        raise ValueError(f"Universe {universe} not found.")
    performance = {}
    for asset in universe_obj.assets:
        metadata = ix.db.Metadata.find_one({"code": asset.code}).run()
        if metadata is None:
            continue
        performance[asset.name] = metadata.tp(field=f"PCT_CHG_{period}").data
    return pd.Series(performance)


class Performance:
    """
    Class to load performance data and create performance plots.
    """

    @classmethod
    def from_universe(cls, universe: str, period: str = "1D") -> "Performance":
        performance = get_perforamnces(universe=universe, period=period)
        return cls(performance=performance)

    def __init__(self, performance: pd.Series):
        self.performance = performance

    def plot(self) -> go.Figure:
        performance = self.performance.sort_values()
        abs_value = performance.abs()
        # Use a gradient color scale for positive and negative values
        col_value = performance.apply(
            lambda x: (
                px.colors.sequential.Blues[-2]
                if x >= 0
                else px.colors.sequential.Reds[-2]
            )
        )
        padded_names = performance.index.to_series().apply(lambda x: x + "\u00A0" * 5)
        hover_text = [
            f"<b>{asset}</b> : {perf:.2f}%" for asset, perf in performance.items()
        ]

        fig = go.Figure(
            data=[
                go.Bar(
                    x=abs_value,  # Bar lengths based on absolute values.
                    y=padded_names,  # Padded asset names.
                    orientation="h",  # Horizontal bar chart.
                    marker_color=col_value,  # Colors based on performance.
                    text=performance,  # Display the original performance values.
                    texttemplate="%{text:.2f}%",
                    textposition="auto",
                    hovertext=hover_text,
                    hoverinfo="text",
                    marker_line_width=1,
                    marker_line_color="gray",
                )
            ]
        )

        # Update layout for a dark theme and remove the title.
        fig.update_layout(
            xaxis=dict(visible=False, showticklabels=False, title=""),
            yaxis=dict(
                tickfont=dict(size=12, family="Arial", color="white"),
                automargin=True,
            ),
            margin=dict(l=25, r=25, t=25, b=25),
            template="plotly_dark",
            showlegend=False,
            hoverlabel=dict(
                bgcolor="black", font_size=12, font_family="Arial", namelength=-1
            ),
            title=None,
        )
        return fig
