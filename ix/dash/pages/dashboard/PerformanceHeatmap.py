import pandas as pd
from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from ix.db import Universe
from ix.misc.date import today, oneyearbefore
from ix.dash.components import ChartGrid
import time
from functools import lru_cache

def CardwithHeader(title: str, children):
    return dbc.Card(
        [
            dbc.CardHeader(
                html.H4(
                    title,
                    className="mb-0",
                    style={
                        "color": "#f1f5f9",
                        "fontSize": "1.1rem",
                        "fontWeight": "600",
                        "lineHeight": "1.2",
                    },
                ),
                style={
                    "background": "rgba(51, 65, 85, 0.9)",
                    "borderBottom": "1px solid rgba(148, 163, 184, 0.3)",
                    "padding": "0.35rem 0.75rem",
                    "minHeight": "unset",
                    "height": "2.2rem",
                    "display": "flex",
                    "alignItems": "center",
                },
            ),
            dbc.CardBody(
                children=children,
                style={
                    "padding": "0.5rem",
                    "background": "rgba(30, 41, 59, 0.9)",
                },
            ),
        ],
        style={
            "background": "rgba(30, 41, 59, 0.9)",
            "border": "1px solid rgba(148, 163, 184, 0.3)",
            "borderRadius": "12px",
            "boxShadow": "0 4px 12px rgba(0, 0, 0, 0.3)",
            "transition": "all 0.3s ease",
            "overflow": "hidden",
            "marginBottom": "1rem",
        },
        className="h-100",
    )

@lru_cache(maxsize=32)
def get_cached_universe_data(universe_name: str, start_date: str, end_date: str):
    """Cache universe data to avoid repeated database calls"""
    try:
        universe_db = Universe.from_name(universe_name)
        pxs = universe_db.get_series(field="PX_LAST")
        return pxs.loc[start_date:end_date]
    except Exception as e:
        print(f"Error loading {universe_name}: {e}")
        return pd.DataFrame()

def performance_heatmap(pxs: pd.DataFrame, periods: list = [1, 5, 21]):
    """Create a heatmap showing performance across different time periods"""
    if pxs.empty:
        # Return empty chart
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#ef4444"),
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=0, r=0, t=0, b=0),
        )
        return fig

    performance_data = {}

    # Add latest values as the first column
    latest_values = pxs.resample("B").last().ffill().iloc[-1]
    performance_data["Latest"] = latest_values

    # Add performance data for each period
    for p in periods:
        pct = pxs.resample("B").last().ffill().pct_change(p).ffill().iloc[-1]
        performance_data[f"{p}D"] = pct

    perf_df = pd.DataFrame(performance_data)

    # Create the matrix for the heatmap
    perf_matrix = perf_df.copy()
    for col in perf_df.columns:
        if col != "Latest":
            perf_matrix[col] = perf_df[col] * 100

    # Create custom colorscale matrix
    z_values = perf_matrix.values.copy()
    z_colors = perf_matrix.values.copy()
    z_colors[:, 0] = 0  # First column is Latest

    fig = go.Figure(
        data=go.Heatmap(
            z=z_colors,
            x=perf_matrix.columns,
            y=perf_df.index,
            colorscale=[
                [0, "#374151"],  # Dark gray for Latest column and zero
                [0.4, "#dc2626"],  # Red for negative
                [0.5, "#374151"],  # Dark gray for zero
                [0.6, "#059669"],  # Green for positive
                [1, "#059669"],
            ],
            zmid=0,
            text=[[f"{val:.2f}" if col == "Latest" else f"{val:.1f}%"
                   for col, val in zip(perf_matrix.columns, row)]
                  for row in z_values],
            texttemplate="%{text}",
            textfont={
                "size": 14,
                "color": "white",
                "family": "Inter",
            },
            hovertemplate="<b>%{y}</b><br>%{x}: %{text}<extra></extra>",
            showscale=False,
        )
    )

    # Add visible borders
    nrows, ncols = perf_matrix.shape
    for i in range(nrows):
        for j in range(ncols):
            fig.add_shape(
                type="rect",
                x0=j - 0.5,
                x1=j + 0.5,
                y0=i - 0.5,
                y1=i + 0.5,
                line=dict(color="white", width=1),
                layer="above",
            )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            title_font=dict(size=12, color="#94a3b8", family="Inter"),
            tickfont=dict(size=13, color="#f1f5f9"),
            side="top",
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(
            tickfont=dict(size=13, color="#f1f5f9"),
            autorange="reversed",
            ticklabelposition="outside left",
            automargin=True,
            showgrid=False,
            zeroline=False,
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        font=dict(family="Inter", color="#f1f5f9"),
        showlegend=False,
    )

    return fig

def Section(
    universes: list[str] = [
        "Major Indices",
        "Global Markets", 
        "Sectors",
        "Themes",
        "Commodities",
        "Currencies",
    ],
    periods: list[int] = [1, 5, 21, 63, 126, 252],
):
    """Optimized section with caching and error handling"""
    
    # Get date range once
    start_date = oneyearbefore().strftime('%Y-%m-%d')
    end_date = today().strftime('%Y-%m-%d')
    
    # Collect all heatmaps with caching
    heatmap_cards = []
    
    for universe in universes:
        try:
            # Use cached data
            pxs = get_cached_universe_data(universe, start_date, end_date)
            
            if not pxs.empty:
                heatmap_fig = performance_heatmap(pxs, periods)
                
                heatmap_cards.append(
                    CardwithHeader(
                        title=universe,
                        children=dcc.Graph(
                            figure=heatmap_fig,
                            config={
                                "displayModeBar": False,
                                "responsive": True,
                                "autosizable": True,
                            },
                            style={
                                "width": "100%",
                                "height": "400px",
                                "minHeight": "300px",
                                "maxHeight": "500px",
                                "minWidth": "400px",
                            },
                        ),
                    )
                )
            else:
                # Create error card
                heatmap_cards.append(
                    CardwithHeader(
                        title=universe,
                        children=html.Div(
                            "No data available",
                            style={
                                "color": "#ef4444",
                                "textAlign": "center",
                                "padding": "2rem",
                                "fontSize": "1.1rem"
                            }
                        ),
                    )
                )
                
        except Exception as e:
            print(f"Error creating heatmap for {universe}: {e}")
            # Create error card
            heatmap_cards.append(
                CardwithHeader(
                    title=universe,
                    children=html.Div(
                        f"Error: {str(e)[:50]}...",
                        style={
                            "color": "#ef4444",
                            "textAlign": "center",
                            "padding": "2rem",
                            "fontSize": "1.1rem"
                        }
                    ),
                )
            )

    return html.Div(
        [
            html.Section(
                [
                    html.Div(
                        [
                            html.H3(
                                "Performance Heatmaps",
                                style={
                                    "fontSize": "1.3rem",
                                    "fontWeight": "600",
                                    "color": "#f1f5f9",
                                    "marginTop": "1.5rem",
                                    "marginBottom": "1rem",
                                    "paddingBottom": "0.5rem",
                                    "borderBottom": "2px solid #3b82f6",
                                },
                            ),
                            ChartGrid(heatmap_cards) if heatmap_cards else html.Div(
                                "Loading heatmaps...",
                                style={
                                    "color": "#94a3b8",
                                    "textAlign": "center",
                                    "padding": "2rem",
                                    "fontSize": "1.1rem"
                                }
                            ),
                        ]
                    ),
                ],
                style={"padding": "1rem 0"},
            ),
        ]
    )
