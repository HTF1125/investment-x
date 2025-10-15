"""
UI components module for dashboard.
Handles skeletons, error displays, layout helpers, and modern UI elements.
"""

from dash import html, dcc
from typing import List, Optional, Dict, Any
from dash_iconify import DashIconify


class SkeletonLoader:
    """Creates skeleton loading animations for dashboard components."""

    @staticmethod
    def create_chart_skeleton(title: str = "Loading chart...") -> html.Div:
        """Create a skeleton loader that matches the actual chart layout."""
        return html.Div(
            [
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
                    },
                ),
                # Heatmap grid skeleton
                html.Div(
                    [
                        # Header row (periods)
                        html.Div(
                            [
                                html.Div(
                                    style={
                                        "background": "linear-gradient(90deg, rgba(100, 116, 139, 0.3) 25%, rgba(148, 163, 184, 0.4) 50%, rgba(100, 116, 139, 0.3) 75%)",
                                        "backgroundSize": "200% 100%",
                                        "animation": "pulse 2s ease-in-out infinite",
                                        "height": "25px",
                                        "borderRadius": "4px",
                                        "margin": "2px",
                                        "animationDelay": f"{i * 0.1}s",
                                    }
                                )
                                for i in range(7)
                            ],
                            style={
                                "display": "grid",
                                "gridTemplateColumns": "repeat(7, 1fr)",
                                "gap": "4px",
                                "marginBottom": "8px",
                                "padding": "0 10px",
                            },
                        ),
                        # Data rows
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div(
                                            style={
                                                "background": "linear-gradient(90deg, rgba(30, 41, 59, 0.4) 25%, rgba(51, 65, 85, 0.6) 50%, rgba(30, 41, 59, 0.4) 75%)",
                                                "backgroundSize": "200% 100%",
                                                "animation": "pulse 2s ease-in-out infinite",
                                                "height": "35px",
                                                "borderRadius": "4px",
                                                "margin": "2px",
                                                "animationDelay": f"{(row * 7 + col) * 0.05}s",
                                            }
                                        )
                                        for col in range(7)
                                    ],
                                    style={
                                        "display": "grid",
                                        "gridTemplateColumns": "repeat(7, 1fr)",
                                        "gap": "4px",
                                        "marginBottom": "4px",
                                    },
                                )
                                for row in range(6)
                            ],
                            style={"padding": "0 10px"},
                        ),
                    ],
                    style={
                        "background": "rgba(30, 41, 59, 0.2)",
                        "borderRadius": "8px",
                        "padding": "20px 10px",
                        "minHeight": "280px",
                    },
                ),
            ],
            style={"padding": "1rem", "minHeight": "350px"},
        )

    @staticmethod
    def create_section_skeleton(
        title: str, description: str, num_charts: int = 6
    ) -> html.Div:
        """Create a consistent skeleton loader for dashboard sections with individual chart skeletons."""
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
                html.Div(
                    [
                        SkeletonLoader.create_chart_skeleton(f"Loading chart {i+1}...")
                        for i in range(num_charts)
                    ],
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "repeat(auto-fit, minmax(350px, 1fr))",
                        "gap": "1.5rem",
                    },
                ),
            ],
            style={"marginBottom": "2rem"},
        )


class ErrorDisplay:
    """Creates error display components for dashboard."""

    @staticmethod
    def create_chart_error(error_message: str, error_id: str) -> html.Div:
        """Create a compact error display for individual charts."""
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
                            style={"marginRight": "0.25rem"},
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

    @staticmethod
    def create_error_section(title: str, error_message: str, error_id: str) -> html.Div:
        """Create a consistent error display for dashboard sections."""
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


class ModernComponents:
    """Modern UI components for dashboard."""

    @staticmethod
    def create_stat_card(
        title: str,
        value: str,
        change: str = None,
        icon: str = "mdi:chart-line",
        trend: str = "up",
    ) -> html.Div:
        """Create a modern statistic card with glassmorphism design."""

        # Determine color based on trend
        if change:
            if trend == "up":
                change_color = "#10b981"
                icon_name = "mdi:trending-up"
            elif trend == "down":
                change_color = "#ef4444"
                icon_name = "mdi:trending-down"
            else:
                change_color = "#94a3b8"
                icon_name = "mdi:minus"

        return html.Div(
            [
                # Background decoration
                html.Div(
                    style={
                        "position": "absolute",
                        "top": "-50%",
                        "right": "-20%",
                        "width": "150px",
                        "height": "150px",
                        "background": "radial-gradient(circle, rgba(59, 130, 246, 0.15) 0%, transparent 70%)",
                        "borderRadius": "50%",
                        "pointerEvents": "none",
                        "filter": "blur(40px)",
                    }
                ),
                # Card content
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        DashIconify(
                                            icon=icon,
                                            width=24,
                                            style={
                                                "color": "#3b82f6",
                                                "marginRight": "0.5rem",
                                            },
                                        ),
                                        html.Span(
                                            title,
                                            style={
                                                "color": "#94a3b8",
                                                "fontSize": "0.875rem",
                                                "fontWeight": "500",
                                                "textTransform": "uppercase",
                                                "letterSpacing": "0.05em",
                                            },
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "marginBottom": "0.75rem",
                                    },
                                ),
                                html.Div(
                                    value,
                                    style={
                                        "color": "#f1f5f9",
                                        "fontSize": "2rem",
                                        "fontWeight": "700",
                                        "letterSpacing": "-0.025em",
                                        "marginBottom": "0.5rem",
                                    },
                                ),
                                html.Div(
                                    [
                                        (
                                            DashIconify(
                                                icon=(
                                                    icon_name
                                                    if change
                                                    else "mdi:circle"
                                                ),
                                                width=16,
                                                style={
                                                    "color": (
                                                        change_color
                                                        if change
                                                        else "#94a3b8"
                                                    ),
                                                    "marginRight": "0.25rem",
                                                },
                                            )
                                            if change
                                            else None
                                        ),
                                        html.Span(
                                            change if change else "No change",
                                            style={
                                                "color": (
                                                    change_color
                                                    if change
                                                    else "#94a3b8"
                                                ),
                                                "fontSize": "0.875rem",
                                                "fontWeight": "600",
                                            },
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                    },
                                ),
                            ],
                            style={
                                "position": "relative",
                                "zIndex": 1,
                            },
                        ),
                    ],
                    style={
                        "padding": "1.5rem",
                    },
                ),
            ],
            className="stat-card",
            style={
                "background": "linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.9))",
                "borderRadius": "16px",
                "border": "1px solid rgba(148, 163, 184, 0.2)",
                "boxShadow": "0 8px 32px rgba(0, 0, 0, 0.3), 0 2px 16px rgba(0, 0, 0, 0.15)",
                "backdropFilter": "blur(20px)",
                "position": "relative",
                "overflow": "hidden",
                "transition": "all 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
                "height": "100%",
            },
        )

    @staticmethod
    def create_tabs(tabs: List[Dict[str, Any]], active_tab: str = None) -> html.Div:
        """Create modern tab navigation."""
        if active_tab is None and tabs:
            active_tab = tabs[0].get("id")

        tab_buttons = []
        for tab in tabs:
            is_active = tab.get("id") == active_tab
            tab_buttons.append(
                html.Button(
                    [
                        (
                            DashIconify(
                                icon=tab.get("icon", "mdi:circle"),
                                width=20,
                                style={"marginRight": "0.5rem"},
                            )
                            if tab.get("icon")
                            else None
                        ),
                        tab.get("label", "Tab"),
                    ],
                    id={"type": "tab-button", "index": tab.get("id")},
                    className="tab-button active" if is_active else "tab-button",
                    style={
                        "background": (
                            "linear-gradient(145deg, #3b82f6, #2563eb)"
                            if is_active
                            else "transparent"
                        ),
                        "color": "#ffffff" if is_active else "#94a3b8",
                        "border": f"1px solid {'#3b82f6' if is_active else 'rgba(148, 163, 184, 0.2)'}",
                        "borderRadius": "10px",
                        "padding": "0.75rem 1.5rem",
                        "fontSize": "0.875rem",
                        "fontWeight": "600",
                        "cursor": "pointer",
                        "transition": "all 0.3s ease",
                        "display": "flex",
                        "alignItems": "center",
                        "boxShadow": (
                            "0 4px 12px rgba(0, 0, 0, 0.15)" if is_active else "none"
                        ),
                    },
                )
            )

        return html.Div(
            tab_buttons,
            style={
                "display": "flex",
                "gap": "0.75rem",
                "marginBottom": "2rem",
                "flexWrap": "wrap",
            },
        )


class LayoutHelpers:
    """Helper functions for dashboard layout components."""

    @staticmethod
    def create_page_header(
        title: str, subtitle: str, refresh_button_id: str
    ) -> html.Div:
        """Create an enhanced page header with modern design."""
        return html.Div(
            [
                # Background decoration
                html.Div(
                    style={
                        "position": "absolute",
                        "top": "-100%",
                        "left": "-10%",
                        "width": "300px",
                        "height": "300px",
                        "background": "radial-gradient(circle, rgba(59, 130, 246, 0.08) 0%, transparent 70%)",
                        "borderRadius": "50%",
                        "pointerEvents": "none",
                        "filter": "blur(60px)",
                    }
                ),
                # Content wrapper
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        DashIconify(
                                            icon="mdi:view-dashboard",
                                            width=36,
                                            style={
                                                "color": "#3b82f6",
                                                "marginRight": "1rem",
                                            },
                                        ),
                                        html.Div(
                                            [
                                                html.H1(
                                                    title,
                                                    style={
                                                        "color": "#f1f5f9",
                                                        "fontSize": "2.5rem",
                                                        "fontWeight": "800",
                                                        "margin": "0",
                                                        "letterSpacing": "-0.025em",
                                                        "background": "linear-gradient(135deg, #f1f5f9 0%, #cbd5e1 100%)",
                                                        "backgroundClip": "text",
                                                        "WebkitBackgroundClip": "text",
                                                        "WebkitTextFillColor": "transparent",
                                                    },
                                                ),
                                                html.P(
                                                    subtitle,
                                                    style={
                                                        "color": "#94a3b8",
                                                        "fontSize": "1rem",
                                                        "margin": "0.25rem 0 0 0",
                                                        "fontWeight": "400",
                                                    },
                                                ),
                                            ],
                                        ),
                                    ],
                                    style={"display": "flex", "alignItems": "center"},
                                ),
                            ],
                            style={"flex": "1"},
                        ),
                        html.Div(
                            [
                                html.Div(
                                    id="last-update-display",
                                    children=[
                                        DashIconify(
                                            icon="mdi:clock-outline",
                                            width=16,
                                            style={
                                                "marginRight": "0.5rem",
                                                "color": "#64748b",
                                            },
                                        ),
                                        html.Span("Last updated: Just now"),
                                    ],
                                    style={
                                        "color": "#64748b",
                                        "fontSize": "0.875rem",
                                        "marginBottom": "0.75rem",
                                        "textAlign": "right",
                                        "display": "flex",
                                        "alignItems": "center",
                                        "justifyContent": "flex-end",
                                    },
                                ),
                                html.Div(
                                    [
                                        html.Button(
                                            [
                                                DashIconify(
                                                    icon="mdi:refresh",
                                                    width=20,
                                                    style={"marginRight": "0.5rem"},
                                                    id="refresh-icon",
                                                ),
                                                "Refresh Data",
                                            ],
                                            id=refresh_button_id,
                                            n_clicks=0,
                                            className="refresh-button",
                                            style={
                                                "background": "linear-gradient(145deg, #059669, #047857)",
                                                "color": "white",
                                                "border": "none",
                                                "borderRadius": "10px",
                                                "padding": "0.75rem 1.5rem",
                                                "fontSize": "0.875rem",
                                                "fontWeight": "600",
                                                "cursor": "pointer",
                                                "transition": "all 0.3s ease",
                                                "boxShadow": "0 4px 12px rgba(5, 150, 105, 0.3)",
                                                "display": "flex",
                                                "alignItems": "center",
                                            },
                                        ),
                                    ],
                                    style={"display": "flex", "gap": "0.75rem"},
                                ),
                            ]
                        ),
                    ],
                    style={
                        "display": "flex",
                        "justifyContent": "space-between",
                        "alignItems": "center",
                        "position": "relative",
                        "zIndex": 1,
                    },
                ),
            ],
            style={
                "position": "relative",
                "marginBottom": "2.5rem",
                "padding": "2rem",
                "background": "linear-gradient(135deg, rgba(30, 41, 59, 0.4), rgba(15, 23, 42, 0.3))",
                "borderRadius": "20px",
                "border": "1px solid rgba(148, 163, 184, 0.15)",
                "boxShadow": "0 8px 32px rgba(0, 0, 0, 0.2)",
                "backdropFilter": "blur(20px)",
                "overflow": "hidden",
            },
        )

    @staticmethod
    def create_section_header(title: str) -> html.H2:
        """Create a standardized section header."""
        return html.H2(
            title,
            style={
                "color": "#f1f5f9",
                "fontSize": "1.75rem",
                "fontWeight": "700",
                "marginBottom": "1.5rem",
                "letterSpacing": "0.025em",
            },
        )

    @staticmethod
    def create_no_data_message(universe_name: str) -> html.Div:
        """Create a standardized no data message."""
        return html.Div(
            [
                html.H4(
                    universe_name,
                    style={
                        "color": "#f1f5f9",
                        "marginBottom": "1rem",
                        "textAlign": "center",
                    },
                ),
                html.Div(
                    "No data available for this universe",
                    style={
                        "color": "#ef4444",
                        "textAlign": "center",
                        "padding": "2rem",
                    },
                ),
            ]
        )
