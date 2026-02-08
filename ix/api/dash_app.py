"""
Dash application for Investment-X charts.

This module creates a Dash app that can be mounted to FastAPI.
Displays all charts in a gallery view organized by category.
Uses callbacks for lazy loading of charts.
"""

import dash
from dash import html, dcc, callback, Input, Output, State, MATCH, ALL, ctx
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from ix.db.conn import Session
from ix.db.models import Chart


def get_charts_by_category():
    """Fetch all charts from DB grouped by category."""
    charts_by_cat = {}
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

    return charts_by_cat


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

    Args:
        requests_pathname_prefix: URL prefix for the Dash app

    Returns:
        Configured Dash application instance
    """

    # Create Dash app with Bootstrap theme
    app = dash.Dash(
        __name__,
        requests_pathname_prefix=requests_pathname_prefix,
        external_stylesheets=[dbc.themes.SLATE],
        suppress_callback_exceptions=True,
        title="Investment-X Charts",
    )

    # Fetch chart metadata (not figures)
    charts_by_cat = get_charts_by_category()

    # Sort categories by order
    sorted_cats = sorted(
        charts_by_cat.keys(),
        key=lambda x: (
            CATEGORY_ORDER.index(x) if x in CATEGORY_ORDER else len(CATEGORY_ORDER)
        ),
    )

    # Build content with placeholders
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

    # Charts by category - create placeholders
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

        # Chart placeholders
        for chart in charts:
            content.append(
                dbc.Card(
                    [
                        dbc.CardHeader(
                            dbc.Row(
                                [
                                    dbc.Col(
                                        html.H5(
                                            chart.code, className="mb-0 text-light"
                                        ),
                                        width=10,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                "🔄",
                                                id={
                                                    "type": "refresh-btn",
                                                    "code": chart.code,
                                                },
                                                color="link",
                                                size="sm",
                                                className="text-light p-0 me-2",
                                                title="Refresh chart",
                                            ),
                                            dbc.Button(
                                                "📋",
                                                id={
                                                    "type": "copy-btn",
                                                    "code": chart.code,
                                                },
                                                color="link",
                                                size="sm",
                                                className="text-light p-0",
                                                title="Copy to clipboard",
                                            ),
                                        ],
                                        width=2,
                                        className="text-end",
                                    ),
                                ],
                                align="center",
                            ),
                        ),
                        dbc.CardBody(
                            [
                                # Description display and editor
                                html.Div(
                                    [
                                        html.P(
                                            chart.description or "No description",
                                            id={
                                                "type": "desc-text",
                                                "code": chart.code,
                                            },
                                            className="text-muted small mb-2",
                                        ),
                                        dbc.Button(
                                            "✏️ Edit",
                                            id={"type": "edit-btn", "code": chart.code},
                                            color="link",
                                            size="sm",
                                            className="p-0 mb-2",
                                        ),
                                    ]
                                ),
                                # Edit modal
                                dbc.Collapse(
                                    dbc.Card(
                                        [
                                            dbc.CardBody(
                                                [
                                                    dbc.Textarea(
                                                        id={
                                                            "type": "desc-input",
                                                            "code": chart.code,
                                                        },
                                                        value=chart.description or "",
                                                        placeholder="Enter description...",
                                                        style={"height": "80px"},
                                                        className="mb-2",
                                                    ),
                                                    dbc.ButtonGroup(
                                                        [
                                                            dbc.Button(
                                                                "💾 Save",
                                                                id={
                                                                    "type": "save-btn",
                                                                    "code": chart.code,
                                                                },
                                                                color="primary",
                                                                size="sm",
                                                            ),
                                                            dbc.Button(
                                                                "Cancel",
                                                                id={
                                                                    "type": "cancel-btn",
                                                                    "code": chart.code,
                                                                },
                                                                color="secondary",
                                                                size="sm",
                                                            ),
                                                        ]
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
                                        ],
                                        className="bg-secondary",
                                    ),
                                    id={"type": "edit-collapse", "code": chart.code},
                                    is_open=False,
                                    className="mb-2",
                                ),
                                # Chart
                                dcc.Loading(
                                    dcc.Graph(
                                        id={"type": "chart-graph", "code": chart.code},
                                        responsive=True,
                                        style={"width": "100%", "minHeight": "500px"},
                                        config={
                                            "displayModeBar": True,
                                            "displaylogo": False,
                                            "responsive": True,
                                        },
                                    ),
                                    type="circle",
                                    color="#17a2b8",
                                ),
                            ]
                        ),
                    ],
                    className="mb-4 bg-dark border-secondary",
                )
            )

    # Layout
    app.layout = dbc.Container(
        [
            dcc.Store(id="charts-loaded", data=[]),
            dcc.Interval(id="load-trigger", interval=100, max_intervals=1),
            *content,
        ],
        fluid=True,
        className="py-3",
        style={"maxWidth": "800px", "margin": "0 auto"},
    )

    # Callback to load all charts on initial load
    @app.callback(
        Output({"type": "chart-graph", "code": ALL}, "figure"),
        Input("load-trigger", "n_intervals"),
        prevent_initial_call=False,
    )
    def load_all_charts(_):
        """Load all charts when the page loads."""
        charts_by_cat = get_charts_by_category()

        # Build ordered list of chart codes
        all_codes = []
        for cat in sorted_cats:
            if cat in charts_by_cat:
                for chart in charts_by_cat[cat]:
                    all_codes.append(chart.code)

        figures = []
        with Session() as s:
            for code in all_codes:
                chart = s.query(Chart).filter(Chart.code == code).first()
                if chart:
                    try:
                        fig = chart.render()
                        fig.update_layout(autosize=True, height=None, width=None)
                        figures.append(fig)
                    except Exception as e:
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
                        figures.append(fig)
                else:
                    figures.append(go.Figure())

        return figures

    # Callback to toggle edit collapse
    @app.callback(
        Output({"type": "edit-collapse", "code": MATCH}, "is_open"),
        Input({"type": "edit-btn", "code": MATCH}, "n_clicks"),
        Input({"type": "cancel-btn", "code": MATCH}, "n_clicks"),
        Input({"type": "save-btn", "code": MATCH}, "n_clicks"),
        State({"type": "edit-collapse", "code": MATCH}, "is_open"),
        prevent_initial_call=True,
    )
    def toggle_edit(edit_clicks, cancel_clicks, save_clicks, is_open):
        triggered = ctx.triggered_id
        if triggered and triggered.get("type") == "edit-btn":
            return not is_open
        return False

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
        if not n_clicks:
            return dash.no_update, dash.no_update

        code = btn_id["code"]
        with Session() as s:
            chart = s.query(Chart).filter(Chart.code == code).first()
            if chart:
                chart.description = description
                s.commit()
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
        if not n_clicks:
            return dash.no_update

        code = btn_id["code"]
        with Session() as s:
            chart = s.query(Chart).filter(Chart.code == code).first()
            if chart:
                try:
                    # Re-render chart and update cached figure in database
                    # update_figure now handles flag_modified and timestamp internally
                    chart.update_figure()
                    s.flush()
                    # Session context manager will commit on exit

                    # Return the freshly rendered figure
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
            
            // Get the chart code for visual feedback
            const triggeredId = window.dash_clientside.callback_context.triggered[0];
            if (!triggeredId) return window.dash_clientside.no_update;
            const btnIdParsed = JSON.parse(triggeredId.prop_id.split('.')[0]);
            const chartCode = btnIdParsed.code;
            
            // Create a temporary div for rendering
            const tempDiv = document.createElement('div');
            tempDiv.style.position = 'absolute';
            tempDiv.style.left = '-9999px';
            tempDiv.style.width = '1200px';
            tempDiv.style.height = '700px';
            document.body.appendChild(tempDiv);
            
            // Create the plot from figure data
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
                    // Visual feedback
                    const btnId = JSON.stringify({"type": "copy-btn", "code": chartCode});
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
                    // Clean up temp div
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
