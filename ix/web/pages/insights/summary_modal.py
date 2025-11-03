"""
Enhanced Summary Modal Component
Modern design with improved typography, better controls, and enhanced UX.
"""

import dash_bootstrap_components as dbc
from dash import html

# Modern Color Scheme
COLORS = {
    "primary": "#3b82f6",
    "secondary": "#64748b",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "dark": "#1e293b",
    "light": "#f8fafc",
    "background": "#0f172a",
    "surface": "#1e293b",
    "surface_light": "#334155",
    "text_primary": "#f1f5f9",
    "text_secondary": "#94a3b8",
    "border": "#475569",
}

# Enhanced Full-Screen Modal for Summary
summary_modal = dbc.Modal(
    [
        # Modern Header with Gradient
        dbc.ModalHeader(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Div(
                                    [
                                        html.I(
                                            className="fas fa-file-invoice me-2",
                                            style={
                                                "color": COLORS["primary"],
                                                "fontSize": "1.2rem",
                                            },
                                        ),
                                        html.Span(
                                            "Insight Summary",
                                            style={
                                                "color": COLORS["text_primary"],
                                                "fontWeight": "600",
                                                "fontSize": "1.3rem",
                                                "letterSpacing": "-0.01em",
                                            },
                                        ),
                                    ],
                                    style={"display": "flex", "alignItems": "center"},
                                ),
                            ],
                            md=9,
                        ),
                        dbc.Col(
                            [
                                dbc.ButtonGroup(
                                    [
                                        dbc.Button(
                                            html.I(className="fas fa-volume-up"),
                                            id="read-summary",
                                            color="success",
                                            size="sm",
                                            n_clicks=0,
                                            title="Read aloud",
                                            style={
                                                "borderRadius": "6px 0 0 6px",
                                                "padding": "6px 12px",
                                            },
                                        ),
                                        dbc.Button(
                                            html.I(className="fas fa-stop"),
                                            id="stop-summary",
                                            color="warning",
                                            size="sm",
                                            n_clicks=0,
                                            title="Stop reading",
                                            style={
                                                "borderRadius": "0",
                                                "padding": "6px 12px",
                                            },
                                        ),
                                    ],
                                    size="sm",
                                ),
                                dbc.Button(
                                    html.I(
                                        className="fas fa-times",
                                        style={"fontSize": "1.2rem"},
                                    ),
                                    id="close-modal",
                                    color="link",
                                    size="sm",
                                    n_clicks=0,
                                    className="ms-2 text-secondary",
                                    title="Close",
                                    style={
                                        "padding": "6px 10px",
                                        "borderRadius": "6px",
                                    },
                                ),
                            ],
                            md=3,
                            className="d-flex justify-content-end align-items-center",
                        ),
                    ],
                    align="center",
                ),
            ],
            close_button=False,
            style={
                "background": f"linear-gradient(135deg, {COLORS['surface']} 0%, {COLORS['surface_light']} 100%)",
                "borderBottom": f"2px solid {COLORS['primary']}",
                "padding": "16px 24px",
                "boxShadow": "0 2px 8px rgba(0, 0, 0, 0.15)",
            },
        ),
        # Enhanced Modal Body
        dbc.ModalBody(
            [
                # Summary Content Container
                html.Div(
                    [
                        html.Div(
                            id="modal-body-content",
                            style={
                                "backgroundColor": COLORS["background"],
                                "color": COLORS["text_primary"],
                                "whiteSpace": "pre-wrap",
                                "overflowY": "auto",
                                "fontSize": "1.05rem",
                                "lineHeight": "1.75",
                                "padding": "28px",
                                "borderRadius": "12px",
                                "border": f"1px solid {COLORS['border']}",
                                "minHeight": "400px",
                                "maxHeight": "calc(80vh - 240px)",
                                "fontFamily": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                                "boxShadow": "inset 0 2px 8px rgba(0, 0, 0, 0.3)",
                            },
                        ),
                        # Reading Progress Indicator
                        html.Div(
                            [
                                html.Div(
                                    id="reading-progress",
                                    style={
                                        "width": "0%",
                                        "height": "3px",
                                        "background": f"linear-gradient(90deg, {COLORS['primary']}, {COLORS['success']})",
                                        "borderRadius": "2px",
                                        "transition": "width 0.3s ease",
                                        "boxShadow": f"0 0 8px {COLORS['primary']}",
                                    },
                                ),
                            ],
                            style={
                                "width": "100%",
                                "height": "3px",
                                "backgroundColor": COLORS["border"],
                                "borderRadius": "2px",
                                "marginTop": "12px",
                            },
                        ),
                    ]
                ),
                # Publishers Section
                html.Div(
                    [
                        html.Div(
                            [
                                html.I(
                                    className="fas fa-building me-2",
                                    style={"color": COLORS["primary"]},
                                ),
                                html.Span(
                                    "Publishers",
                                    style={
                                        "color": COLORS["text_primary"],
                                        "fontWeight": "600",
                                        "fontSize": "1rem",
                                    },
                                ),
                            ],
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "marginBottom": "12px",
                                "paddingBottom": "8px",
                                "borderBottom": f"1px solid {COLORS['border']}",
                            },
                        ),
                        html.Div(
                            id="modal-publishers-content",
                            style={
                                "display": "flex",
                                "flexWrap": "wrap",
                                "gap": "12px",
                            },
                        ),
                    ],
                    className="mt-3",
                    style={
                        "padding": "16px",
                        "backgroundColor": COLORS["background"],
                        "borderRadius": "8px",
                        "border": f"1px solid {COLORS['border']}",
                    },
                ),
            ],
            style={
                "backgroundColor": COLORS["surface"],
                "padding": "20px 24px",
                "height": "calc(80vh - 140px)",
                "overflowY": "auto",
            },
        ),
        # Enhanced Footer - Compact
        dbc.ModalFooter(
            [
                html.Div(
                    [
                        html.Small(
                            [
                                html.I(className="fas fa-info-circle me-1"),
                                "Powered by AI",
                            ],
                            style={
                                "color": COLORS["text_secondary"],
                                "fontSize": "0.75rem",
                            },
                        ),
                        html.Small(
                            [
                                html.I(className="fas fa-clock me-1 ms-3"),
                                html.Span(id="modal-last-updated", children="Just now"),
                            ],
                            style={
                                "color": COLORS["text_secondary"],
                                "fontSize": "0.75rem",
                            },
                        ),
                    ],
                    style={
                        "display": "flex",
                        "justifyContent": "center",
                        "alignItems": "center",
                        "width": "100%",
                    },
                ),
            ],
            style={
                "background": f"linear-gradient(135deg, {COLORS['surface']} 0%, {COLORS['surface_light']} 100%)",
                "borderTop": f"1px solid {COLORS['border']}",
                "padding": "12px 24px",
                "boxShadow": "0 -2px 8px rgba(0, 0, 0, 0.1)",
            },
        ),
    ],
    id="insight-modal",
    is_open=False,
    centered=True,
    backdrop="static",
    keyboard=True,
    scrollable=True,
    size="xl",
    style={
        "width": "80vw",
        "height": "80vh",
        "maxWidth": "80vw",
        "maxHeight": "80vh",
        "margin": "auto",
        "position": "fixed",
        "top": "50%",
        "left": "50%",
        "transform": "translate(-50%, -50%)",
        "zIndex": "9999",
        "boxShadow": "0 25px 50px -12px rgba(0, 0, 0, 0.9), 0 0 100px rgba(59, 130, 246, 0.2)",
        "borderRadius": "20px",
        "overflow": "hidden",
        "border": f"1px solid {COLORS['border']}",
    },
    className="modern-modal",
)
