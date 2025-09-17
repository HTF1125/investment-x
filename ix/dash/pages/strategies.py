# import dash_mantine_components as dmc  # Removed to avoid React errors
from dash import html
import dash

# Register Page
dash.register_page(__name__, path="/strategies", title="Strategies", name="Strategies")

# Strategies layout
layout = html.Div(
    [
        html.H1("⚡ Trading Strategies", className="main-title"),
        html.P(
            "Advanced trading strategies and backtesting tools",
            className="subtitle",
        ),
        html.Div(
            "Trading strategies page coming soon! This will include strategy development, backtesting, and performance analysis tools.",
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
