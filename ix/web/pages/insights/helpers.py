from typing import Dict, Any
from dash import html
import dash_bootstrap_components as dbc


def create_insight_card(insight: Dict[str, Any]) -> dbc.Card:
    """
    Creates a Bootstrap card for a given insight dictionary.
    """
    published_date = (
        insight.get("published_date", "")[:10]
        if isinstance(insight.get("published_date", ""), str)
        else ""
    )

    # Define styles
    published_date_style = {
        "color": "white",
        "opacity": 0.7,
        "fontSize": "0.75rem",
        "width": "80px",
        "textAlign": "left",
        "overflow": "hidden",
        "whiteSpace": "nowrap",
    }

    issuer_style = {
        "color": "white",
        "opacity": 0.7,
        "fontSize": "0.75rem",
        "width": "150px",
        "overflow": "hidden",
        "whiteSpace": "nowrap",
        "textAlign": "left",
        "marginLeft": "8px",
    }

    name_style = {
        "color": "white",
        "fontWeight": "600",
        "fontSize": "1rem",
        "maxWidth": "220px",
        "overflow": "hidden",
        "whiteSpace": "nowrap",
        "textAlign": "left",
        "marginLeft": "8px",
    }

    # Left side content (clickable)
    left_content = html.Div(
        [
            html.Small(f"{published_date}", style=published_date_style),
            html.Small(f"{insight.get('issuer', 'Unknown')}", style=issuer_style),
            html.H5(insight.get("name", "No Name"), className="mb-0", style=name_style),
        ],
        id={"type": "insight-card-clickable", "index": insight.get("id")},
        n_clicks=0,
        style={
            "cursor": "pointer",
            "display": "flex",
            "alignItems": "center",
            "flexWrap": "wrap",
        },
    )

    # Right side: Icon buttons
    pdf_button = dbc.Button(
        html.I(className="fa-regular fa-file-pdf", style={"fontSize": "1rem"}),
        href=f"/api/download-pdf/{insight.get('id')}",
        target="_blank",
        color="light",
        size="sm",
        style={"marginRight": "5px", "padding": "0.3rem", "minWidth": "initial"},
    )

    delete_button = dbc.Button(
        html.I(className="fa fa-trash", style={"fontSize": "1rem"}),
        id={"type": "delete-insight-button", "index": insight.get("id")},
        color="danger",
        size="sm",
        n_clicks=0,
        style={"padding": "0.3rem", "minWidth": "initial"},
    )

    # Group buttons in a responsive div
    button_group = html.Div(
        [pdf_button, delete_button],
        style={
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "flex-end",
            "gap": "5px",
        },
    )

    # Create a responsive card
    card = dbc.Card(
        dbc.CardBody(
            dbc.Row(
                [
                    dbc.Col(left_content, xs=8, sm=9, style={"padding": "0.2rem 0"}),
                    dbc.Col(
                        button_group,
                        xs=4,
                        sm=3,
                        style={"padding": "0.2rem 0", "textAlign": "right"},
                    ),
                ],
                align="center",
                style={"marginLeft": 0, "marginRight": 0},
            )
        ),
        className="mb-2",
        style={
            "border": "1px solid #444",
            "backgroundColor": "#1a1a1a",
            "color": "white",
            "padding": "0.5rem",
            "borderRadius": "8px",
        },
    )

    return card
