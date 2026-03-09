import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


def performance_fig(performance: pd.Series) -> go.Figure:
    performance = performance.sort_values()
    abs_value = performance.abs()

    # Use a gradient color scale for positive and negative values.
    col_value = performance.apply(
        lambda x: (
            px.colors.sequential.Blues[-2] if x >= 0 else px.colors.sequential.Reds[-2]
        )
    )

    # Optionally, you can remove extra padding if not needed.
    padded_names = performance.index.to_series().apply(lambda x: x + "\u00A0" * 5)
    hover_text = [
        f"<b>{asset}</b> : {perf:.2f}%" for asset, perf in performance.items()
    ]

    fig = go.Figure(
        data=[
            go.Bar(
                x=abs_value,
                y=padded_names,
                orientation="h",
                marker_color=col_value,
                text=performance,
                texttemplate="%{text:.2f}%",
                textposition="auto",
                # Set uniform font size for text labels inside the bars.
                textfont=dict(size=12, color="white"),
                hovertext=hover_text,
                hoverinfo="text",
                marker_line_width=1,
                marker_line_color="gray",
            )
        ]
    )

    # Update layout to ensure y-axis labels are fully visible
    # and to use a uniform font for both tick labels and bar texts.
    fig.update_layout(
        xaxis=dict(visible=False, showticklabels=False, title=""),
        yaxis=dict(
            tickfont=dict(size=12, family="Arial", color="white"),
            automargin=True,
        ),
        # Increased left margin for y-axis label visibility.
        margin=dict(l=25, r=25, t=25, b=25),
        template="plotly_dark",
        showlegend=False,
        hoverlabel=dict(
            bgcolor="black", font_size=12, namelength=-1
        ),
        title=None,
    )
    return fig
