# import pandas as pd
# from dash import html, dcc
# import dash_bootstrap_components as dbc
# import plotly.graph_objects as go
# from ix.db import Universe
# from ix.core import rebase
# from ix.misc.date import today, oneyearbefore
# from ix.dash.components import ChartGrid
# from functools import lru_cache

# def CardwithHeader(title: str, children):
#     return dbc.Card(
#         [
#             dbc.CardHeader(
#                 html.H4(
#                     title,
#                     className="mb-0",
#                     style={
#                         "color": "#f1f5f9",
#                         "fontSize": "1.1rem",
#                         "fontWeight": "600",
#                         "lineHeight": "1.2",
#                     },
#                 ),
#                 style={
#                     "background": "rgba(51, 65, 85, 0.9)",
#                     "borderBottom": "1px solid rgba(148, 163, 184, 0.3)",
#                     "padding": "0.35rem 0.75rem",
#                     "minHeight": "unset",
#                     "height": "2.2rem",
#                     "display": "flex",
#                     "alignItems": "center",
#                 },
#             ),
#             dbc.CardBody(
#                 children=children,
#                 style={
#                     "padding": "0.5rem",
#                     "background": "rgba(30, 41, 59, 0.9)",
#                 },
#             ),
#         ],
#         style={
#             "background": "rgba(30, 41, 59, 0.9)",
#             "border": "1px solid rgba(148, 163, 184, 0.3)",
#             "borderRadius": "12px",
#             "boxShadow": "0 4px 12px rgba(0, 0, 0, 0.3)",
#             "transition": "all 0.3s ease",
#             "overflow": "hidden",
#             "marginBottom": "1rem",
#         },
#         className="h-100",
#     )

# @lru_cache(maxsize=32)
# def get_cached_universe_data(universe_name: str, start_date: str, end_date: str):
#     """Cache universe data to avoid repeated database calls"""
#     try:
#         universe_db = Universe.from_name(universe_name)
#         pxs = universe_db.get_series(field="PX_LAST")
#         return pxs.loc[start_date:end_date]
#     except Exception as e:
#         print(f"Error loading {universe_name}: {e}")
#         return pd.DataFrame()

# def create_performance_chart(pxs: pd.DataFrame) -> go.Figure:
#     """Create performance chart with error handling"""

#     if pxs.empty:
#         # Return empty chart
#         fig = go.Figure()
#         fig.add_annotation(
#             text="No data available",
#             xref="paper",
#             yref="paper",
#             x=0.5,
#             y=0.5,
#             showarrow=False,
#             font=dict(size=16, color="#ef4444"),
#         )
#         fig.update_layout(
#             paper_bgcolor="rgba(0,0,0,0)",
#             plot_bgcolor="rgba(0,0,0,0)",
#             xaxis=dict(visible=False),
#             yaxis=dict(visible=False),
#             margin=dict(l=0, r=0, t=0, b=0),
#         )
#         return fig

#     fig = go.Figure()

#     try:
#         for i, (name, series) in enumerate(pxs.items()):
#             if series.dropna().empty:
#                 continue

#             d = rebase(series.dropna()).sub(1)
#             if d.empty:
#                 continue

#             latest_value = float(d.iloc[-1])

#             fig.add_trace(
#                 go.Scatter(
#                     x=d.index,
#                     y=d.values,
#                     name=f"{name} : ({latest_value:.2%})",
#                     line=dict(
#                         width=2,
#                         shape="spline",
#                     ),
#                     hovertemplate=f"<b>{name}</b> : %{{y:.2%}} %<extra></extra>",
#                 )
#             )
#     except Exception as e:
#         print(f"Error creating performance chart: {e}")
#         # Return error chart
#         fig = go.Figure()
#         fig.add_annotation(
#             text=f"Error: {str(e)[:50]}...",
#             xref="paper",
#             yref="paper",
#             x=0.5,
#             y=0.5,
#             showarrow=False,
#             font=dict(size=16, color="#ef4444"),
#         )
#         fig.update_layout(
#             paper_bgcolor="rgba(0,0,0,0)",
#             plot_bgcolor="rgba(0,0,0,0)",
#             xaxis=dict(visible=False),
#             yaxis=dict(visible=False),
#             margin=dict(l=0, r=0, t=0, b=0),
#         )
#         return fig

#     if not fig.data:
#         # No data traces added
#         fig.add_annotation(
#             text="No valid data available",
#             xref="paper",
#             yref="paper",
#             x=0.5,
#             y=0.5,
#             showarrow=False,
#             font=dict(size=16, color="#ef4444"),
#         )
#         fig.update_layout(
#             paper_bgcolor="rgba(0,0,0,0)",
#             plot_bgcolor="rgba(0,0,0,0)",
#             xaxis=dict(visible=False),
#             yaxis=dict(visible=False),
#             margin=dict(l=0, r=0, t=0, b=0),
#         )
#         return fig

#     fig.update_layout(
#         xaxis=dict(
#             title="Date",
#             title_font=dict(size=12, color="#94a3b8", family="Inter"),
#             tickfont=dict(size=11, color="#64748b"),
#             gridcolor="rgba(148, 163, 184, 0.2)",
#             gridwidth=1,
#         ),
#         yaxis=dict(
#             title="Performance",
#             title_font=dict(size=12, color="#94a3b8", family="Inter"),
#             tickfont=dict(size=11, color="#64748b"),
#             gridcolor="rgba(148, 163, 184, 0.2)",
#             gridwidth=1,
#             tickformat=".0%",
#         ),
#         paper_bgcolor="rgba(0,0,0,0)",
#         plot_bgcolor="rgba(0,0,0,0)",
#         legend=dict(
#             orientation="h",
#             yanchor="bottom",
#             y=1.02,
#             xanchor="center",
#             x=0.5,
#             bgcolor="rgba(30, 41, 59, 0.9)",
#             bordercolor="rgba(148, 163, 184, 0.3)",
#             font=dict(size=10, color="#f1f5f9", family="Inter"),
#             borderwidth=0,
#             valign="middle",
#             xref="paper",
#             yref="paper",
#             itemsizing="trace",
#             title_text='',
#             traceorder="normal",
#         ),
#         margin=dict(l=50, r=50, t=50, b=50),
#         font=dict(family="Inter", color="#f1f5f9"),
#         hovermode="x unified",
#         hoverlabel=dict(
#             bgcolor="rgba(30, 41, 59, 0.95)",
#             bordercolor="rgba(148, 163, 184, 0.3)",
#             font=dict(color="#f1f5f9", family="Inter", size=11),
#         ),
#     )
#     return fig

# def Section(
#     universes: list[str] = [
#         "Major Indices",
#         "Global Markets",
#         "Sectors",
#         "Themes",
#         "Commodities",
#         "Currencies",
#     ],
#     periods: list[int] = [1, 5, 21, 63, 126, 252],
# ):
#     """Optimized section with caching and error handling"""

#     # Get date range once
#     start_date = oneyearbefore().strftime('%Y-%m-%d')
#     end_date = today().strftime('%Y-%m-%d')

#     # Collect all performance charts with caching
#     chart_cards = []

#     for universe in universes:
#         try:
#             # Use cached data
#             pxs = get_cached_universe_data(universe, start_date, end_date)

#             if not pxs.empty:
#                 chart_cards.append(
#                     CardwithHeader(
#                         title=universe,
#                         children=dcc.Graph(
#                             figure=create_performance_chart(pxs),
#                             config={
#                                 "displayModeBar": False,
#                                 "responsive": True,
#                                 "autosizable": True,
#                             },
#                             style={
#                                 "width": "100%",
#                                 "height": "400px",
#                                 "minHeight": "300px",
#                                 "maxHeight": "500px",
#                                 "minWidth": "400px",
#                             },
#                         ),
#                     )
#                 )
#             else:
#                 # Create error card
#                 chart_cards.append(
#                     CardwithHeader(
#                         title=universe,
#                         children=html.Div(
#                             "No data available",
#                             style={
#                                 "color": "#ef4444",
#                                 "textAlign": "center",
#                                 "padding": "2rem",
#                                 "fontSize": "1.1rem"
#                             }
#                         ),
#                     )
#                 )

#         except Exception as e:
#             print(f"Error creating performance chart for {universe}: {e}")
#             # Create error card
#             chart_cards.append(
#                 CardwithHeader(
#                     title=universe,
#                     children=html.Div(
#                         f"Error: {str(e)[:50]}...",
#                         style={
#                             "color": "#ef4444",
#                             "textAlign": "center",
#                             "padding": "2rem",
#                             "fontSize": "1.1rem"
#                         }
#                     ),
#                 )
#             )

#     return html.Div(
#         [
#             html.Section(
#                 [
#                     # Performance charts section
#                     html.Div(
#                         [
#                             html.H3(
#                                 "Market Performance",
#                                 style={
#                                     "fontSize": "1.3rem",
#                                     "fontWeight": "600",
#                                     "color": "#f1f5f9",
#                                     "marginTop": "1.5rem",
#                                     "marginBottom": "1rem",
#                                     "paddingBottom": "0.5rem",
#                                     "borderBottom": "2px solid #3b82f6",
#                                 },
#                             ),
#                             ChartGrid(chart_cards) if chart_cards else html.Div(
#                                 "Loading performance charts...",
#                                 style={
#                                     "color": "#94a3b8",
#                                     "textAlign": "center",
#                                     "padding": "2rem",
#                                     "fontSize": "1.1rem"
#                                 }
#                             ),
#                         ]
#                     ),
#                 ],
#                 style={"padding": "1rem 0"},
#             ),
#         ]
#     )
