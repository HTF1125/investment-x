"""Modal components for Insights page."""

import dash_bootstrap_components as dbc
from dash import html
from dash_iconify import DashIconify

# Consistent color scheme
COLORS = {
    "primary": "#3b82f6",
    "secondary": "#64748b",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "dark": "#1e293b",
    "background": "#0f172a",
    "surface": "#1e293b",
    "surface_light": "#334155",
    "text_primary": "#f1f5f9",
    "text_secondary": "#94a3b8",
    "border": "#475569",
}


def create_summary_modal() -> dbc.Modal:
    """Create summary view modal."""
    return dbc.Modal(
        [
            dbc.ModalHeader(
                [
                    html.Div(
                        [
                            html.I(
                                className="fas fa-file-invoice me-2",
                                style={"color": COLORS["primary"], "fontSize": "1.2rem"},
                            ),
                            html.Span(
                                "Insight Summary",
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
                        id="close-modal",
                        color="link",
                        className="ms-auto",
                        style={"color": COLORS["text_secondary"]},
                    ),
                ],
                close_button=False,
                style={"background": COLORS["surface"], "borderBottom": f"1px solid {COLORS['border']}"},
            ),
            dbc.ModalBody(
                [
                    html.Div(
                        id="modal-body-content",
                        style={
                            "backgroundColor": COLORS["background"],
                            "color": COLORS["text_primary"],
                            "whiteSpace": "pre-wrap",
                            "overflowY": "auto",
                            "padding": "28px",
                            "borderRadius": "12px",
                            "minHeight": "400px",
                            "maxHeight": "calc(80vh - 240px)",
                        },
                    ),
                ],
                style={"backgroundColor": COLORS["surface"], "padding": "20px"},
            ),
        ],
        id="insight-modal",
        is_open=False,
        centered=True,
        size="xl",
    )


def create_edit_summary_modal() -> dbc.Modal:
    """Create edit summary modal."""
    return dbc.Modal(
        [
            dbc.ModalHeader(
                html.Div(
                    [
                        DashIconify(icon="carbon:edit", width=22, color=COLORS["primary"]),
                        html.Span("Edit Insight Summary", style={"color": COLORS["text_primary"], "fontWeight": "600"}),
                        dbc.Button(
                            DashIconify(icon="carbon:close", width=18),
                            id="cancel-summary-edit",
                            color="link",
                            className="ms-auto",
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center", "width": "100%"},
                ),
                close_button=False,
            ),
            dbc.ModalBody(
                [
                    dbc.Textarea(
                        id="edit-summary-textarea",
                        placeholder="Write or paste the insight summary here...",
                        style={"minHeight": "220px", "backgroundColor": COLORS["background"], "color": COLORS["text_primary"]},
                    ),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button("Cancel", id="dismiss-summary-edit", color="secondary", outline=True, className="me-auto"),
                    dbc.Button(
                        [DashIconify(icon="carbon:save", width=18), "Save Changes"],
                        id="save-summary-button",
                        color="primary",
                    ),
                ]
            ),
        ],
        id="edit-summary-modal",
        is_open=False,
        centered=True,
        size="lg",
    )


def create_add_publisher_modal() -> dbc.Modal:
    """Create add publisher modal."""
    return dbc.Modal(
        [
            dbc.ModalHeader(
                [
                    html.Div(
                        [
                            html.I(className="fas fa-plus-circle me-2", style={"color": COLORS["primary"]}),
                            html.Span("Add Publisher", style={"color": COLORS["text_primary"], "fontWeight": "600"}),
                        ],
                        style={"display": "flex", "alignItems": "center"},
                    ),
                    dbc.Button(html.I(className="fas fa-times"), id="close-add-publisher-modal", color="link"),
                ],
                close_button=False,
            ),
            dbc.ModalBody(
                [
                    html.Div(
                        [
                            html.Label("Publisher Name", style={"color": COLORS["text_primary"], "fontWeight": "500"}),
                            dbc.Input(id="publisher-name-input", placeholder="e.g., BlackRock Insights"),
                        ],
                        className="mb-3",
                    ),
                    html.Div(
                        [
                            html.Label("Publisher URL", style={"color": COLORS["text_primary"], "fontWeight": "500"}),
                            dbc.Input(id="publisher-url-input", type="url", placeholder="https://example.com/insights"),
                        ],
                        className="mb-3",
                    ),
                    html.Div(
                        [
                            html.Label("Update Frequency", style={"color": COLORS["text_primary"], "fontWeight": "500"}),
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
                            ),
                        ],
                        className="mb-3",
                    ),
                    html.Div(id="add-publisher-feedback"),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button("Cancel", id="cancel-add-publisher", color="secondary", outline=True),
                    dbc.Button("Add Publisher", id="submit-add-publisher", color="primary"),
                ]
            ),
        ],
        id="add-publisher-modal",
        is_open=False,
        centered=True,
        size="lg",
    )


def create_all_modals():
    """Create all modals for the insights page."""
    return [
        create_summary_modal(),
        create_edit_summary_modal(),
        create_add_publisher_modal(),
    ]







