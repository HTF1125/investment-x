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
from sqlalchemy.orm import load_only
from sqlalchemy import func
from datetime import datetime, timedelta

# Global caches for permanent storage until database update
# Gallery Metadata Cache: stores (max_updated_at, charts_by_cat, sorted_cats)
_GALLERY_CACHE = {"max_ts": None, "charts_by_cat": None, "sorted_cats": None}

# Individual Figure Cache: maps code -> {"ts": updated_at, "fig": go.Figure}
_FIGURE_CACHE = {}

# Keep TTL news cache as it's not the main bottleneck and doesn't have updated_at
from cachetools import TTLCache, cached

news_cache = TTLCache(maxsize=1, ttl=300)


# Define category order
CATEGORY_ORDER = [
    "Performance",
    "RRG",
    "Positions",
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


def create_dash_app(requests_pathname_prefix: str = "/") -> dash.Dash:
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

        # 1. Fetch Master Version (MAX updated_at)
        try:
            with Session() as s:
                db_max_ts = s.query(func.max(Chart.updated_at)).scalar()

            # If nothing changed, use cache
            if db_max_ts and _GALLERY_CACHE["max_ts"] == db_max_ts:
                charts_by_cat = _GALLERY_CACHE["charts_by_cat"]
                sorted_cats = _GALLERY_CACHE["sorted_cats"]
            else:
                # Rebuild cache
                charts_by_cat = {}
                with Session() as s:
                    charts = (
                        s.query(Chart)
                        .options(
                            load_only(
                                Chart.code,
                                Chart.category,
                                Chart.description,
                                Chart.updated_at,
                            )
                        )
                        .all()
                    )

                for chart in charts:
                    cat = chart.category or "Uncategorized"
                    if cat not in charts_by_cat:
                        charts_by_cat[cat] = []
                    charts_by_cat[cat].append(chart)

                # Sort categories by order
                sorted_cats = sorted(
                    charts_by_cat.keys(),
                    key=lambda x: (
                        CATEGORY_ORDER.index(x)
                        if x in CATEGORY_ORDER
                        else len(CATEGORY_ORDER)
                    ),
                )

                # Update global cache
                _GALLERY_CACHE["max_ts"] = db_max_ts
                _GALLERY_CACHE["charts_by_cat"] = charts_by_cat
                _GALLERY_CACHE["sorted_cats"] = sorted_cats

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
                                    className="me-2",
                                ),
                                href="/api/charts/export/pdf",
                                target="_blank",
                            ),
                            # Refresh All button
                            dbc.Button(
                                "🔄 Refresh All",
                                id="refresh-all-btn",
                                color="warning",
                                size="sm",
                                className="me-3",
                            ),
                            dbc.Tooltip(
                                "Trigger a full background refresh of all chart data",
                                target="refresh-all-btn",
                            ),
                            html.Div(
                                id="refresh-all-status", className="d-inline-block"
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

        # Recent Telegram Messages (Last 24h)
        from datetime import datetime, timedelta
        from ix.db.models import TelegramMessage

        try:

            @cached(news_cache)
            def get_recent_news():
                # Current KST = UTC + 9
                now_utc = datetime.utcnow()
                since_date = now_utc + timedelta(hours=9) - timedelta(hours=24)
                with Session() as s:
                    return (
                        s.query(TelegramMessage)
                        .filter(TelegramMessage.date >= since_date)
                        .order_by(TelegramMessage.date.desc())
                        .limit(50)
                        .all()
                    )

            recent_msgs = get_recent_news()

            if recent_msgs:
                msg_rows = []
                for msg in recent_msgs:
                    dt_str = msg.date.strftime("%Y-%m-%d %H:%M") if msg.date else ""
                    msg_rows.append(
                        html.Tr(
                            [
                                html.Td(
                                    dt_str,
                                    className="text-muted small",
                                    style={"whiteSpace": "nowrap"},
                                ),
                                html.Td(msg.channel_name, className="fw-bold small"),
                                html.Td(
                                    msg.message,
                                    style={
                                        "whiteSpace": "pre-wrap",
                                        "wordBreak": "break-word",
                                        "fontSize": "0.9rem",
                                    },
                                ),
                            ]
                        )
                    )

                content.append(
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                html.H5(
                                    "Recent Telegram News (24h)",
                                    className="mb-0 text-white",
                                ),
                                className="bg-primary text-white",
                            ),
                            dbc.CardBody(
                                dbc.Table(
                                    [
                                        html.Thead(
                                            html.Tr(
                                                [
                                                    html.Th("Date (KST)"),
                                                    html.Th("Channel"),
                                                    html.Th("Message"),
                                                ]
                                            )
                                        ),
                                        html.Tbody(msg_rows),
                                    ],
                                    bordered=True,
                                    hover=True,
                                    responsive=True,
                                    striped=True,
                                    color="dark",  # Matches the slate theme better
                                    className="mb-0",
                                ),
                                style={"maxHeight": "400px", "overflowY": "auto"},
                            ),
                        ],
                        className="mb-4 shadow-sm border-primary",
                    )
                )

        except Exception as e:
            content.append(
                dbc.Alert(
                    f"Failed to load recent messages: {str(e)}",
                    color="warning",
                    className="mb-4",
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
                                                    dcc.Markdown(
                                                        chart.description
                                                        or "No description available",
                                                        id={
                                                            "type": "desc-text",
                                                            "code": chart.code,
                                                        },
                                                        className="text-light small flex-grow-1",
                                                        style={"marginBottom": "0"},
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
                                        [
                                            dcc.Interval(
                                                id={
                                                    "type": "load-interval",
                                                    "code": chart.code,
                                                },
                                                interval=100,
                                                max_intervals=1,
                                            ),
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
                                        ],
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
                *content,
            ],
            fluid=True,
            className="py-3",
            style={"maxWidth": "800px", "margin": "0 auto"},
        )

    # Use function-based layout for lazy loading
    app.layout = serve_layout

    # Callback to load single chart
    @app.callback(
        Output({"type": "chart-graph", "code": MATCH}, "figure"),
        Input({"type": "load-interval", "code": MATCH}, "n_intervals"),
        State({"type": "load-interval", "code": MATCH}, "id"),
    )
    def load_single_chart(n, interval_id):
        """Load a single chart."""
        if not n:
            return dash.no_update

        code = interval_id["code"]
        from ix.db.conn import Session
        from ix.db.models import Chart

        try:
            with Session() as s:
                # Check timestamp first
                chart_meta = (
                    s.query(Chart)
                    .options(load_only(Chart.updated_at))
                    .filter(Chart.code == code)
                    .first()
                )
                if not chart_meta:
                    return dash.no_update

                # If cached and ts matches, return cached figure
                if (
                    code in _FIGURE_CACHE
                    and _FIGURE_CACHE[code]["ts"] == chart_meta.updated_at
                ):
                    return _FIGURE_CACHE[code]["fig"]

                # Otherwise, fetch the full figure
                chart = s.query(Chart).filter(Chart.code == code).first()
                if chart and chart.figure:
                    # Reuse dict directly if possible, or convert to Figure
                    if isinstance(chart.figure, str):
                        import json

                        fig_dict = json.loads(chart.figure)
                    else:
                        fig_dict = chart.figure

                    fig = go.Figure(fig_dict)
                    fig.update_layout(autosize=True, height=None, width=None)

                    # Store in cache
                    _FIGURE_CACHE[code] = {"ts": chart.updated_at, "fig": fig}
                    return fig
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
                    return fig
        except Exception as e:
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error: {str(e)[:100]}",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(color="red"),
            )
            return fig

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

    # Callback to trigger background refresh of all charts
    @app.callback(
        Output("refresh-all-status", "children"),
        Input("refresh-all-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def trigger_refresh_all(n_clicks):
        import threading
        from ix.misc.task import refresh_all_charts

        if n_clicks:
            # Run in a background thread to avoid blocking Dash
            threading.Thread(target=refresh_all_charts, daemon=True).start()
            return dbc.Alert(
                "Full refresh started in background...",
                color="info",
                duration=3000,
                className="ms-2 mb-0 py-1 px-2 small",
            )
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
