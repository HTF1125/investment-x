"""
Dash application for Investment-X charts.

This module creates a Dash app that can be mounted to FastAPI.
Displays all charts in a gallery view organized by category.
Uses callbacks for lazy loading of charts - no DB queries at import time.
"""

import dash
from dash import html, dcc, Input, Output, State, MATCH, ALL
import dash_bootstrap_components as dbc
import plotly.graph_objects as go


# Define category order
CATEGORY_ORDER = [
    "Performance",
    "RRG",
    "Business",
    "Composite",
    "Earnings",
    "Liquidity",
    "Credit",
    "Fiscal",
    "Debt",
    "Financial",
    "Consumer",
    "Inflation",
    "Surprise",
    "Gold",
    "OECD",
    "LongTerm",
    "Uncategorized",
]


def create_dash_app(requests_pathname_prefix: str = "/dash/") -> dash.Dash:
    """
    Creates and configures the Dash application.

    Uses function-based layout to defer database queries until page is accessed.
    """
    # Create Dash app with Bootstrap theme
    app = dash.Dash(
        __name__,
        requests_pathname_prefix=requests_pathname_prefix,
        external_stylesheets=[dbc.themes.SLATE],
        suppress_callback_exceptions=True,
        title="Investment-X Charts",
    )

    def serve_layout():
        """Generate layout dynamically on each page load."""
        # Import here to avoid import-time DB access
        from ix.db.conn import Session
        from ix.db.models import Chart

        # Fetch charts
        charts_by_cat = {}
        try:
            with Session() as s:
                charts = s.query(Chart).all()
                for chart in charts:
                    s.expunge(chart)
                    cat = chart.category or "Uncategorized"
                    if cat not in charts_by_cat:
                        charts_by_cat[cat] = []
                    charts_by_cat[cat].append(chart)

            # Sort charts within each category
            for cat in charts_by_cat:
                charts_by_cat[cat].sort(key=lambda c: c.code)
        except Exception as e:
            # If DB fails, show error
            return dbc.Container(
                [
                    html.H2("Investment-X", className="text-primary"),
                    dbc.Alert(f"Failed to load charts: {e}", color="danger"),
                ],
                className="py-3",
            )

        # Sort categories by order
        sorted_cats = sorted(
            charts_by_cat.keys(),
            key=lambda x: (
                CATEGORY_ORDER.index(x) if x in CATEGORY_ORDER else len(CATEGORY_ORDER)
            ),
        )

        # Build content
        content = []

        # Header
        content.append(
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2("Investment-X", className="text-primary mb-0"),
                            html.P("Research Library", className="text-muted"),
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            # PDF Download button
                            html.A(
                                dbc.Button(
                                    "📥 Download PDF",
                                    color="info",
                                    size="sm",
                                    className="me-3",
                                ),
                                href="/api/charts/export/pdf",
                                target="_blank",
                            ),
                            # Category quick links
                            html.Span(
                                [
                                    html.A(
                                        cat,
                                        href=f"#{cat.lower().replace(' ', '-')}",
                                        className="badge bg-secondary me-1 text-decoration-none",
                                    )
                                    for cat in sorted_cats
                                ]
                            ),
                        ],
                        width=6,
                        className="text-end",
                    ),
                ],
                className="py-3 border-bottom mb-4 sticky-top bg-dark align-items-center",
            )
        )

        # Charts by category
        for cat in sorted_cats:
            charts = charts_by_cat[cat]
            anchor = cat.lower().replace(" ", "-")

            # Category header
            content.append(
                html.H3(
                    cat,
                    id=anchor,
                    className="mt-4 mb-3 pb-2 border-bottom text-info",
                )
            )

            # Chart cards
            for chart in charts:
                last_updated = (
                    chart.updated_at.strftime("%Y-%m-%d %H:%M")
                    if chart.updated_at
                    else "Never"
                )

                content.append(
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            [
                                                html.H5(
                                                    chart.code,
                                                    className="mb-0 text-white",
                                                    style={"fontWeight": "600"},
                                                ),
                                                html.Small(
                                                    f"Last updated: {last_updated}",
                                                    className="text-muted",
                                                    style={"fontSize": "0.75rem"},
                                                ),
                                            ],
                                            width=9,
                                        ),
                                        dbc.Col(
                                            [
                                                dbc.Button(
                                                    "🔄",
                                                    id={
                                                        "type": "refresh-btn",
                                                        "code": chart.code,
                                                    },
                                                    color="light",
                                                    outline=True,
                                                    size="sm",
                                                    className="me-2 border-0",
                                                    title="Refresh chart data",
                                                ),
                                                dbc.Button(
                                                    "📋",
                                                    id={
                                                        "type": "copy-btn",
                                                        "code": chart.code,
                                                    },
                                                    color="light",
                                                    outline=True,
                                                    size="sm",
                                                    className="border-0",
                                                    title="Copy chart to clipboard",
                                                ),
                                            ],
                                            width=3,
                                            className="text-end",
                                        ),
                                    ],
                                    align="center",
                                ),
                                className="bg-transparent border-bottom border-secondary",
                            ),
                            dbc.CardBody(
                                [
                                    # Description
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.Span("ℹ️ ", className="me-1"),
                                                    html.Span(
                                                        chart.description
                                                        or "No description available",
                                                        id={
                                                            "type": "desc-text",
                                                            "code": chart.code,
                                                        },
                                                        className="text-light small",
                                                    ),
                                                    dbc.Button(
                                                        "✎",
                                                        id={
                                                            "type": "edit-btn",
                                                            "code": chart.code,
                                                        },
                                                        color="link",
                                                        size="sm",
                                                        className="text-muted p-0 ms-2 text-decoration-none",
                                                        title="Edit description",
                                                    ),
                                                ],
                                                className="d-flex align-items-center mb-2 p-2 rounded",
                                                style={
                                                    "backgroundColor": "rgba(255,255,255,0.05)"
                                                },
                                            ),
                                            dbc.Collapse(
                                                dbc.Card(
                                                    dbc.CardBody(
                                                        [
                                                            dbc.Textarea(
                                                                id={
                                                                    "type": "desc-input",
                                                                    "code": chart.code,
                                                                },
                                                                value=chart.description
                                                                or "",
                                                                className="mb-2 bg-dark text-light border-secondary",
                                                                style={
                                                                    "height": "100px"
                                                                },
                                                            ),
                                                            dbc.ButtonGroup(
                                                                [
                                                                    dbc.Button(
                                                                        "Save",
                                                                        id={
                                                                            "type": "save-btn",
                                                                            "code": chart.code,
                                                                        },
                                                                        color="success",
                                                                        size="sm",
                                                                        outline=True,
                                                                    ),
                                                                    dbc.Button(
                                                                        "Cancel",
                                                                        id={
                                                                            "type": "cancel-btn",
                                                                            "code": chart.code,
                                                                        },
                                                                        color="secondary",
                                                                        size="sm",
                                                                        outline=True,
                                                                    ),
                                                                ],
                                                                size="sm",
                                                            ),
                                                            html.Div(
                                                                id={
                                                                    "type": "save-status",
                                                                    "code": chart.code,
                                                                },
                                                                className="mt-2",
                                                            ),
                                                        ]
                                                    ),
                                                    className="bg-transparent border-0",
                                                ),
                                                id={
                                                    "type": "desc-collapse",
                                                    "code": chart.code,
                                                },
                                                is_open=False,
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                    # Chart with loading spinner
                                    dcc.Loading(
                                        dcc.Graph(
                                            figure=go.Figure(),
                                            id={
                                                "type": "chart-graph",
                                                "code": chart.code,
                                            },
                                            responsive=True,
                                            style={
                                                "width": "100%",
                                                "minHeight": "500px",
                                            },
                                            config={
                                                "displayModeBar": "hover",
                                                "displaylogo": False,
                                                "responsive": True,
                                                "modeBarButtonsToRemove": [
                                                    "lasso2d",
                                                    "select2d",
                                                ],
                                            },
                                        ),
                                        type="circle",
                                        color="#0dcaf0",  # Info cyan color
                                    ),
                                ]
                            ),
                        ],
                        className="mb-5 shadow-sm border-secondary",
                        style={
                            "backgroundColor": "#1e2126",  # Slightly lighter than main bg
                            "borderRadius": "10px",
                            "overflow": "hidden",
                        },
                    )
                )

        return dbc.Container(
            [
                dcc.Store(id="charts-loaded", data=[]),
                dcc.Interval(id="load-trigger", interval=100, max_intervals=1),
                *content,
            ],
            fluid=True,
            className="py-3",
            style={"maxWidth": "800px", "margin": "0 auto"},
        )

    # Use function-based layout for lazy loading
    app.layout = serve_layout

    # Callback to load all charts on initial load
    @app.callback(
        Output({"type": "chart-graph", "code": ALL}, "figure"),
        Input("load-trigger", "n_intervals"),
        prevent_initial_call=False,
    )
    def load_all_charts(_):
        """Load all charts when the page loads."""
        from ix.db.conn import Session
        from ix.db.models import Chart

        charts_by_cat = {}
        try:
            with Session() as s:
                charts = s.query(Chart).all()
                for chart in charts:
                    s.expunge(chart)
                    cat = chart.category or "Uncategorized"
                    if cat not in charts_by_cat:
                        charts_by_cat[cat] = []
                    charts_by_cat[cat].append(chart)
        except Exception:
            return []

        # Sort charts in the same order as layout
        sorted_cats = sorted(
            charts_by_cat.keys(),
            key=lambda x: (
                CATEGORY_ORDER.index(x) if x in CATEGORY_ORDER else len(CATEGORY_ORDER)
            ),
        )

        figures = []
        for cat in sorted_cats:
            chart_list = sorted(charts_by_cat[cat], key=lambda c: c.code)
            for chart in chart_list:
                try:
                    if chart.figure:
                        fig = go.Figure(chart.figure)
                        fig.update_layout(autosize=True, height=None, width=None)
                        figures.append(fig)
                    else:
                        fig = go.Figure()
                        fig.add_annotation(
                            text="No figure data",
                            xref="paper",
                            yref="paper",
                            x=0.5,
                            y=0.5,
                            showarrow=False,
                        )
                        figures.append(fig)
                except Exception as e:
                    fig = go.Figure()
                    fig.add_annotation(
                        text=f"Error: {str(e)[:50]}",
                        xref="paper",
                        yref="paper",
                        x=0.5,
                        y=0.5,
                        showarrow=False,
                        font=dict(color="red"),
                    )
                    figures.append(fig)

        return figures

    # Callback to toggle description editor
    @app.callback(
        Output({"type": "desc-collapse", "code": MATCH}, "is_open"),
        Input({"type": "edit-btn", "code": MATCH}, "n_clicks"),
        Input({"type": "cancel-btn", "code": MATCH}, "n_clicks"),
        State({"type": "desc-collapse", "code": MATCH}, "is_open"),
        prevent_initial_call=True,
    )
    def toggle_description_editor(edit_clicks, cancel_clicks, is_open):
        return not is_open

    # Callback to save description
    @app.callback(
        Output({"type": "desc-text", "code": MATCH}, "children"),
        Output({"type": "save-status", "code": MATCH}, "children"),
        Input({"type": "save-btn", "code": MATCH}, "n_clicks"),
        State({"type": "desc-input", "code": MATCH}, "value"),
        State({"type": "save-btn", "code": MATCH}, "id"),
        prevent_initial_call=True,
    )
    def save_description(n_clicks, description, btn_id):
        from ix.db.conn import Session
        from ix.db.models import Chart

        if n_clicks:
            code = btn_id["code"]
            with Session() as s:
                chart = s.query(Chart).filter(Chart.code == code).first()
                if chart:
                    chart.description = description
                    return (
                        description or "No description",
                        dbc.Alert("Saved!", color="success", duration=2000),
                    )
        return dash.no_update, dbc.Alert("Error", color="danger")

    # Callback to refresh individual chart
    @app.callback(
        Output({"type": "chart-graph", "code": MATCH}, "figure", allow_duplicate=True),
        Input({"type": "refresh-btn", "code": MATCH}, "n_clicks"),
        State({"type": "refresh-btn", "code": MATCH}, "id"),
        prevent_initial_call=True,
    )
    def refresh_chart(n_clicks, btn_id):
        from ix.db.conn import Session
        from ix.db.models import Chart

        if not n_clicks:
            return dash.no_update

        code = btn_id["code"]
        with Session() as s:
            chart = s.query(Chart).filter(Chart.code == code).first()
            if chart:
                try:
                    # Re-render and update the cached figure
                    chart.update_figure()

                    # Ensure the object is marked as dirty in the session
                    s.add(chart)

                    # Explicit commit to persist changes
                    s.commit()

                    # Return the updated figure
                    fig = chart.render()
                    fig.update_layout(autosize=True, height=None, width=None)
                    return fig
                except Exception as e:
                    s.rollback()
                    fig = go.Figure()
                    fig.add_annotation(
                        text=f"Error: {str(e)}",
                        xref="paper",
                        yref="paper",
                        x=0.5,
                        y=0.5,
                        showarrow=False,
                        font=dict(color="red", size=14),
                    )
                    return fig
        return dash.no_update

    # Clientside callback to copy chart to clipboard
    app.clientside_callback(
        """
        function(n_clicks, figure) {
            if (!n_clicks || !figure) return window.dash_clientside.no_update;
            
            const triggeredId = window.dash_clientside.callback_context.triggered[0];
            if (!triggeredId) return window.dash_clientside.no_update;
            const btnIdParsed = JSON.parse(triggeredId.prop_id.split('.')[0]);
            const chartCode = btnIdParsed.code;
            
            const tempDiv = document.createElement('div');
            tempDiv.style.position = 'absolute';
            tempDiv.style.left = '-9999px';
            tempDiv.style.width = '1200px';
            tempDiv.style.height = '700px';
            document.body.appendChild(tempDiv);
            
            Plotly.newPlot(tempDiv, figure.data, figure.layout, {staticPlot: true})
                .then(() => {
                    return Plotly.toImage(tempDiv, {format: 'png', width: 1200, height: 700, scale: 2});
                })
                .then(dataUrl => {
                    return fetch(dataUrl);
                })
                .then(res => res.blob())
                .then(blob => {
                    const item = new ClipboardItem({'image/png': blob});
                    return navigator.clipboard.write([item]);
                })
                .then(() => {
                    const allBtns = document.querySelectorAll('button');
                    allBtns.forEach(btn => {
                        if (btn.id && btn.id.includes(chartCode) && btn.id.includes('copy-btn')) {
                            const original = btn.textContent;
                            btn.textContent = '✅';
                            setTimeout(() => { btn.textContent = original; }, 1500);
                        }
                    });
                })
                .catch(err => {
                    console.error('Copy failed:', err);
                    alert('Failed to copy chart: ' + err.message);
                })
                .finally(() => {
                    document.body.removeChild(tempDiv);
                });
            
            return window.dash_clientside.no_update;
        }
        """,
        Output({"type": "copy-btn", "code": MATCH}, "n_clicks"),
        Input({"type": "copy-btn", "code": MATCH}, "n_clicks"),
        State({"type": "chart-graph", "code": MATCH}, "figure"),
        prevent_initial_call=True,
    )

    return app


# Create app instance for mounting
dash_app = create_dash_app()
