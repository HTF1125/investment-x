import json
from dash import html
import dash_bootstrap_components as dbc

def create_insight_card(insight):
    published_date = (
        insight.get("published_date", "")[:10]
        if isinstance(insight.get("published_date", ""), str)
        else ""
    )

    # Define fixed widths and styles for each field.
    published_date_style = {
        "color": "white",
        "opacity": 0.7,
        "fontSize": "0.8rem",
        "width": "80px",
        "textAlign": "left",
        "overflow": "hidden",
        "whiteSpace": "nowrap"
    }

    issuer_style = {
        "color": "white",
        "opacity": 0.7,
        "fontSize": "0.8rem",
        "width": "150px",
        "overflow": "hidden",
        "whiteSpace": "nowrap",
        "textAlign": "left",
        "marginLeft": "10px"
    }
    name_style = {
        "color": "white",
        "fontWeight": "600",
        "fontSize": "1rem",
        "width": "200px",
        "overflow": "hidden",
        "whiteSpace": "nowrap",
        "textAlign": "left",
        "marginLeft": "8px"
    }
    # Left side content (clickable to open modal) with fixed-width fields.
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
            "flexWrap": "nowrap"
        },
    )

    # Right side: Icon-only buttons for PDF and Delete actions.
    # Note: Ensure that Font Awesome is included in your project.
    pdf_button = dbc.Button(
        html.I(className="fa-regular fa-file-pdf", style={"fontSize": "1.2rem"}),
        href=f"https://files.investment-x.app/{insight.get('id')}.pdf",
        target="_blank",
        color="light",
        size="sm",
        style={
            "marginRight": "5px",
            "padding": "0.25rem 0.5rem",
            "minWidth": "initial"
        }
    )

    delete_button = dbc.Button(
        html.I(className="fa fa-trash", style={"fontSize": "1.2rem"}),
        id={'type': 'delete-insight-button', 'index': insight.get('id')},
        color="danger",
        size="sm",
        n_clicks=0,
        style={
            "padding": "0.25rem 0.5rem",
            "minWidth": "initial"
        }
    )

    # Group the buttons in a flex container aligned to the right.
    button_group = html.Div(
        [pdf_button, delete_button],
        style={
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "flex-end"
        }
    )

    # Create a compact card with reduced paddings and margins.
    card = dbc.Card(
        dbc.CardBody(
            dbc.Row(
                [
                    dbc.Col(left_content, width=9, style={"padding": "0.25rem 0"}),
                    dbc.Col(
                        button_group,
                        width=3,
                        style={"padding": "0.25rem 0", "textAlign": "right"}
                    ),
                ],
                align="center",
                style={"marginLeft": 0, "marginRight": 0}
            )
        ),
        className="mb-2",
        style={
            "border": "1px solid #333",
            "backgroundColor": "#222",
            "color": "white",
            "padding": "0.25rem"
        },
    )
    return card
