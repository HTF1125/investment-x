from dash import html, dcc
import dash

from ix.web.components import Grid, Card
from ix.web.pages.dashboard.ui_components import LayoutHelpers, SkeletonLoader
from ix.web.pages.dashboard.callbacks import DashboardCallbacks

# Register Page
dash.register_page(__name__, path="/", title="Dashboard", name="Dashboard")


# --- Layout ---
layout = html.Div(
    [
        # Stores for state management
        dcc.Store(id="dashboard-load-state", data={"loaded": False}),
        dcc.Store(id="last-refresh-time", data=None),
        dcc.Store(id="global-data", data=None),
        # Consolidated figure store for all charts
        dcc.Store(id="figure-cache", data={}),
        # Pre-loading status store
        dcc.Store(
            id="preload-status", data={"charts_ready": False, "charts_loaded": 0}
        ),
        # Global data refresh interval (5 minutes with caching)
        dcc.Interval(
            id="global-data-refresh-interval",
            interval=60 * 1000 * 5,  # 5 minutes
            n_intervals=0,
            disabled=False,
        ),
        # Page header with refresh controls
        LayoutHelpers.create_page_header(
            "Investment Dashboard",
            "Real-time market performance and analytics",
            "manual-refresh-btn",
        ),
        # Pre-loading status indicator
        html.Div(
            id="preload-indicator",
            children=[
                html.Div(
                    id="preload-progress",
                    style={
                        "display": "none",
                        "background": "linear-gradient(90deg, #059669, #047857)",
                        "height": "4px",
                        "width": "0%",
                        "transition": "width 0.3s ease",
                        "borderRadius": "2px",
                        "marginBottom": "1rem",
                    },
                ),
                html.Div(
                    id="preload-text",
                    style={
                        "color": "#94a3b8",
                        "fontSize": "0.9rem",
                        "textAlign": "center",
                        "marginBottom": "1rem",
                        "display": "none",
                    },
                ),
            ],
        ),
        # Dashboard content
        html.Div(
            [
                html.Div(
                    id="heatmap-section",
                    children=SkeletonLoader.create_section_skeleton(
                        "Performance Heatmaps",
                        "Analyzing market performance across sectors...",
                    ),
                ),
            ],
            style={
                "display": "grid",
                "gap": "2rem",
                "gridTemplateColumns": "1fr",
            },
        ),
    ],
    style={
        "maxWidth": "1600px",
        "margin": "0 auto",
        "padding": "2rem",
        "backgroundColor": "transparent",
        "color": "#ffffff",
        "fontFamily": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    },
    className="dashboard-content",
)


# Register callbacks only once
if (
    not hasattr(DashboardCallbacks, "_callbacks_registered")
    or not DashboardCallbacks._callbacks_registered
):
    DashboardCallbacks.register_callbacks()
