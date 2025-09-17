"""
Comprehensive Macro Analysis Page
Modern responsive layout for ISM business cycle and liquidity analysis.
"""

from dash import html
import dash
import dash_mantine_components as dmc
from ix.dash.pages.macro import IsmCycle, Liquidity
from ix.misc.date import today


# Register Page
dash.register_page(
    __name__, path="/macro", title="Macro Analysis", name="Macro Analysis"
)

# Main Layout
layout = html.Div(
    [
        # Shared Controls Section
        dmc.Container(
            [
                dmc.Stack(
                    [
                        dmc.Title(
                            "📊 Macro Economic Analysis",
                            order=1,
                            ta="center",
                            c="gray",
                            fw="bold",
                            mb="xs",
                            style={"color": "#ffffff"},
                        ),
                        dmc.Text(
                            "Comprehensive analysis of ISM business cycles and global liquidity trends",
                            c="gray",
                            ta="center",
                            size="md",
                            mb="lg",
                            style={"color": "#a0aec0"},
                        ),
                    ],
                    gap="xs",
                ),
                # Shared date controls
                dmc.Paper(
                    dmc.Group(
                        [
                            dmc.NumberInput(
                                id="macro-start-date",
                                label="Start Year",
                                value=today().year - 10,
                                min=2000,
                                max=today().year,
                                step=1,
                                w=120,
                                size="sm",
                                styles={
                                    "label": {
                                        "color": "#cbd5e0",
                                        "fontSize": "12px",
                                        "fontWeight": "500",
                                    },
                                    "input": {
                                        "backgroundColor": "#2d3748",
                                        "color": "#ffffff",
                                        "border": "1px solid #4a5568",
                                    },
                                },
                            ),
                            dmc.NumberInput(
                                id="macro-end-date",
                                label="End Year",
                                value=today().year,
                                min=2000,
                                max=today().year,
                                step=1,
                                w=120,
                                size="sm",
                                styles={
                                    "label": {
                                        "color": "#cbd5e0",
                                        "fontSize": "12px",
                                        "fontWeight": "500",
                                    },
                                    "input": {
                                        "backgroundColor": "#2d3748",
                                        "color": "#ffffff",
                                        "border": "1px solid #4a5568",
                                    },
                                },
                            ),
                        ],
                        justify="center",
                        gap="lg",
                    ),
                    p="lg",
                    mb="xl",
                    bg="dark",
                    radius="md",
                    withBorder=True,
                    style={
                        "borderColor": "rgba(255, 255, 255, 0.1)",
                        "backgroundColor": "rgba(45, 55, 72, 0.3)",
                    },
                ),
            ],
            fluid=True,
            p="lg",
            style={
                "background": "rgba(26, 32, 44, 0.8)",
                "border-radius": "16px",
                "border": "1px solid rgba(255, 255, 255, 0.1)",
                "box-shadow": "0 4px 6px rgba(0, 0, 0, 0.1)",
                "marginBottom": "30px",
            },
        ),
        # ISM Business Cycle Analysis
        html.Div(
            [
                html.Div(IsmCycle.Section(), className="ism-section"),
            ],
            className="ism-container",
            style={"marginBottom": "30px"},
        ),
        # Global Liquidity Analysis
        html.Div(
            [
                html.Div(Liquidity.Section(), className="liquidity-section"),
            ],
            className="liquidity-container",
        ),
    ],
    style={
        "backgroundColor": "#0f172a",
        "color": "#ffffff",
        "minHeight": "100vh",
        "paddingTop": "90px",  # Account for fixed navbar
        "paddingBottom": "40px",
        "paddingLeft": "20px",
        "paddingRight": "20px",
    },
    className="main-content",  # Add class for responsive margin
)
