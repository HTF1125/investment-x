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
    "Technical",
    "Uncategorized",
]


def apply_premium_style(fig: go.Figure) -> go.Figure:
    """Applies consistent premium styling to all charts while respecting theme."""
    # Default to dark for the premium Investment-X aesthetic
    is_dark = True
    bg = fig.layout.paper_bgcolor
    if bg and isinstance(bg, str):
        upper_bg = bg.upper()
        # Only switch to light if explicitly set to white/light
        if (
            upper_bg in ["WHITE", "#FFFFFF", "#F8FAFC"]
            or "RGBA(255, 255, 255" in upper_bg
        ):
            # Check if we should override it anyway (user feedback suggests they prefer dark)
            # For now, let's keep it flexible but lean towards dark
            pass

    # Force dark theme for now to resolve user visibility issues on white backgrounds
    is_dark = True

    # Theme-adaptive colors
    text_color = "#f8fafc" if is_dark else "#0f172a"
    accent_color = "rgba(255, 255, 255, 0.15)" if is_dark else "rgba(15, 23, 42, 0.1)"
    grid_color = "rgba(255, 255, 255, 0.06)" if is_dark else "rgba(0, 0, 0, 0.05)"

    fig.update_layout(
        template="plotly_dark" if is_dark else "plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=text_color, family="'Inter', sans-serif"),
        title_font=dict(color=text_color, family="'Outfit', sans-serif", size=18),
        legend=dict(
            font=dict(color=text_color, size=11),
            bgcolor="rgba(0,0,0,0)",
            bordercolor=accent_color,
            borderwidth=0,
        ),
        # Increased margins to prevent label clipping
        margin=dict(t=85, b=65, l=75, r=50),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#1e2126" if is_dark else "white",
            font_size=13,
            font_family="'Inter', sans-serif",
            font_color=text_color,
            bordercolor=accent_color,
        ),
    )

    # Force all axes to match the theme
    axis_config = dict(
        gridcolor=grid_color,
        zerolinecolor=accent_color,
        tickfont=dict(color=text_color, size=10),
        tickcolor=text_color,
        title_font=dict(color=text_color, size=12),
        linecolor=accent_color,
        showgrid=True,
    )

    fig.update_xaxes(**axis_config)
    fig.update_yaxes(**axis_config)

    # Ensure title is properly positioned
    if fig.layout.title and fig.layout.title.text:
        fig.update_layout(
            title=dict(
                x=0.03,
                y=0.96,
                xanchor="left",
                yanchor="top",
                font=dict(color=text_color, size=16),
            )
        )

    return fig


@cached(news_cache)
def get_recent_news():
    """Fetch recent news from database with caching."""
    from ix.db.conn import Session
    from ix.db.models import TelegramMessage
    from datetime import datetime, timedelta

    # Current KST = UTC + 9
    now_utc = datetime.utcnow()
    since_date = now_utc + timedelta(hours=9) - timedelta(hours=24)
    try:
        with Session() as s:
            return (
                s.query(TelegramMessage)
                .filter(TelegramMessage.date >= since_date)
                .order_by(TelegramMessage.date.desc())
                .limit(50)
                .all()
            )
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []


def create_dash_app(requests_pathname_prefix: str = "/") -> dash.Dash:
    """
    Creates and configures the Dash application.

    Uses function-based layout to defer database queries until page is accessed.
    """
    import os

    # Force absolute path for assets folder to ensure reliability in mounted FastAPI app
    assets_folder = os.path.join(os.path.dirname(__file__), "assets")

    # Create Dash app with Bootstrap theme and Icons
    app = dash.Dash(
        __name__,
        requests_pathname_prefix=requests_pathname_prefix,
        assets_folder=assets_folder,
        external_stylesheets=[
            dbc.themes.SLATE,
            "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css",
        ],
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
                    html.H2("Investment-X", className="text-gradient"),
                    dbc.Alert(
                        f"Failed to load charts: {e}", color="danger", className="mt-4"
                    ),
                ],
                className="py-5 text-center",
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
                            html.Div(
                                [
                                    html.Img(
                                        src=app.get_asset_url(
                                            "investment-x-logo-light.svg"
                                        ),
                                        style={"height": "28px"},
                                    ),
                                ],
                                className="d-flex align-items-center justify-content-center justify-content-md-start",
                            ),
                            html.P(
                                "Real-time Macro Intelligence & Research Library",
                                className="text-muted small mt-1",
                            ),
                        ],
                        md=6,
                        xs=12,
                        className="text-center text-md-start mb-3 mb-md-0",
                    ),
                    dbc.Col(
                        [
                            html.Div(
                                [
                                    # PDF Download button with loading state
                                    dcc.Loading(
                                        id="loading-pdf",
                                        children=[
                                            dbc.Button(
                                                [
                                                    html.I(
                                                        className="bi bi-file-earmark-pdf me-2"
                                                    ),
                                                    "Export PDF",
                                                ],
                                                id="pdf-download-btn",
                                                color="info",
                                                size="sm",
                                                className="px-3",
                                            ),
                                        ],
                                        type="circle",
                                        className="d-inline-block",
                                    ),
                                    dcc.Download(id="download-pdf-data"),
                                    # Refresh All button
                                    dbc.Button(
                                        [
                                            html.I(
                                                className="bi bi-arrow-clockwise me-2"
                                            ),
                                            "Refresh Data",
                                        ],
                                        id="refresh-all-btn",
                                        color="warning",
                                        size="sm",
                                        className="px-3",
                                    ),
                                    html.Div(
                                        id="refresh-all-status",
                                        className="d-inline-block",
                                    ),
                                    # Scrape Telegram button
                                    dbc.Button(
                                        [
                                            html.I(className="bi bi-telegram me-2"),
                                            "Scrape Telegram",
                                        ],
                                        id="scrape-telegram-btn",
                                        color="primary",
                                        size="sm",
                                        className="px-3",
                                    ),
                                    html.Div(
                                        id="scrape-telegram-status",
                                        className="d-inline-block",
                                    ),
                                ],
                                className="d-flex align-items-center justify-content-center justify-content-md-end gap-3",
                            ),
                            dbc.Tooltip(
                                "Trigger a full background refresh of all chart data",
                                target="refresh-all-btn",
                            ),
                            dbc.Tooltip(
                                "Scrape latest messages from Telegram channels",
                                target="scrape-telegram-btn",
                            ),
                        ],
                        md=6,
                        xs=12,
                        className="text-center text-md-end",
                    ),
                    dbc.Col(
                        [
                            # Category quick links
                            html.Div(
                                [
                                    html.A(
                                        cat,
                                        href=f"#{cat.lower().replace(' ', '-')}",
                                        className="badge bg-secondary me-2 mb-2 text-decoration-none",
                                    )
                                    for cat in sorted_cats
                                ],
                                className="mt-3 d-flex flex-wrap justify-content-center justify-content-md-end",
                            ),
                        ],
                        width=12,
                    ),
                ],
                className="py-4 px-3 sticky-top shadow-sm align-items-center",
            )
        )

        # Recent Telegram Messages (Last 24h)
        from datetime import datetime, timedelta
        from ix.db.models import TelegramMessage

        try:
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
                                    [
                                        html.I(className="bi bi-cpu me-2"),
                                        "Quant Intelligence Feed (24h)",
                                    ],
                                    className="mb-0 text-white fw-bold",
                                ),
                                className="bg-primary",
                            ),
                            dbc.CardBody(
                                dbc.Table(
                                    [
                                        html.Thead(
                                            html.Tr(
                                                [
                                                    html.Th("Timestamp"),
                                                    html.Th("Source"),
                                                    html.Th("Intelligence Content"),
                                                ]
                                            )
                                        ),
                                        html.Tbody(msg_rows),
                                    ],
                                    borderless=True,
                                    hover=False,
                                    responsive=True,
                                    striped=True,
                                    className="mb-0",
                                ),
                                style={
                                    "maxHeight": "350px",
                                    "overflowY": "auto",
                                    "padding": "0",
                                },
                            ),
                        ],
                        className="mb-5 shadow-lg border-primary border-opacity-25",
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

            # Chart cards container
            chart_cards = []
            for chart in charts:
                last_updated = (
                    chart.updated_at.strftime("%Y-%m-%d %H:%M")
                    if chart.updated_at
                    else "Never"
                )

                chart_cards.append(
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            [
                                                html.Small(
                                                    f"Updated: {last_updated}",
                                                    className="text-muted",
                                                ),
                                            ],
                                            width=8,
                                        ),
                                        dbc.Col(
                                            [
                                                dbc.Button(
                                                    html.I(
                                                        className="bi bi-arrow-repeat"
                                                    ),
                                                    id={
                                                        "type": "refresh-btn",
                                                        "code": chart.code,
                                                    },
                                                    color="secondary",
                                                    outline=True,
                                                    size="sm",
                                                    className="me-2 rounded-circle shadow-sm hover-lift",
                                                    title="Refresh chart data",
                                                ),
                                                dbc.Button(
                                                    html.I(
                                                        className="bi bi-clipboard-plus"
                                                    ),
                                                    id={
                                                        "type": "copy-btn",
                                                        "code": chart.code,
                                                    },
                                                    color="secondary",
                                                    outline=True,
                                                    size="sm",
                                                    className="rounded-circle shadow-sm hover-lift",
                                                    title="Copy chart to clipboard",
                                                ),
                                            ],
                                            width=4,
                                            className="text-end",
                                        ),
                                    ],
                                    align="center",
                                ),
                            ),
                            dbc.CardBody(
                                [
                                    # Lazy loading trigger (staggered to avoid connection storm)
                                    dcc.Interval(
                                        id={
                                            "type": "load-interval",
                                            "code": chart.code,
                                        },
                                        interval=300
                                        + (len(chart_cards) * 50),  # Staggered
                                        max_intervals=1,
                                    ),
                                    # Chart
                                    dcc.Loading(
                                        [
                                            dcc.Graph(
                                                figure=go.Figure(),
                                                id={
                                                    "type": "chart-graph",
                                                    "code": chart.code,
                                                },
                                                responsive=True,
                                                style={"minHeight": "450px"},
                                                config={
                                                    "displayModeBar": "hover",
                                                    "displaylogo": False,
                                                    "modeBarButtonsToRemove": [
                                                        "lasso2d",
                                                        "select2d",
                                                    ],
                                                },
                                            ),
                                        ],
                                        type="circle",
                                        color="#00f2fe",
                                    ),
                                    # Description (moved below chart)
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.Span("💡", className="me-2"),
                                                    dcc.Markdown(
                                                        chart.description
                                                        or "No analysis available for this chart.",
                                                        id={
                                                            "type": "desc-text",
                                                            "code": chart.code,
                                                        },
                                                        className="small flex-grow-1 mb-0",
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
                                                    ),
                                                ],
                                                className="description-box d-flex align-items-center mt-4",
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
                                                                    "height": "120px"
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
                                                                ],
                                                                className="w-100",
                                                            ),
                                                            html.Div(
                                                                id={
                                                                    "type": "save-status",
                                                                    "code": chart.code,
                                                                },
                                                                className="mt-2",
                                                            ),
                                                        ],
                                                        className="bg-dark p-2 border-0",
                                                    ),
                                                    className="mb-3",
                                                ),
                                                id={
                                                    "type": "desc-collapse",
                                                    "code": chart.code,
                                                },
                                                is_open=False,
                                            ),
                                        ],
                                    ),
                                ],
                                className="p-4",
                            ),
                        ],
                        className="h-100",
                    )
                )

            # Add categories and their charts in a grid
            content.append(html.Div(chart_cards, className="chart-grid mb-5"))

        return dbc.Container(
            [
                dcc.Store(id="charts-loaded", data=[]),
                html.Div(content, className="pb-5"),
            ],
            fluid=True,
            className="px-lg-5 px-md-3 px-2",
            style={"maxWidth": "1600px", "margin": "0 auto"},
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
                    fig = apply_premium_style(fig)

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
                    fig = apply_premium_style(fig)
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

    # Callback to trigger Telegram scraping
    @app.callback(
        Output("scrape-telegram-status", "children"),
        Input("scrape-telegram-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def trigger_scrape_telegram(n_clicks):
        import threading
        from ix.misc.telegram import run_scrape_all

        if n_clicks:
            # Run in a background thread to avoid blocking Dash
            threading.Thread(target=run_scrape_all, daemon=True).start()
            return dbc.Alert(
                "Telegram scraping started...",
                color="primary",
                duration=3000,
                className="ms-2 mb-0 py-1 px-2 small",
            )
        return dash.no_update

    # Callback to handle PDF export via server-side generation
    @app.callback(
        Output("download-pdf-data", "data"),
        Input("pdf-download-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def handle_pdf_download(n_clicks):
        if not n_clicks:
            return dash.no_update

        from ix.misc.scripts import export_charts_to_pdf
        from datetime import datetime

        # Generate PDF bytes
        try:
            pdf_bytes = export_charts_to_pdf(output_path=None)
            if not pdf_bytes:
                return dash.no_update

            filename = (
                f"Investment-X_Macro_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
            )

            return dcc.send_bytes(pdf_bytes, filename)
        except Exception as e:
            print(f"PDF Export Error in Dash: {e}")
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
                            const icon = btn.querySelector('i');
                            const originalClass = icon.className;
                            icon.className = 'bi bi-check-lg text-success';
                            setTimeout(() => { icon.className = originalClass; }, 1500);
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
