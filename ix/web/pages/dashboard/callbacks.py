"""
Callbacks module for dashboard.
Handles dashboard callbacks and event handlers.
"""

import pandas as pd
import traceback
import json
import plotly.graph_objects as go
from datetime import datetime
import dash
from dash import callback, Output, Input, State, clientside_callback, dcc, html
from dash.exceptions import PreventUpdate
from dash import callback_context

from ix.misc import get_logger
from ix.web.pages.dashboard.data_manager import DataManager, BackgroundRefreshManager
from ix.web.pages.dashboard.visualizations import HeatmapGenerator
from ix.web.pages.dashboard.ui_components import (
    SkeletonLoader,
    ErrorDisplay,
    LayoutHelpers,
    ModernComponents,
)
from ix.web.components import Grid, Card

logger = get_logger(__name__)


class DashboardCallbacks:
    """Manages all dashboard callbacks and event handlers."""

    _callbacks_registered = False

    @staticmethod
    def register_callbacks():
        """Register all dashboard callbacks."""
        if DashboardCallbacks._callbacks_registered:
            return
        DashboardCallbacks._callbacks_registered = True

        # Global data refresh callback
        @callback(
            Output("global-data", "data"),
            Input("global-data-refresh-interval", "n_intervals"),
            prevent_initial_call=False,
            allow_duplicate=True,
        )
        def refresh_global_data(n_intervals):
            """Refresh global dashboard data - now uses cached data and background refresh."""
            try:
                logger.info(f"Global data callback fired: interval {n_intervals}")
                logger.info(
                    f"Refreshing global dashboard data (interval: {n_intervals})"
                )

                # Start background refresh on first load
                if n_intervals == 0:
                    BackgroundRefreshManager.start_background_refresh()

                # Get cached data (will be refreshed by background worker)
                cache_key = "dashboard_data"
                dashboard_data = DataManager.get_cached_data(cache_key)

                if dashboard_data is None:
                    # If no cached data, load it synchronously (first time only)
                    logger.info("No cached data found, loading synchronously...")
                    dashboard_data = DataManager.refresh_global_dashboard_data()

                # Ensure all data is JSON serializable
                def convert_arrays_to_lists(obj):
                    if isinstance(obj, dict):
                        return {k: convert_arrays_to_lists(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_arrays_to_lists(item) for item in obj]
                    elif hasattr(obj, "tolist"):  # numpy array
                        return obj.tolist()
                    else:
                        return obj

                try:
                    # Convert any numpy arrays to lists before JSON serialization
                    dashboard_data = convert_arrays_to_lists(dashboard_data)
                    json.dumps(dashboard_data)
                except (TypeError, ValueError) as e:
                    logger.error(f"Data not JSON serializable: {e}")
                    return {
                        "error": f"Data serialization error: {str(e)}",
                        "last_updated": datetime.now().isoformat(),
                    }

                return dashboard_data
            except Exception as e:
                logger.error(f"Error refreshing global data: {e}")
                logger.error(f"Full traceback: {traceback.format_exc()}")
                return {"error": str(e), "last_updated": datetime.now().isoformat()}

        # Tab click callback
        @callback(
            Output("active-tab", "data"),
            Input({"type": "tab-button", "index": dash.ALL}, "n_clicks"),
            State({"type": "tab-button", "index": dash.ALL}, "id"),
            prevent_initial_call=True,
        )
        def handle_tab_click(n_clicks, tab_ids):
            """Handle tab button clicks."""
            ctx = callback_context
            if not ctx.triggered:
                raise PreventUpdate

            # Find which tab was clicked
            button_id = ctx.triggered[0]["prop_id"].split(".")[0]
            if button_id:
                import json

                tab_data = json.loads(button_id)
                return tab_data["index"]

            return "all"

        # Tab styling update callback
        @callback(
            Output("dashboard-tabs", "children"),
            Input("active-tab", "data"),
            prevent_initial_call=False,
            allow_duplicate=True,
        )
        def update_tab_styling(active_tab):
            """Update tab styling based on active tab."""
            return ModernComponents.create_tabs(
                [
                    {"id": "all", "label": "All Markets", "icon": "mdi:view-grid"},
                    {"id": "indices", "label": "Indices", "icon": "mdi:chart-line"},
                    {"id": "sectors", "label": "Sectors", "icon": "mdi:domain"},
                    {"id": "commodities", "label": "Commodities", "icon": "mdi:gold"},
                ],
                active_tab=active_tab,
            )

        # Heatmap section loading callback with tab filtering
        @callback(
            Output("heatmap-section", "children"),
            Output("dashboard-load-state", "data"),
            [
                Input("global-data", "data"),
                Input("manual-refresh-btn", "n_clicks"),
                Input("active-tab", "data"),
            ],
            State("dashboard-load-state", "data"),
            prevent_initial_call=False,
            allow_duplicate=True,
        )
        def load_heatmap_section(global_data, manual_refresh, active_tab, load_state):
            """Load the heatmap section with lazy loading for individual charts and tab filtering."""

            try:
                logger.info(
                    f"Loading heatmap section from global data (tab: {active_tab})"
                )

                if global_data is None or "error" in global_data:
                    # Show skeleton while waiting for data
                    return SkeletonLoader.create_section_skeleton(
                        "Performance Heatmaps",
                        "Loading market data...",
                    ), {"loaded": False}

                # Define all universes
                all_universes = [
                    "Major Indices",
                    "Global Markets",
                    "Sectors",
                    "Themes",
                    "Commodities",
                    "Currencies",
                ]

                # Filter based on active tab
                if active_tab == "indices":
                    universes = ["Major Indices", "Global Markets"]
                elif active_tab == "sectors":
                    universes = ["Sectors", "Themes"]
                elif active_tab == "commodities":
                    universes = ["Commodities", "Currencies"]
                else:  # "all"
                    universes = all_universes

                # Create chart cards with lazy loading containers
                chart_cards = []
                from ix.web.components import Grid, Card

                for i, universe in enumerate(all_universes):
                    if universe not in universes:
                        continue

                    # Create individual chart containers that will load lazily
                    chart_content = html.Div(
                        id=f"chart-container-{i}",
                        children=SkeletonLoader.create_chart_skeleton(
                            f"Loading {universe}..."
                        ),
                    )
                    chart_cards.append(Card(chart_content))

                # Display message if no data for selected tab
                if not chart_cards:
                    return html.Div(
                        "No data available for this filter",
                        style={
                            "textAlign": "center",
                            "padding": "3rem",
                            "color": "#94a3b8",
                            "fontSize": "1.1rem",
                        },
                    ), {"loaded": True}

                heatmap_content = html.Div(
                    [
                        LayoutHelpers.create_section_header("Performance Heatmaps"),
                        Grid(chart_cards),
                    ]
                )

                return heatmap_content, {"loaded": True}

            except Exception as e:
                error_trace = traceback.format_exc()
                logger.error(f"Error loading heatmap section: {error_trace}")

                return (
                    ErrorDisplay.create_error_section(
                        "Performance Heatmaps",
                        f"Error: {str(e)}\n\nFull traceback:\n{error_trace}",
                        "heatmap",
                    ),
                    {"loaded": False, "error": True},
                )

        # Individual chart loading callbacks for lazy loading with progressive loading
        universes = [
            "Major Indices",
            "Global Markets",
            "Sectors",
            "Themes",
            "Commodities",
            "Currencies",
        ]

        # Register callbacks without delays for maximum speed
        for i, universe in enumerate(universes):
            DashboardCallbacks._register_individual_chart_callback(i, universe)

        # Last refresh time display callback
        @callback(
            Output("last-update-display", "children"),
            [
                Input("global-data-refresh-interval", "n_intervals"),
                Input("manual-refresh-btn", "n_clicks"),
            ],
            prevent_initial_call=True,
            allow_duplicate=True,
        )
        def update_last_refresh_time_dashboard(*args):
            """Update the last refresh time display."""
            from dash_iconify import DashIconify

            ctx = callback_context
            if not ctx.triggered:
                raise PreventUpdate

            current_time = datetime.now().strftime("%H:%M:%S")
            return [
                DashIconify(
                    icon="mdi:clock-outline",
                    width=16,
                    style={
                        "marginRight": "0.5rem",
                        "color": "#64748b",
                    },
                ),
                html.Span(f"Last updated: {current_time}"),
            ]

        # Summary stats callback
        @callback(
            Output("summary-stats-section", "children"),
            Input("global-data", "data"),
            prevent_initial_call=False,
            allow_duplicate=True,
        )
        def update_summary_stats(global_data):
            """Update summary statistics cards."""
            try:
                if global_data is None or "error" in global_data:
                    # Show loading skeletons
                    return html.Div(
                        [
                            SkeletonLoader.create_chart_skeleton("Loading..."),
                            SkeletonLoader.create_chart_skeleton("Loading..."),
                            SkeletonLoader.create_chart_skeleton("Loading..."),
                            SkeletonLoader.create_chart_skeleton("Loading..."),
                        ],
                        style={
                            "display": "grid",
                            "gridTemplateColumns": "repeat(auto-fit, minmax(250px, 1fr))",
                            "gap": "1.5rem",
                            "marginBottom": "2.5rem",
                        },
                    )

                # Calculate summary statistics
                total_markets = 0
                gainers = 0
                losers = 0
                avg_change = 0
                changes = []

                universes = [
                    "Major Indices",
                    "Global Markets",
                    "Sectors",
                    "Themes",
                    "Commodities",
                    "Currencies",
                ]

                for universe in universes:
                    if universe in global_data:
                        universe_data = global_data[universe]
                        if universe_data.get("data_available", False):
                            perf_matrix = universe_data.get("performance_matrix", {})
                            if "1D" in perf_matrix:
                                day_changes = perf_matrix["1D"]
                                total_markets += len(day_changes)
                                for change in day_changes.values():
                                    if change > 0:
                                        gainers += 1
                                    elif change < 0:
                                        losers += 1
                                    changes.append(change)

                if changes:
                    avg_change = sum(changes) / len(changes)

                # Create stat cards
                stat_cards = html.Div(
                    [
                        ModernComponents.create_stat_card(
                            "Total Markets",
                            str(total_markets),
                            None,
                            "mdi:chart-multiple",
                            "neutral",
                        ),
                        ModernComponents.create_stat_card(
                            "Gainers",
                            str(gainers),
                            (
                                f"{(gainers/total_markets*100):.1f}%"
                                if total_markets > 0
                                else "0%"
                            ),
                            "mdi:trending-up",
                            "up",
                        ),
                        ModernComponents.create_stat_card(
                            "Losers",
                            str(losers),
                            (
                                f"{(losers/total_markets*100):.1f}%"
                                if total_markets > 0
                                else "0%"
                            ),
                            "mdi:trending-down",
                            "down",
                        ),
                        ModernComponents.create_stat_card(
                            "Avg Change",
                            f"{avg_change*100:+.2f}%",
                            "1D Performance",
                            "mdi:chart-timeline-variant",
                            "up" if avg_change > 0 else "down",
                        ),
                    ],
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "repeat(auto-fit, minmax(250px, 1fr))",
                        "gap": "1.5rem",
                        "marginBottom": "2.5rem",
                    },
                )

                return stat_cards

            except Exception as e:
                logger.error(f"Error updating summary stats: {e}")
                return html.Div(
                    "Error loading summary statistics",
                    style={
                        "color": "#ef4444",
                        "textAlign": "center",
                        "padding": "2rem",
                    },
                )

        # Consolidated figure cache callback with pre-loading status
        @callback(
            [Output("figure-cache", "data"), Output("preload-status", "data")],
            Input("global-data", "data"),
            prevent_initial_call=False,
            allow_duplicate=True,
        )
        def update_figure_cache(global_data):
            """Update consolidated figure cache with all charts and track pre-loading status."""
            try:
                if global_data is None or "error" in global_data:
                    return {}, {"charts_ready": False, "charts_loaded": 0}

                figure_cache = {}
                charts_loaded = 0
                universes = [
                    "Major Indices",
                    "Global Markets",
                    "Sectors",
                    "Themes",
                    "Commodities",
                    "Currencies",
                ]

                for universe in universes:
                    if universe in global_data:
                        universe_data = global_data[universe]

                        if universe_data.get("data_available", False):
                            # Use pre-generated figure if available
                            if (
                                "figure" in universe_data
                                and universe_data["figure"] is not None
                            ):
                                figure_cache[universe] = universe_data["figure"]
                                charts_loaded += 1
                            else:
                                # Generate figure on-demand if not pre-loaded
                                try:
                                    latest_values = universe_data["latest_values"]
                                    performance_matrix = universe_data[
                                        "performance_matrix"
                                    ]

                                    # Create performance DataFrame
                                    perf_data = {"Latest": latest_values}
                                    perf_data.update(performance_matrix)
                                    perf_df = pd.DataFrame(perf_data)

                                    # Generate figure
                                    fig = HeatmapGenerator.performance_heatmap_from_perf_data(
                                        perf_df, title=universe
                                    )

                                    # Convert to dict and cache
                                    fig_dict = fig.to_dict()
                                    universe_data["figure"] = fig_dict
                                    figure_cache[universe] = fig_dict
                                    charts_loaded += 1

                                except Exception as e:
                                    logger.error(
                                        f"Error generating figure for {universe}: {e}"
                                    )
                                    figure_cache[universe] = None
                        else:
                            figure_cache[universe] = None

                # Determine if all charts are ready
                charts_ready = charts_loaded == len(universes)

                return figure_cache, {
                    "charts_ready": charts_ready,
                    "charts_loaded": charts_loaded,
                    "total_charts": len(universes),
                }

            except Exception as e:
                logger.error(f"Error updating figure cache: {e}")
                return {}, {"charts_ready": False, "charts_loaded": 0}

        # Pre-loading indicator callback
        @callback(
            [Output("preload-progress", "style"), Output("preload-text", "children")],
            Input("preload-status", "data"),
            prevent_initial_call=False,
            allow_duplicate=True,
        )
        def update_preload_indicator(preload_status):
            """Update pre-loading progress indicator."""
            try:
                if not preload_status:
                    return {"display": "none"}, ""

                charts_loaded = preload_status.get("charts_loaded", 0)
                total_charts = preload_status.get("total_charts", 6)
                charts_ready = preload_status.get("charts_ready", False)

                if charts_ready:
                    # All charts loaded
                    progress_style = {
                        "display": "block",
                        "background": "linear-gradient(90deg, #059669, #047857)",
                        "height": "4px",
                        "width": "100%",
                        "transition": "width 0.3s ease",
                        "borderRadius": "2px",
                        "marginBottom": "1rem",
                    }
                    text = "✅ All charts loaded and ready!"
                elif charts_loaded > 0:
                    # Partial loading
                    progress_percent = (charts_loaded / total_charts) * 100
                    progress_style = {
                        "display": "block",
                        "background": "linear-gradient(90deg, #059669, #047857)",
                        "height": "4px",
                        "width": f"{progress_percent}%",
                        "transition": "width 0.3s ease",
                        "borderRadius": "2px",
                        "marginBottom": "1rem",
                    }
                    text = f"🔄 Loading charts... {charts_loaded}/{total_charts} ready"
                else:
                    # Not started
                    progress_style = {"display": "none"}
                    text = "⏳ Preparing charts..."

                return progress_style, text

            except Exception as e:
                logger.error(f"Error updating preload indicator: {e}")
                return {"display": "none"}, ""

        # Note: Removed clientside callback to avoid duplicate output conflicts
        # Hover effects can be added via CSS if needed

    @staticmethod
    def _register_individual_chart_callback(chart_index: int, universe_name: str):
        """Register callback for individual chart loading with optimized performance."""

        @callback(
            Output(f"chart-container-{chart_index}", "children"),
            [
                Input("global-data", "data"),
                Input("figure-cache", "data"),
            ],
            prevent_initial_call=False,
        )
        def load_individual_chart(global_data, figure_cache):
            """Load individual chart when global data is available."""
            name = universe_name
            index = chart_index
            try:
                logger.info(f"Loading chart for {name} (index {index})")
                # Priority 1: Use pre-loaded figure from consolidated cache
                if (
                    figure_cache
                    and name in figure_cache
                    and figure_cache[name] is not None
                ):
                    fig = go.Figure(figure_cache[name])
                    return dcc.Graph(
                        figure=fig,
                        config={"displayModeBar": False},
                        style={"width": "100%", "height": "400px"},
                    )

                # Priority 2: Use figure from global data (pre-loaded)
                if global_data and name in global_data:
                    universe_data = global_data[name]
                    if (
                        universe_data.get("data_available", False)
                        and "figure" in universe_data
                        and universe_data["figure"] is not None
                    ):
                        fig = go.Figure(universe_data["figure"])
                        return dcc.Graph(
                            figure=fig,
                            config={"displayModeBar": False},
                            style={"width": "100%", "height": "400px"},
                        )

                # Priority 3: Show skeleton while waiting for pre-loading
                if global_data is None or "error" in global_data:
                    return SkeletonLoader.create_chart_skeleton(
                        f"Pre-loading {name}..."
                    )

                if name not in global_data:
                    return SkeletonLoader.create_chart_skeleton(
                        f"Pre-loading {name}..."
                    )

                universe_data = global_data[name]

                if not universe_data.get("data_available", False):
                    if "error" in universe_data:
                        return ErrorDisplay.create_chart_error(
                            f"Error loading {name}: {universe_data['error']}",
                            f"chart-{index}",
                        )
                    else:
                        return LayoutHelpers.create_no_data_message(name)

                # Priority 4: Generate figure on-demand as fallback
                latest_values = universe_data["latest_values"]
                performance_matrix = universe_data["performance_matrix"]

                # Create performance DataFrame from pre-calculated data
                perf_data = {"Latest": latest_values}
                perf_data.update(performance_matrix)
                perf_df = pd.DataFrame(perf_data)

                # Generate optimized heatmap figure
                fig = HeatmapGenerator.performance_heatmap_from_perf_data(
                    perf_df, title=name
                )

                return dcc.Graph(
                    figure=fig,
                    config={"displayModeBar": False},
                    style={"width": "100%", "height": "400px"},
                )

            except Exception as e:
                logger.error(f"Error loading chart for {name}: {e}")
                return ErrorDisplay.create_chart_error(
                    f"Error generating chart for {name}: {str(e)}",
                    f"chart-{index}",
                )
