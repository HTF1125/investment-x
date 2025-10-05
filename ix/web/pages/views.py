# import dash_mantine_components as dmc  # Removed to avoid React errors
from dash import html
import dash

# Register Page
dash.register_page(__name__, path="/views", title="Views", name="Views")

# Views layout
layout = html.Div(
    [
        html.H1("📈 Market Views", className="main-title"),
        html.P(
            "Professional market analysis and trading views",
            className="subtitle",
        ),
        html.Div(
            "Market views page coming soon! This will include professional analysis, trading ideas, and market commentary.",
            style={
                "marginTop": "2rem",
                "backgroundColor": "rgba(59, 130, 246, 0.1)",
                "border": "1px solid rgba(59, 130, 246, 0.3)",
                "borderRadius": "8px",
                "padding": "20px",
                "color": "#93c5fd",
            },
        ),
    ],
    style={"marginTop": "80px", "padding": "20px"},
)
