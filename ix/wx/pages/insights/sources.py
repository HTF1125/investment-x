import json
from ix.db import InsightSource
from dash import html, dcc, callback_context, Output, Input, ALL, callback
from datetime import datetime
import webbrowser

# Define the layout component
layout = html.Div(
    [
        html.H1("Insight Sources"),
        html.Div(
            id="sources-container",
            style={
                "maxHeight": "400px",
                "overflowY": "auto",
                "border": "1px solid #ccc",
                "padding": "10px",
            },
        ),
        dcc.Interval(id="interval-refresh", interval=10 * 1000, n_intervals=0),
    ]
)


@callback(
    Output("sources-container", "children"),
    Input({"type": "visit-btn", "index": ALL}, "n_clicks"),
    Input("interval-refresh", "n_intervals"),
)
def update_sources(n_clicks_list, n_intervals):
    ctx = callback_context
    if ctx.triggered:
        trigger_prop = ctx.triggered[0]["prop_id"]
        if trigger_prop.startswith("{"):
            json_str = trigger_prop.split(".")[0].replace("'", '"')
            triggered_id = json.loads(json_str)
            source_id = triggered_id["index"]
            new_time = datetime.now()
            # Update the document's last_visited field
            insight_source = InsightSource.find_one({"id": source_id}).run()
            if insight_source:
                insight_source.set({"last_visited": new_time})
                webbrowser.open(insight_source.url, new=2)  # Open in new tab

    sources = InsightSource.find({}).sort("last_visited").run()
    children = []
    for source in sources:
        source_dict = source.model_dump()
        source_dict["_id"] = str(source.id)
        if "last_visited" in source_dict and isinstance(
            source_dict["last_visited"], datetime
        ):
            source_dict["last_visited"] = (
                source_dict["last_visited"].replace(microsecond=0).isoformat(" ")
            )
        children.append(
            html.Div(
                [
                    html.Span(source_dict.get("name", "Unnamed"), style={"fontWeight": "bold", "marginRight": "10px"}),
                    html.Span(f"Frequency: {source_dict.get('frequency', 'Unclassified')}", style={"marginRight": "10px"}),
                    html.Span("Last visited: ", style={"marginRight": "5px"}),
                    html.Span(source_dict.get("last_visited", ""), style={"fontFamily": "monospace", "marginRight": "10px"}),
                    html.Button(
                        "Visit",
                        id={"type": "visit-btn", "index": source_dict["_id"]},
                        n_clicks=0,
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "padding": "8px",
                    "marginBottom": "6px",
                    "border": "1px solid #eee",
                },
            )
        )
    return children
