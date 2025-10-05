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
                                html.H4(
                                    "📄 Insight Summary",
                                    className="mb-0",
                                    style={
                                        "color": COLORS["text_primary"],
                                        "fontWeight": "600",
                                    },
                                ),
                                html.Small(
                                    "AI-generated insights from your document",
                                    style={
                                        "color": COLORS["text_secondary"],
                                        "fontSize": "0.9rem",
                                    },
                                ),
                            ],
                            md=8,
                        ),
                        dbc.Col(
                            [
                                dbc.ButtonGroup(
                                    [
                                        dbc.Button(
                                            [
                                                html.I(
                                                    className="fas fa-volume-up me-1"
                                                ),
                                                "Read",
                                            ],
                                            id="read-summary",
                                            color="success",
                                            size="sm",
                                            n_clicks=0,
                                            style={
                                                "borderRadius": "6px",
                                                "fontSize": "0.8rem",
                                            },
                                        ),
                                        dbc.Button(
                                            [
                                                html.I(className="fas fa-stop me-1"),
                                                "Stop",
                                            ],
                                            id="stop-summary",
                                            color="warning",
                                            size="sm",
                                            n_clicks=0,
                                            style={
                                                "borderRadius": "6px",
                                                "fontSize": "0.8rem",
                                            },
                                        ),
                                        dbc.Button(
                                            [
                                                html.I(className="fas fa-times me-1"),
                                                "Close",
                                            ],
                                            id="close-modal",
                                            color="secondary",
                                            size="sm",
                                            n_clicks=0,
                                            style={
                                                "borderRadius": "6px",
                                                "fontSize": "0.8rem",
                                            },
                                        ),
                                    ],
                                    className="float-end",
                                ),
                            ],
                            md=4,
                            className="d-flex justify-content-end",
                        ),
                    ],
                    align="center",
                ),
            ],
            style={
                "background": f"linear-gradient(135deg, {COLORS['surface']} 0%, {COLORS['surface_light']} 100%)",
                "borderBottom": f"2px solid {COLORS['border']}",
                "padding": "20px",
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
                                "fontSize": "1rem",
                                "lineHeight": "1.6",
                                "padding": "24px",
                                "borderRadius": "8px",
                                "border": f"1px solid {COLORS['border']}",
                                "minHeight": "400px",
                                "maxHeight": "70vh",
                                "fontFamily": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
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
                                        "backgroundColor": COLORS["primary"],
                                        "borderRadius": "2px",
                                        "transition": "width 0.3s ease",
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
                # Action Buttons Row
                html.Div(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Button(
                                            [
                                                html.I(className="fas fa-copy me-2"),
                                                "Copy Summary",
                                            ],
                                            id="copy-summary-btn",
                                            color="outline-primary",
                                            size="sm",
                                            style={
                                                "borderRadius": "6px",
                                                "fontSize": "0.85rem",
                                            },
                                        ),
                                    ],
                                    md=3,
                                ),
                                dbc.Col(
                                    [
                                        dbc.Button(
                                            [
                                                html.I(
                                                    className="fas fa-download me-2"
                                                ),
                                                "Export as Text",
                                            ],
                                            id="export-summary-btn",
                                            color="outline-success",
                                            size="sm",
                                            style={
                                                "borderRadius": "6px",
                                                "fontSize": "0.85rem",
                                            },
                                        ),
                                    ],
                                    md=3,
                                ),
                                dbc.Col(
                                    [
                                        dbc.Button(
                                            [
                                                html.I(className="fas fa-share me-2"),
                                                "Share Summary",
                                            ],
                                            id="share-summary-btn",
                                            color="outline-info",
                                            size="sm",
                                            style={
                                                "borderRadius": "6px",
                                                "fontSize": "0.85rem",
                                            },
                                        ),
                                    ],
                                    md=3,
                                ),
                                dbc.Col(
                                    [
                                        dbc.Button(
                                            [
                                                html.I(className="fas fa-star me-2"),
                                                "Bookmark",
                                            ],
                                            id="bookmark-summary-btn",
                                            color="outline-warning",
                                            size="sm",
                                            style={
                                                "borderRadius": "6px",
                                                "fontSize": "0.85rem",
                                            },
                                        ),
                                    ],
                                    md=3,
                                ),
                            ],
                            className="mt-4",
                        ),
                    ],
                    className="mt-3",
                ),
            ],
            style={
                "backgroundColor": COLORS["surface"],
                "padding": "20px",
            },
        ),
        # Enhanced Footer
        dbc.ModalFooter(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Small(
                                    [
                                        html.I(className="fas fa-info-circle me-1"),
                                        "Powered by AI • Generated insights may vary in accuracy",
                                    ],
                                    style={
                                        "color": COLORS["text_secondary"],
                                        "fontSize": "0.8rem",
                                    },
                                ),
                            ],
                            md=8,
                        ),
                        dbc.Col(
                            [
                                html.Small(
                                    [
                                        html.I(className="fas fa-clock me-1"),
                                        "Last updated: ",
                                        html.Span(
                                            id="modal-last-updated", children="Just now"
                                        ),
                                    ],
                                    style={
                                        "color": COLORS["text_secondary"],
                                        "fontSize": "0.8rem",
                                    },
                                ),
                            ],
                            md=4,
                            className="text-end",
                        ),
                    ],
                    align="center",
                ),
            ],
            style={
                "background": f"linear-gradient(135deg, {COLORS['surface']} 0%, {COLORS['surface_light']} 100%)",
                "borderTop": f"1px solid {COLORS['border']}",
                "padding": "16px 20px",
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
        "maxWidth": "95vw",
        "maxHeight": "95vh",
        "margin": "auto",
        "position": "fixed",
        "top": "2.5vh",
        "left": "50%",
        "transform": "translateX(-50%)",
        "zIndex": "9999",
        "boxShadow": "0 25px 50px -12px rgba(0, 0, 0, 0.8)",
        "borderRadius": "16px",
        "overflow": "hidden",
    },
    className="modern-modal",
)
