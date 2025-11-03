"""Add Publisher Modal for Insights Dashboard"""

import dash_bootstrap_components as dbc
from dash import html

# Color scheme matching the insights page
COLORS = {
    "primary": "#3b82f6",
    "secondary": "#64748b",
    "background": "#1e293b",
    "card_bg": "#0f172a",
    "border": "#334155",
    "text_primary": "#f1f5f9",
    "text_secondary": "#94a3b8",
    "success": "#10b981",
    "danger": "#ef4444",
}

# Add Publisher Modal
add_publisher_modal = dbc.Modal(
    [
        dbc.ModalHeader(
            [
                html.Div(
                    [
                        html.I(
                            className="fas fa-plus-circle me-2",
                            style={"color": COLORS["primary"], "fontSize": "1.3rem"},
                        ),
                        html.Span(
                            "Add Publisher",
                            style={
                                "color": COLORS["text_primary"],
                                "fontWeight": "600",
                                "fontSize": "1.3rem",
                            },
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center"},
                ),
                dbc.Button(
                    html.I(className="fas fa-times"),
                    id="close-add-publisher-modal",
                    color="link",
                    style={
                        "position": "absolute",
                        "right": "16px",
                        "top": "16px",
                        "color": COLORS["secondary"],
                        "fontSize": "1.2rem",
                        "padding": "4px 8px",
                        "transition": "all 0.2s ease",
                        "border": "none",
                        "background": "transparent",
                    },
                    className="modal-close-button",
                ),
            ],
            close_button=False,
            style={
                "backgroundColor": COLORS["card_bg"],
                "borderBottom": f"1px solid {COLORS['border']}",
                "padding": "16px 24px",
            },
        ),
        dbc.ModalBody(
            [
                # Publisher Name Input
                html.Div(
                    [
                        html.Label(
                            [
                                html.I(className="fas fa-building me-2"),
                                "Publisher Name",
                            ],
                            style={
                                "color": COLORS["text_primary"],
                                "fontWeight": "500",
                                "marginBottom": "8px",
                                "display": "flex",
                                "alignItems": "center",
                            },
                        ),
                        dbc.Input(
                            id="publisher-name-input",
                            type="text",
                            placeholder="e.g., BlackRock Insights",
                            style={
                                "backgroundColor": COLORS["background"],
                                "border": f"1px solid {COLORS['border']}",
                                "color": COLORS["text_primary"],
                                "borderRadius": "8px",
                                "padding": "10px 12px",
                            },
                        ),
                    ],
                    className="mb-3",
                ),
                # Publisher URL Input
                html.Div(
                    [
                        html.Label(
                            [
                                html.I(className="fas fa-link me-2"),
                                "Publisher URL",
                            ],
                            style={
                                "color": COLORS["text_primary"],
                                "fontWeight": "500",
                                "marginBottom": "8px",
                                "display": "flex",
                                "alignItems": "center",
                            },
                        ),
                        dbc.Input(
                            id="publisher-url-input",
                            type="url",
                            placeholder="https://example.com/insights",
                            style={
                                "backgroundColor": COLORS["background"],
                                "border": f"1px solid {COLORS['border']}",
                                "color": COLORS["text_primary"],
                                "borderRadius": "8px",
                                "padding": "10px 12px",
                            },
                        ),
                    ],
                    className="mb-3",
                ),
                # Frequency Input
                html.Div(
                    [
                        html.Label(
                            [
                                html.I(className="fas fa-clock me-2"),
                                "Update Frequency",
                            ],
                            style={
                                "color": COLORS["text_primary"],
                                "fontWeight": "500",
                                "marginBottom": "8px",
                                "display": "flex",
                                "alignItems": "center",
                            },
                        ),
                        dbc.Select(
                            id="publisher-frequency-input",
                            options=[
                                {"label": "Daily", "value": "Daily"},
                                {"label": "Weekly", "value": "Weekly"},
                                {"label": "Monthly", "value": "Monthly"},
                                {"label": "Quarterly", "value": "Quarterly"},
                                {"label": "As Needed", "value": "As Needed"},
                            ],
                            value="Weekly",
                            style={
                                "backgroundColor": COLORS["background"],
                                "border": f"1px solid {COLORS['border']}",
                                "color": COLORS["text_primary"],
                                "borderRadius": "8px",
                                "padding": "8px 12px",
                            },
                        ),
                    ],
                    className="mb-3",
                ),
                # Feedback message
                html.Div(
                    id="add-publisher-feedback",
                    style={"marginTop": "16px"},
                ),
            ],
            style={
                "backgroundColor": COLORS["card_bg"],
                "padding": "24px",
            },
        ),
        dbc.ModalFooter(
            [
                dbc.Button(
                    [
                        html.I(className="fas fa-times me-2"),
                        "Cancel",
                    ],
                    id="cancel-add-publisher",
                    color="secondary",
                    outline=True,
                    style={
                        "borderRadius": "8px",
                        "padding": "8px 20px",
                        "fontWeight": "500",
                        "transition": "all 0.2s ease",
                    },
                ),
                dbc.Button(
                    [
                        html.I(className="fas fa-check me-2"),
                        "Add Publisher",
                    ],
                    id="submit-add-publisher",
                    color="primary",
                    style={
                        "borderRadius": "8px",
                        "padding": "8px 20px",
                        "fontWeight": "500",
                        "transition": "all 0.2s ease",
                        "background": f"linear-gradient(135deg, {COLORS['primary']} 0%, #2563eb 100%)",
                        "border": "none",
                    },
                ),
            ],
            style={
                "backgroundColor": COLORS["card_bg"],
                "borderTop": f"1px solid {COLORS['border']}",
                "padding": "16px 24px",
                "display": "flex",
                "justifyContent": "flex-end",
                "gap": "12px",
            },
        ),
    ],
    id="add-publisher-modal",
    is_open=False,
    centered=True,
    backdrop="static",
    size="lg",
    className="modern-modal add-publisher-modal",
    style={
        "position": "fixed",
        "top": "50%",
        "left": "50%",
        "transform": "translate(-50%, -50%)",
        "maxWidth": "600px",
        "width": "90vw",
        "maxHeight": "90vh",
        "overflow": "auto",
        "zIndex": "1050",
        "boxShadow": "0 20px 60px rgba(0, 0, 0, 0.5)",
        "borderRadius": "12px",
        "border": f"1px solid {COLORS['border']}",
    },
)
