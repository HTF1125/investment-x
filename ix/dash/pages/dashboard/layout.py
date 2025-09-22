from dash import html, dcc
import dash

# Register Page
dash.register_page(__name__, path="/", title="Dashboard", name="Dashboard")

# Import analysis modules
from ix.dash.pages.dashboard import PerformanceHeatmap, MarketPerformance

# Dashboard layout with loading states - simplified approach
layout = html.Div(
    [
        # Main loading wrapper
        dcc.Loading(
            id="dashboard-main-loading",
            children=[
                # Performance Heatmaps section with individual loading
                dcc.Loading(
                    id="heatmap-section-loading",
                    children=html.Div(id="heatmap-section"),
                    type="circle",
                    color="#3b82f6",
                    style={"marginBottom": "2rem"},
                ),
                # Market Performance section with individual loading
                dcc.Loading(
                    id="performance-section-loading",
                    children=html.Div(id="performance-section"),
                    type="circle",
                    color="#3b82f6",
                ),
            ],
            type="dot",
            color="#3b82f6",
            style={"marginTop": "100px"},
        ),
    ],
    style={
        "backgroundColor": "#0f172a",
        "color": "#ffffff",
    },
    className="main-content",
)


# Initialize content immediately to avoid callback conflicts
def initialize_content():
    """Initialize dashboard content with error handling"""
    try:
        heatmap_content = PerformanceHeatmap.Section()
    except Exception as e:
        heatmap_content = html.Div(
            [
                html.H3("Performance Heatmaps", style={"color": "#f1f5f9"}),
                html.Div(
                    f"Error loading heatmaps: {str(e)}",
                    style={"color": "#ef4444", "padding": "1rem"},
                ),
            ]
        )

    try:
        performance_content = MarketPerformance.Section()
    except Exception as e:
        performance_content = html.Div(
            [
                html.H3("Market Performance", style={"color": "#f1f5f9"}),
                html.Div(
                    f"Error loading performance charts: {str(e)}",
                    style={"color": "#ef4444", "padding": "1rem"},
                ),
            ]
        )

    return [heatmap_content, performance_content]


# Set the content directly to avoid callback issues
try:
    content = initialize_content()
    # Update the layout with actual content
    layout.children[0].children = content
except Exception as e:
    # Fallback to error message
    layout.children[0].children = html.Div(
        [
            html.H2("Dashboard", style={"color": "#f1f5f9", "textAlign": "center"}),
            html.Div(
                f"Error initializing dashboard: {str(e)}",
                style={"color": "#ef4444", "padding": "2rem", "textAlign": "center"},
            ),
        ]
    )
