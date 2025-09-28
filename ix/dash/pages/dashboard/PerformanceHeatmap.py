
# import pandas as pd
# from dash import html, dcc, callback, Output, Input, State, clientside_callback
# import dash
# from dash.exceptions import PreventUpdate
# import dash_bootstrap_components as dbc
# import plotly.graph_objects as go
# import traceback
# from datetime import datetime
# from functools import lru_cache

# from ix.db import Universe
# from ix.misc.date import today, oneyearbefore
# from ix.dash.components import Grid, Card
# from ix.misc import get_logger

# logger = get_logger(__name__)

# # --- Cached Data Loader ---
# @lru_cache(maxsize=32)
# def get_cached_universe_data(universe_name: str, start_date: str, end_date: str):
#     try:
#         universe_db = Universe.from_name(universe_name)
#         pxs = universe_db.get_series(field="PX_LAST")
#         return pxs.loc[start_date:end_date]
#     except Exception as e:
#         logger.error(f"Error loading {universe_name}: {e}")
#         return pd.DataFrame()


# # --- Heatmap Generator ---
# def performance_heatmap(pxs: pd.DataFrame, periods: list = [1, 5, 21], title: str = ""):
#     if pxs.empty:
#         fig = go.Figure()
#         fig.add_annotation(
#             text="No data available",
#             xref="paper", yref="paper", x=0.5, y=0.5,
#             showarrow=False, font=dict(size=16, color="#ef4444")
#         )
#         fig.update_layout(
#             title=dict(text=title, x=0.5, xanchor="center", font=dict(size=16, color="#f1f5f9")),
#             paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
#             xaxis=dict(visible=False), yaxis=dict(visible=False),
#             margin=dict(l=0, r=0, t=40, b=0)
#         )
#         return fig

#     performance_data = {}
#     latest_values = pxs.resample("B").last().ffill().iloc[-1]
#     performance_data["Latest"] = latest_values

#     for p in periods:
#         pct = pxs.resample("B").last().ffill().pct_change(p).ffill().iloc[-1]
#         performance_data[f"{p}D"] = pct

#     perf_df = pd.DataFrame(performance_data)
#     perf_matrix = perf_df.copy()
#     for col in perf_df.columns:
#         if col != "Latest":
#             perf_matrix[col] = perf_df[col] * 100

#     z_values = perf_matrix.values.copy()
#     z_colors = perf_matrix.values.copy()
#     z_colors[:, 0] = 0

#     fig = go.Figure(
#         data=go.Heatmap(
#             z=z_colors, x=perf_matrix.columns, y=perf_df.index,
#             colorscale=[
#                 [0, "#374151"], [0.4, "#dc2626"], [0.5, "#374151"],
#                 [0.6, "#059669"], [1, "#059669"]
#             ],
#             zmid=0,
#             text=[[
#                 f"{val:.2f}" if col == "Latest" else f"{val:.1f}%"
#                 for col, val in zip(perf_matrix.columns, row)
#             ] for row in z_values],
#             texttemplate="%{text}", textfont=dict(size=14, color="white"),
#             hovertemplate="<b>%{y}</b><br>%{x}: %{text}<extra></extra>",
#             showscale=False
#         )
#     )

#     nrows, ncols = perf_matrix.shape
#     for i in range(nrows):
#         for j in range(ncols):
#             fig.add_shape(
#                 type="rect", x0=j-0.5, x1=j+0.5, y0=i-0.5, y1=i+0.5,
#                 line=dict(color="white", width=1), layer="above"
#             )

#     fig.update_layout(
#         title=dict(text=title, x=0.5, xanchor="center", font=dict(size=16, color="#f1f5f9")),
#         paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
#         xaxis=dict(tickfont=dict(size=13, color="#f1f5f9"), side="top", showgrid=False),
#         yaxis=dict(tickfont=dict(size=13, color="#f1f5f9"), autorange="reversed", showgrid=False),
#         margin=dict(l=0, r=0, t=40, b=0)
#     )
#     return fig


# # --- Section Builder ---
# def Section(universes=["Major Indices", "Global Markets", "Sectors", "Themes", "Commodities", "Currencies"],
#             periods=[1, 5, 21, 63, 126, 252]):
#     start_date = oneyearbefore().strftime("%Y-%m-%d")
#     end_date = today().strftime("%Y-%m-%d")
#     heatmap_cards = []

#     for universe in universes:
#         try:
#             pxs = get_cached_universe_data(universe, start_date, end_date)
#             if not pxs.empty:
#                 fig = performance_heatmap(pxs, periods, title=universe)
#                 heatmap_cards.append(Card([dcc.Graph(figure=fig, config={"displayModeBar": False},
#                                                     style={"width": "100%", "height": "400px"})]))
#             else:
#                 heatmap_cards.append(Card([html.H4(universe, style={"color": "#f1f5f9"}),
#                                            html.Div("No data available", style={"color": "#ef4444"})]))
#         except Exception as e:
#             logger.error(f"Error creating heatmap for {universe}: {e}")
#             heatmap_cards.append(Card([html.H4(universe, style={"color": "#f1f5f9"}),
#                                        html.Div(f"Error: {str(e)}", style={"color": "#ef4444"})]))

#     return html.Div([html.Section([html.Div([html.H3("Performance Heatmaps", style={"color": "#f1f5f9"}),
#                                              Grid(heatmap_cards)])])])


# # --- Page Registration ---
# dash.register_page(__name__, path="/", title="Dashboard", name="Dashboard")

# # --- Layout ---
# layout = html.Div([
#     dcc.Store(id="dashboard-load-state", data={"loaded": False}),
#     dcc.Store(id="last-refresh-time", data=None),
#     dcc.Interval(id="dashboard-refresh-interval", interval=10*60*1000, n_intervals=0),
#     dcc.Interval(id="dashboard-initial-load", interval=100, n_intervals=0, max_intervals=1),
#     html.Div([html.Div([html.H1("Investment Dashboard", style={"color": "#f1f5f9"}),
#                         html.P("Real-time market performance and analytics", style={"color": "#94a3b8"})], style={"flex": "1"}),
#               html.Div([html.Div(id="last-update-display", style={"color": "#64748b"}),
#                         html.Button([html.I(className="fas fa-sync-alt"), "Refresh Now"],
#                                     id="manual-refresh-btn", n_clicks=0,
#                                     style={"background": "#059669", "color": "white"})])],
#              style={"display": "flex", "justifyContent": "space-between"}),
#     html.Div([html.Div(id="heatmap-section", children=Section())])
# ])


# # --- Callbacks ---
# @callback(Output("heatmap-section", "children"),
#           [Input("dashboard-initial-load", "n_intervals"),
#            Input("dashboard-refresh-interval", "n_intervals"),
#            Input("manual-refresh-btn", "n_clicks")],
#           State("dashboard-load-state", "data"),
#           prevent_initial_call=False)
# def load_heatmap_section(initial_load, refresh_intervals, manual_refresh, load_state):
#     try:
#         logger.info("Loading heatmap section")
#         return Section()
#     except Exception as e:
#         error_trace = traceback.format_exc()
#         logger.error(f"Error loading heatmaps: {error_trace}")
#         return html.Div(["Error loading heatmaps"])


# @callback(Output("last-update-display", "children"),
#           [Input("dashboard-initial-load", "n_intervals"),
#            Input("dashboard-refresh-interval", "n_intervals"),
#            Input("manual-refresh-btn", "n_clicks")],
#           prevent_initial_call=True)
# def update_last_refresh_time(initial_load, refresh_intervals, manual_refresh):
#     return f"Last updated: {datetime.now().strftime('%H:%M:%S')}"


# # --- Clientside hover effects ---
# clientside_callback(
#     """
#     function() {
#         return window.dash_clientside.no_update;
#     }
#     """,
#     Output("dashboard-load-state", "data"),
#     Input("dashboard-load-state", "data")
# )
