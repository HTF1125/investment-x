# import dash_mantine_components as dmc  # Removed to avoid React errors
from dash import html
import dash

# Register Page
dash.register_page(__name__, path="/", title="Dashboard", name="Dashboard")

# Import analysis modules
# from ix.dash.components.sections import MarketPerformance
from ix.dash.pages.dashboard import PerformanceHeatmap, MarketPerformance

# Dashboard layout
layout = html.Div(
    [

        # Universe sections
        PerformanceHeatmap.Section(),
        MarketPerformance.Section(),
    ],
    style={
        "marginTop": "80px",
        "padding": "20px",
        "backgroundColor": "#0f172a",
        "color": "#ffffff",
        "minHeight": "100vh",
    },
    className="main-content",  # Add class for responsive margin
)
