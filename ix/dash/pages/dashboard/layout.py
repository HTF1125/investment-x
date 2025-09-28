import pandas as pd
from dash import html, dcc, callback, Output, Input, State, clientside_callback
import dash
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
import traceback
from datetime import datetime
from functools import lru_cache

from ix.db import Universe
from ix.misc.date import today, oneyearbefore
from ix.dash.components import Grid, Card
from ix.misc import get_logger

logger = get_logger(__name__)

# Register Page
dash.register_page(__name__, path="/", title="Dashboard", name="Dashboard")


# --- Cached Data Loader ---
@lru_cache(maxsize=32)
def get_cached_universe_data(universe_name: str, start_date: str, end_date: str):
    """Cache universe data to improve performance"""
    try:
        universe_db = Universe.from_name(universe_name)
        pxs = universe_db.get_series(field="PX_LAST")
        return pxs.loc[start_date:end_date]
    except Exception as e:
        logger.error(f"Error loading {universe_name}: {e}")
        return pd.DataFrame()


# --- Heatmap Generator ---
def performance_heatmap(pxs: pd.DataFrame, periods: list = [1, 5, 21], title: str = ""):
    """Generate performance heatmap for given price data"""
    if pxs.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=16, color="#ef4444")
        )
        fig.update_layout(
            title=dict(text=title, x=0.5, xanchor="center", font=dict(size=16, color="#f1f5f9")),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=0, r=0, t=40, b=0),
            height=350
        )
        return fig

    # Calculate performance metrics
    performance_data = {}
    latest_values = pxs.resample("B").last().ffill().iloc[-1]
    performance_data["Latest"] = latest_values

    for p in periods:
        pct = pxs.resample("B").last().ffill().pct_change(p).ffill().iloc[-1]
        performance_data[f"{p}D"] = pct

    perf_df = pd.DataFrame(performance_data)
    perf_matrix = perf_df.copy()

    # Convert percentages to display format
    for col in perf_df.columns:
        if col != "Latest":
            perf_matrix[col] = perf_df[col] * 100

    z_values = perf_matrix.values.copy()
    z_colors = perf_matrix.values.copy()
    z_colors[:, 0] = 0  # Neutral color for latest values

    fig = go.Figure(
        data=go.Heatmap(
            z=z_colors,
            x=perf_matrix.columns,
            y=perf_df.index,
            colorscale=[
                [0, "#374151"], [0.4, "#dc2626"], [0.5, "#374151"],
                [0.6, "#059669"], [1, "#059669"]
            ],
            zmid=0,
            text=[[
                f"{val:.2f}" if col == "Latest" else f"{val:.1f}%"
                for col, val in zip(perf_matrix.columns, row)
            ] for row in z_values],
            texttemplate="%{text}",
            textfont=dict(size=12, color="white"),
            hovertemplate="<b>%{y}</b><br>%{x}: %{text}<extra></extra>",
            showscale=False
        )
    )

    # Add grid lines
    nrows, ncols = perf_matrix.shape
    for i in range(nrows):
        for j in range(ncols):
            fig.add_shape(
                type="rect",
                x0=j-0.5, x1=j+0.5, y0=i-0.5, y1=i+0.5,
                line=dict(color="white", width=1),
                layer="above"
            )

    fig.update_layout(
        title=dict(
            text=title,
            x=0.5,
            xanchor="center",
            font=dict(size=16, color="#f1f5f9")
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            tickfont=dict(size=12, color="#f1f5f9"),
            side="top",
            showgrid=False
        ),
        yaxis=dict(
            tickfont=dict(size=12, color="#f1f5f9"),
            autorange="reversed",
            showgrid=False
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        height=350
    )
    return fig


# --- UI Helper Functions ---
def create_chart_skeleton(title="Loading chart..."):
    """Create a skeleton loader that matches the actual chart layout"""
    return html.Div([
        # Chart title skeleton
        html.Div(
            title,
            style={
                "color": "#f1f5f9",
                "fontSize": "16px",
                "fontWeight": "600",
                "textAlign": "center",
                "marginBottom": "20px",
                "padding": "0 10px",
            }
        ),
        # Heatmap grid skeleton
        html.Div([
            # Header row (periods)
            html.Div([
                html.Div(style={
                    "background": "linear-gradient(90deg, rgba(100, 116, 139, 0.3) 25%, rgba(148, 163, 184, 0.4) 50%, rgba(100, 116, 139, 0.3) 75%)",
                    "backgroundSize": "200% 100%",
                    "animation": "pulse 2s ease-in-out infinite",
                    "height": "25px",
                    "borderRadius": "4px",
                    "margin": "2px",
                    "animationDelay": f"{i * 0.1}s"
                }) for i in range(7)
            ], style={
                "display": "grid",
                "gridTemplateColumns": "repeat(7, 1fr)",
                "gap": "4px",
                "marginBottom": "8px",
                "padding": "0 10px"
            }),
            # Data rows
            html.Div([
                html.Div([
                    html.Div(style={
                        "background": "linear-gradient(90deg, rgba(30, 41, 59, 0.4) 25%, rgba(51, 65, 85, 0.6) 50%, rgba(30, 41, 59, 0.4) 75%)",
                        "backgroundSize": "200% 100%",
                        "animation": "pulse 2s ease-in-out infinite",
                        "height": "35px",
                        "borderRadius": "4px",
                        "margin": "2px",
                        "animationDelay": f"{(row * 7 + col) * 0.05}s"
                    }) for col in range(7)
                ], style={
                    "display": "grid",
                    "gridTemplateColumns": "repeat(7, 1fr)",
                    "gap": "4px",
                    "marginBottom": "4px"
                }) for row in range(6)
            ], style={"padding": "0 10px"})
        ], style={
            "background": "rgba(30, 41, 59, 0.2)",
            "borderRadius": "8px",
            "padding": "20px 10px",
            "minHeight": "280px"
        })
    ], style={
        "padding": "1rem",
        "minHeight": "350px"
    })


def create_chart_error(error_message, error_id):
    """Create a compact error display for individual charts"""
    return html.Div(
        [
            html.Div(
                [
                    html.I(
                        className="fas fa-exclamation-triangle",
                        style={
                            "color": "#f59e0b",
                            "fontSize": "1.2rem",
                            "marginRight": "0.5rem",
                        },
                    ),
                    html.Span(
                        "Failed to load",
                        style={
                            "color": "#ef4444",
                            "fontSize": "0.9rem",
                            "fontWeight": "600",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "marginBottom": "1rem",
                },
            ),
            html.Details(
                [
                    html.Summary(
                        "View Details",
                        style={
                            "color": "#94a3b8",
                            "cursor": "pointer",
                            "fontSize": "0.8rem",
                            "textAlign": "center",
                            "marginBottom": "0.5rem",
                        },
                    ),
                    html.Pre(
                        error_message,
                        style={
                            "color": "#ef4444",
                            "fontSize": "0.7rem",
                            "background": "rgba(239, 68, 68, 0.1)",
                            "padding": "0.75rem",
                            "borderRadius": "6px",
                            "border": "1px solid rgba(239, 68, 68, 0.2)",
                            "overflow": "auto",
                            "maxHeight": "150px",
                        },
                    ),
                ]
            ),
            html.Button(
                [
                    html.I(
                        className="fas fa-sync-alt",
                        style={"marginRight": "0.25rem"}
                    ),
                    "Retry",
                ],
                id={"type": "retry-btn", "section": error_id},
                n_clicks=0,
                style={
                    "background": "linear-gradient(145deg, #3b82f6, #2563eb)",
                    "color": "white",
                    "border": "none",
                    "borderRadius": "6px",
                    "padding": "0.5rem 1rem",
                    "fontSize": "0.8rem",
                    "fontWeight": "600",
                    "cursor": "pointer",
                    "transition": "all 0.3s ease",
                    "marginTop": "0.75rem",
                    "display": "block",
                    "marginLeft": "auto",
                    "marginRight": "auto",
                },
            ),
        ],
        style={
            "padding": "1rem",
            "textAlign": "center",
            "background": "rgba(239, 68, 68, 0.05)",
            "borderRadius": "8px",
            "border": "1px solid rgba(239, 68, 68, 0.2)",
        },
    )


def create_section_skeleton(title, description, num_charts=6):
    """Create a consistent skeleton loader for dashboard sections with individual chart skeletons"""
    return html.Div(
        [
            html.Div(
                [
                    html.H2(
                        title,
                        style={
                            "color": "#f1f5f9",
                            "fontSize": "1.75rem",
                            "fontWeight": "700",
                            "marginBottom": "0.5rem",
                            "letterSpacing": "0.025em",
                        },
                    ),
                    html.P(
                        description,
                        style={
                            "color": "#94a3b8",
                            "fontSize": "1rem",
                            "margin": "0 0 1.5rem 0",
                        },
                    ),
                ]
            ),
            html.Div([
                create_chart_skeleton(f"Loading chart {i+1}...")
                for i in range(num_charts)
            ], style={
                "display": "grid",
                "gridTemplateColumns": "repeat(auto-fit, minmax(350px, 1fr))",
                "gap": "1.5rem",
            }),
        ],
        style={"marginBottom": "2rem"},
    )


def create_error_section(title, error_message, error_id):
    """Create a consistent error display for dashboard sections"""
    return html.Div(
        [
            html.Div(
                [
                    html.H2(
                        title,
                        style={
                            "color": "#f1f5f9",
                            "fontSize": "1.75rem",
                            "fontWeight": "700",
                            "marginBottom": "0.5rem",
                        },
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.I(
                                        className="fas fa-exclamation-triangle",
                                        style={
                                            "color": "#f59e0b",
                                            "fontSize": "1.5rem",
                                            "marginRight": "0.75rem",
                                        },
                                    ),
                                    html.Span(
                                        "Failed to load section",
                                        style={
                                            "color": "#ef4444",
                                            "fontSize": "1.1rem",
                                            "fontWeight": "600",
                                        },
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "marginBottom": "1rem",
                                },
                            ),
                            html.Details(
                                [
                                    html.Summary(
                                        "View Error Details",
                                        style={
                                            "color": "#94a3b8",
                                            "cursor": "pointer",
                                            "fontSize": "0.9rem",
                                            "marginBottom": "0.5rem",
                                        },
                                    ),
                                    html.Pre(
                                        error_message,
                                        style={
                                            "color": "#ef4444",
                                            "fontSize": "0.8rem",
                                            "background": "rgba(239, 68, 68, 0.1)",
                                            "padding": "1rem",
                                            "borderRadius": "8px",
                                            "border": "1px solid rgba(239, 68, 68, 0.2)",
                                            "overflow": "auto",
                                            "maxHeight": "200px",
                                        },
                                    ),
                                ]
                            ),
                            html.Button(
                                [
                                    html.I(
                                        className="fas fa-sync-alt",
                                        style={"marginRight": "0.5rem"},
                                    ),
                                    "Retry Loading",
                                ],
                                id={"type": "retry-btn", "section": error_id},
                                n_clicks=0,
                                style={
                                    "background": "linear-gradient(145deg, #3b82f6, #2563eb)",
                                    "color": "white",
                                    "border": "none",
                                    "borderRadius": "8px",
                                    "padding": "0.75rem 1.5rem",
                                    "fontSize": "0.9rem",
                                    "fontWeight": "600",
                                    "cursor": "pointer",
                                    "transition": "all 0.3s ease",
                                    "marginTop": "1rem",
                                },
                            ),
                        ],
                        style={
                            "padding": "1.5rem",
                            "background": "linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.9))",
                            "borderRadius": "16px",
                            "border": "1px solid rgba(239, 68, 68, 0.3)",
                        },
                    ),
                ]
            ),
        ],
        style={"marginBottom": "2rem"},
    )


# --- Section Builder ---
def PerformanceHeatmapSection(
    universes=["Major Indices", "Global Markets", "Sectors", "Themes", "Commodities", "Currencies"]
):
    """Build the performance heatmap section with individual chart containers using Grid and Card components"""

    # Create individual chart cards that will load separately
    chart_cards = []
    for i, universe in enumerate(universes):
        chart_cards.append(
            Card(
                html.Div(
                    id=f"chart-container-{i}",
                    children=create_chart_skeleton(f"Loading {universe}..."),
                )
            )
        )

    return html.Div([
        html.H2(
            "Performance Heatmaps",
            style={
                "color": "#f1f5f9",
                "fontSize": "1.75rem",
                "fontWeight": "700",
                "marginBottom": "1.5rem",
                "letterSpacing": "0.025em",
            },
        ),
        Grid(chart_cards)
    ])


# --- Layout ---
layout = html.Div(
    [
        # Stores for state management
        dcc.Store(id="dashboard-load-state", data={"loaded": False}),
        dcc.Store(id="last-refresh-time", data=None),

        # Auto-refresh interval (10 minutes)
        dcc.Interval(
            id="dashboard-refresh-interval",
            interval=10 * 60 * 1000,  # 10 minutes
            n_intervals=0,
            disabled=False,
        ),

        # Individual chart loading intervals - staggered timing
        html.Div([
            dcc.Interval(
                id=f"chart-load-interval-{i}",
                interval=1000 + (i * 500),  # Staggered: 1s, 1.5s, 2s, 2.5s, 3s, 3.5s
                n_intervals=0,
                max_intervals=1,
            ) for i in range(6)  # For 6 charts
        ]),

        # Page header with refresh controls
        html.Div(
            [
                html.Div(
                    [
                        html.H1(
                            "Investment Dashboard",
                            style={
                                "color": "#f1f5f9",
                                "fontSize": "2.5rem",
                                "fontWeight": "800",
                                "margin": "0",
                                "letterSpacing": "-0.025em",
                            },
                        ),
                        html.P(
                            "Real-time market performance and analytics",
                            style={
                                "color": "#94a3b8",
                                "fontSize": "1.1rem",
                                "margin": "0.5rem 0 0 0",
                            },
                        ),
                    ],
                    style={"flex": "1"},
                ),
                html.Div(
                    [
                        html.Div(
                            id="last-update-display",
                            style={
                                "color": "#64748b",
                                "fontSize": "0.9rem",
                                "marginBottom": "0.5rem",
                                "textAlign": "right",
                            },
                        ),
                        html.Button(
                            [
                                html.I(
                                    className="fas fa-sync-alt",
                                    style={"marginRight": "0.5rem"},
                                ),
                                "Refresh Now",
                            ],
                            id="manual-refresh-btn",
                            n_clicks=0,
                            style={
                                "background": "linear-gradient(145deg, #059669, #047857)",
                                "color": "white",
                                "border": "none",
                                "borderRadius": "8px",
                                "padding": "0.75rem 1.25rem",
                                "fontSize": "0.9rem",
                                "fontWeight": "600",
                                "cursor": "pointer",
                                "transition": "all 0.3s ease",
                            },
                        ),
                    ]
                ),
            ],
            style={
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "flex-end",
                "marginBottom": "2rem",
                "padding": "0 0.5rem",
            },
        ),

        # Dashboard content
        html.Div(
            [
                html.Div(
                    id="heatmap-section",
                    children=create_section_skeleton(
                        "Performance Heatmaps",
                        "Analyzing market performance across sectors...",
                    ),
                ),
            ],
            style={
                "display": "grid",
                "gap": "2rem",
                "gridTemplateColumns": "1fr",
            },
        ),
    ],
    style={
        "maxWidth": "1600px",
        "margin": "0 auto",
        "padding": "2rem",
        "backgroundColor": "transparent",
        "color": "#ffffff",
        "fontFamily": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    },
    className="dashboard-content",
)


# --- Callbacks ---
@callback(
    Output("heatmap-section", "children"),
    Output("dashboard-load-state", "data"),
    [
        Input("dashboard-refresh-interval", "n_intervals"),
        Input("manual-refresh-btn", "n_clicks"),
    ],
    State("dashboard-load-state", "data"),
    prevent_initial_call=False,
)
def load_heatmap_section(refresh_intervals, manual_refresh, load_state):
    """Load the heatmap section structure (containers only)"""

    try:
        logger.info(f"Loading heatmap section structure")

        # Load the section with empty containers that will be filled individually
        heatmap_content = PerformanceHeatmapSection()

        if heatmap_content is None:
            raise ValueError("PerformanceHeatmapSection() returned None")

        return heatmap_content, {"loaded": True}

    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"Error loading heatmap section: {error_trace}")

        return (create_error_section(
            "Performance Heatmaps",
            f"Error: {str(e)}\n\nFull traceback:\n{error_trace}",
            "heatmap",
        ), {"loaded": False, "error": True})


# Individual chart loading callbacks
universes = ["Major Indices", "Global Markets", "Sectors", "Themes", "Commodities", "Currencies"]
periods = [1, 5, 21, 63, 126, 252]

def create_individual_chart_callback(chart_index, universe_name):
    """Create a callback for loading an individual chart"""

    @callback(
        Output(f"chart-container-{chart_index}", "children"),
        Input(f"chart-load-interval-{chart_index}", "n_intervals"),
        prevent_initial_call=False,
    )
    def load_individual_chart(n_intervals):
        """Load individual chart data"""

        if n_intervals == 0:
            return create_chart_skeleton(f"Loading {universe_name}...")

        try:
            logger.info(f"Loading chart for {universe_name}")

            start_date = oneyearbefore().strftime("%Y-%m-%d")
            end_date = today().strftime("%Y-%m-%d")

            pxs = get_cached_universe_data(universe_name, start_date, end_date)

            if not pxs.empty:
                fig = performance_heatmap(pxs, periods, title=universe_name)
                return dcc.Graph(
                    figure=fig,
                    config={"displayModeBar": False},
                    style={"width": "100%", "height": "400px"}
                )
            else:
                return html.Div([
                    html.H4(universe_name, style={"color": "#f1f5f9", "marginBottom": "1rem", "textAlign": "center"}),
                    html.Div(
                        "No data available for this universe",
                        style={"color": "#ef4444", "textAlign": "center", "padding": "2rem"}
                    )
                ])

        except Exception as e:
            logger.error(f"Error loading chart for {universe_name}: {e}")
            return html.Div([
                html.H4(universe_name, style={"color": "#f1f5f9", "marginBottom": "1rem", "textAlign": "center"}),
                create_chart_error(f"Error loading {universe_name}: {str(e)}", f"chart-{chart_index}")
            ])

# Create callbacks for all charts
for i, universe in enumerate(universes):
    create_individual_chart_callback(i, universe)


# Callback to update last refresh time display
@callback(
    Output("last-update-display", "children"),
    [
        Input("dashboard-refresh-interval", "n_intervals"),
        Input("manual-refresh-btn", "n_clicks"),
    ] + [Input(f"chart-load-interval-{i}", "n_intervals") for i in range(6)],
    prevent_initial_call=True,
)
def update_last_refresh_time(*args):
    """Update the last refresh time display"""
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    current_time = datetime.now().strftime("%H:%M:%S")
    return f"Last updated: {current_time}"


# Clientside callback for button hover effects
clientside_callback(
    """
    function() {
        // Add hover effects for buttons when DOM is ready
        setTimeout(function() {
            const buttons = document.querySelectorAll('button');
            buttons.forEach(button => {
                if (button.id === 'manual-refresh-btn') {
                    button.addEventListener('mouseenter', function() {
                        this.style.transform = 'translateY(-2px) scale(1.02)';
                        this.style.boxShadow = '0 8px 25px rgba(5, 150, 105, 0.4)';
                    });
                    button.addEventListener('mouseleave', function() {
                        this.style.transform = 'translateY(0) scale(1)';
                        this.style.boxShadow = 'none';
                    });
                } else if (button.className && button.className.includes('retry')) {
                    button.addEventListener('mouseenter', function() {
                        this.style.transform = 'translateY(-1px) scale(1.01)';
                        this.style.boxShadow = '0 4px 15px rgba(59, 130, 246, 0.3)';
                    });
                    button.addEventListener('mouseleave', function() {
                        this.style.transform = 'translateY(0) scale(1)';
                        this.style.boxShadow = 'none';
                    });
                }
            });
        }, 100);
        return window.dash_clientside.no_update;
    }
    """,
    Output("last-refresh-time", "data"),  # Use a different output that's not used elsewhere
    Input("dashboard-load-state", "data"),
)
