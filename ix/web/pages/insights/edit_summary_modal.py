"""
Edit Summary Modal Component
Provides a rich text area for updating insight summaries directly from the UI.
"""

import dash_bootstrap_components as dbc
from dash import html
from dash_iconify import DashIconify

# Consistent styling palette with other insight components
COLORS = {
    "primary": "#2563eb",
    "secondary": "#64748b",
    "background": "#0f172a",
    "surface": "#1e293b",
    "surface_light": "#334155",
    "text_primary": "#f8fafc",
    "text_secondary": "#cbd5f5",
    "border": "#374151",
}


edit_summary_modal = dbc.Modal(
    [
        dbc.ModalHeader(
            html.Div(
                [
                    html.Div(
                        [
                            DashIconify(
                                icon="carbon:edit",
                                width=22,
                                color=COLORS["primary"],
                                style={"marginRight": "12px"},
                            ),
                            html.Div(
                                [
                                    html.Span(
                                        "Edit Insight Summary",
                                        style={
                                            "color": COLORS["text_primary"],
                                            "fontWeight": "600",
                                            "fontSize": "1.1rem",
                                        },
                                    ),
                                    html.Small(
                                        id="edit-summary-doc-name",
                                        style={
                                            "color": COLORS["text_secondary"],
                                            "display": "block",
                                            "marginTop": "4px",
                                        },
                                    ),
                                ]
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                        },
                    ),
                    dbc.Button(
                        DashIconify(
                            icon="carbon:close",
                            width=18,
                            color=COLORS["text_secondary"],
                        ),
                        id="cancel-summary-edit",
                        color="link",
                        className="ms-auto text-secondary",
                        style={
                            "padding": "6px 8px",
                            "borderRadius": "6px",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "width": "100%",
                },
            ),
            close_button=False,
            style={
                "background": COLORS["surface"],
                "borderBottom": f"1px solid {COLORS['border']}",
                "padding": "16px 22px",
            },
        ),
        dbc.ModalBody(
            [
                html.P(
                    "Refine the generated AI summary or craft your own narrative. "
                    "Changes are saved instantly and reflected across the dashboard.",
                    style={
                        "color": COLORS["text_secondary"],
                        "marginBottom": "12px",
                    },
                ),
                dbc.Textarea(
                    id="edit-summary-textarea",
                    placeholder="Write or paste the insight summary here...",
                    style={
                        "minHeight": "220px",
                        "backgroundColor": COLORS["background"],
                        "color": COLORS["text_primary"],
                        "borderColor": COLORS["border"],
                        "borderRadius": "10px",
                        "resize": "vertical",
                    },
                ),
                html.Small(
                    "Tip: Keep sentences crisp and actionable. Use paragraphs for clarity.",
                    style={
                        "color": COLORS["text_secondary"],
                        "display": "block",
                        "marginTop": "12px",
                    },
                ),
            ],
            style={
                "background": COLORS["surface_light"],
                "padding": "20px 22px",
            },
        ),
        dbc.ModalFooter(
            [
                dbc.Button(
                    "Cancel",
                    id="dismiss-summary-edit",
                    color="secondary",
                    outline=True,
                    className="me-auto",
                ),
                dbc.Button(
                    [
                        DashIconify(
                            icon="carbon:save",
                            width=18,
                            color="white",
                            style={"marginRight": "8px"},
                        ),
                        html.Span("Save Changes"),
                    ],
                    id="save-summary-button",
                    color="primary",
                    className="me-2",
                    style={"display": "flex", "alignItems": "center"},
                ),
            ],
            style={
                "background": COLORS["surface"],
                "borderTop": f"1px solid {COLORS['border']}",
                "padding": "14px 22px",
            },
        ),
    ],
    id="edit-summary-modal",
    is_open=False,
    centered=True,
    backdrop="static",
    keyboard=False,
    size="lg",
    style={
        "backgroundColor": "rgba(15, 23, 42, 0.7)",
    },
)
