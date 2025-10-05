"""
Main Layout Component for Dash Pages
Simple HTML-based layout without complex components.
"""

from dash import html


def page_layout(children, page_title=None, page_description=None, extra_padding=False):
    """
    Create a consistent page layout with proper navbar spacing

    Args:
        children: Page content components
        page_title: Optional page title
        page_description: Optional page description
        extra_padding: Add extra padding for dense content
    """
    # Calculate top padding to account for fixed navbar
    top_padding = "110px" if extra_padding else "90px"

    content = []

    # Add page header if title is provided
    if page_title:
        header = html.Div(
            [
                html.H1(
                    page_title,
                    style={
                        "color": "#ffffff",
                        "textAlign": "center",
                        "fontSize": "3rem",
                        "fontWeight": "bold",
                        "marginBottom": "8px",
                    },
                ),
                (
                    html.P(
                        page_description or "",
                        style={
                            "color": "#94a3b8",
                            "textAlign": "center",
                            "fontSize": "1.2rem",
                            "marginBottom": "0",
                        },
                    )
                    if page_description
                    else None
                ),
            ],
            style={
                "backgroundColor": "#1e293b",
                "padding": "30px",
                "borderRadius": "12px",
                "border": "1px solid #475569",
                "marginBottom": "20px",
                "boxShadow": "0 4px 12px rgba(0, 0, 0, 0.3)",
            },
        )
        content.append(header)

    # Add the main content
    if isinstance(children, list):
        content.extend(children)
    else:
        content.append(children)

    return html.Div(
        content,
        style={
            "backgroundColor": "#0f172a",
            "color": "#ffffff",
            "minHeight": "100vh",
            "paddingTop": top_padding,  # Account for fixed navbar
            "paddingBottom": "40px",
            "paddingLeft": "20px",
            "paddingRight": "20px",
            "maxWidth": "1680px",
            "margin": "0 auto",
        },
    )


def card_wrapper(children, title=None, icon=None, className=""):
    """
    Create a consistent dark-themed card wrapper

    Args:
        children: Card content
        title: Optional card title
        icon: Optional icon for title
        className: Additional CSS classes
    """
    header_content = None
    if title:
        header_content = html.Div(
            [
                html.I(className=f"{icon} me-2") if icon else None,
                html.H4(title, style={"color": "#ffffff", "margin": "0"}),
            ],
            style={"display": "flex", "alignItems": "center"},
        )

    if header_content:
        return html.Div(
            [
                html.Div(
                    header_content,
                    style={
                        "backgroundColor": "#1e293b",
                        "padding": "20px",
                        "borderBottom": "1px solid #475569",
                        "borderRadius": "12px 12px 0 0",
                    },
                ),
                html.Div(
                    children,
                    style={
                        "backgroundColor": "#1e293b",
                        "padding": "20px",
                        "borderRadius": "0 0 12px 12px",
                    },
                ),
            ],
            style={
                "border": "1px solid #475569",
                "borderRadius": "12px",
                "backgroundColor": "#1e293b",
                "marginBottom": "20px",
                "boxShadow": "0 4px 12px rgba(0, 0, 0, 0.3)",
                "transition": "all 0.3s ease",
            },
        )
    else:
        return html.Div(
            children,
            style={
                "backgroundColor": "#1e293b",
                "padding": "20px",
                "borderRadius": "12px",
                "border": "1px solid #475569",
                "marginBottom": "20px",
                "boxShadow": "0 4px 12px rgba(0, 0, 0, 0.3)",
                "transition": "all 0.3s ease",
            },
        )
