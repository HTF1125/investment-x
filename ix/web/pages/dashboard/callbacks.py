"""
Callbacks module for dashboard.
Handles dashboard callbacks and event handlers.
"""

import pandas as pd
import traceback
import json
import plotly.graph_objects as go
from datetime import datetime
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
                try:
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

        # Heatmap section loading callback
        @callback(
            Output("heatmap-section", "children"),
            Output("dashboard-load-state", "data"),
            [
                Input("global-data", "data"),
                Input("manual-refresh-btn", "n_clicks"),
            ],
            State("dashboard-load-state", "data"),
            prevent_initial_call=False,
            allow_duplicate=True,
        )
        def load_heatmap_section(global_data, manual_refresh, load_state):
            """Load the heatmap section with lazy loading for individual charts."""

            try:
                logger.info(f"Loading heatmap section from global data")

                if global_data is None or "error" in global_data:
                    # Show skeleton while waiting for data
                    return SkeletonLoader.create_section_skeleton(
                        "Performance Heatmaps",
                        "Loading market data...",
                    ), {"loaded": False}

                # Create chart cards with lazy loading containers
                chart_cards = []
                universes = [
                    "Major Indices",
                    "Global Markets",
                    "Sectors",
                    "Themes",
                    "Commodities",
                    "Currencies",
                ]

                from ix.web.components import Grid, Card

                for i, universe in enumerate(universes):
                    # Create individual chart containers that will load lazily
                    chart_content = html.Div(
                        id=f"chart-container-{i}",
                        children=SkeletonLoader.create_chart_skeleton(
                            f"Loading {universe}..."
                        ),
                    )
                    chart_cards.append(Card(chart_content))

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
            ctx = callback_context
            if not ctx.triggered:
                raise PreventUpdate

            current_time = datetime.now().strftime("%H:%M:%S")
            return f"Last updated: {current_time}"

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

        def create_chart_callback(index: int, name: str):
            @callback(
                Output(f"chart-container-{index}", "children"),
                [
                    Input("global-data", "data"),
                    Input("figure-cache", "data"),
                ],
                prevent_initial_call=False,
                allow_duplicate=True,
            )
            def load_individual_chart(global_data, figure_cache):
                """Load individual chart when global data is available."""
                try:
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

            return load_individual_chart

        # Create and register the callback with proper closure
        create_chart_callback(chart_index, universe_name)
