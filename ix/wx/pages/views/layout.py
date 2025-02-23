from dash import register_page, html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
from ix.db.client import get_recent_tactical_view

# Register the page
register_page(__name__, path="/views", title="Tactical Views", name="Tactical Views")


def render_item(key, value, level=0):
    """Recursively renders a view item based on its type.

    - For dicts that are "leaf" nodes (with 'view' and 'rationale'), renders a simple div.
    - For non-leaf dicts, recurses into its children and wraps them in an Accordion.
    - For lists, distinguishes between a list of dicts (e.g. tactical ideas) and a list of strings.
    - For strings, renders a simple card.
    """
    # Top-level sections are expanded; nested sections are collapsed.
    start_collapsed = False if level == 0 else True

    if isinstance(value, dict):
        # Check if this dict is a leaf node (contains a view and rationale)
        if "view" in value and "rationale" in value:
            return html.Div(
                [
                    html.H6(key, className="fw-bold mb-1 text-white"),
                    html.P(
                        f"View: {value.get('view', 'N/A')}", className="text-info mb-1"
                    ),
                    html.P(
                        value.get("rationale", "No rationale available"),
                        className="text-muted small",
                    ),
                ],
                className="mb-3 border-bottom pb-2",
            )
        else:
            # Non-leaf dict: render each child recursively in an AccordionItem.
            children = [
                render_item(subkey, subvalue, level=level + 1)
                for subkey, subvalue in value.items()
            ]
            return dbc.Card(
                dbc.Accordion(
                    [dbc.AccordionItem(html.Div(children), title=key)],
                    start_collapsed=start_collapsed,
                    always_open=True,
                ),
                className="mb-3 bg-dark text-white border-light",
            )

    elif isinstance(value, list):
        # If the list consists entirely of dicts, assume each item has keys (like tactical ideas)
        if value and all(isinstance(item, dict) for item in value):
            children = []
            for item in value:
                idea = item.get("idea", "N/A")
                rationale = item.get("rationale", "No rationale available")
                children.append(
                    html.Div(
                        [
                            html.H6(idea, className="fw-bold mb-1 text-white"),
                            html.P(rationale, className="text-muted small"),
                        ],
                        className="mb-3 border-bottom pb-2",
                    )
                )
            return dbc.Card(
                dbc.Accordion(
                    [dbc.AccordionItem(html.Div(children), title=key)],
                    start_collapsed=start_collapsed,
                    always_open=True,
                ),
                className="mb-3 bg-dark text-white border-light",
            )
        else:
            # Otherwise, assume it's a list of strings
            return dbc.Card(
                dbc.CardBody(
                    [
                        html.H5(key, className="text-white"),
                        html.Ul(
                            [html.Li(item, className="text-muted") for item in value]
                        ),
                    ]
                ),
                className="mb-3 bg-dark text-white border-light",
            )

    elif isinstance(value, str):
        return dbc.Card(
            dbc.CardBody(
                [
                    html.H5(key, className="text-white"),
                    html.P(value, className="text-muted"),
                ]
            ),
            className="mb-3 bg-dark text-white border-light",
        )
    else:
        # Fallback for unexpected types
        return html.Div(f"{key}: {value}", className="text-muted")


layout = dbc.Container(
    fluid=True,
    className="p-3",
    style={"backgroundColor": "#121212", "color": "#ffffff"},  # Dark mode background
    children=[
        html.H3("Tactical Market Views", className="text-center mb-4 text-white"),
        html.H5(id="published-date", className="text-center text-secondary mb-4"),
        dcc.Loading(type="circle", children=[html.Div(id="views-content")]),
    ],
)


@callback(
    [Output("views-content", "children"), Output("published-date", "children")],
    Input("views-content", "id"),  # Dummy input to trigger on load
)
def update_views(_):
    tactical_view = get_recent_tactical_view()
    if not tactical_view:
        return (
            html.P("No recent tactical views available.", className="text-danger"),
            "",
        )

    views = tactical_view.views
    published_date = tactical_view.published_date.strftime(
        "Published Date: %Y-%m-%d %H:%M:%S"
    )
    # Render each top-level view section using our recursive function.
    sections = [
        render_item(category, content, level=0) for category, content in views.items()
    ]

    return dbc.Row(dbc.Col(sections, width=12)), published_date
