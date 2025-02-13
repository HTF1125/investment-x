import json
import base64
from datetime import datetime
from bson import ObjectId

import dash
import dash_bootstrap_components as dbc
from dash import html, callback, Input, Output, State, ALL
from dash.exceptions import PreventUpdate

# External modules—ensure these are installed and in your PYTHONPATH.
from ix.db.client import get_insights
from ix.db.conn import Insight
from ix.db.boto import Boto
from ix.misc import PDFSummarizer, Settings

# Import helper function from our helpers module.
from .helpers import create_insight_card

# ----------------------------------------------------------------------
# Combined Callback: Fetch (Load/Search) and Delete Insights
# ----------------------------------------------------------------------
@callback(
    Output("insights-data", "data"),
    Output("total-insights-loaded", "data"),
    Output("search-query", "data"),
    Input("load-more-insights", "n_clicks"),
    Input("search-button", "n_clicks"),
    Input("insights-search", "n_submit"),
    Input({'type': 'delete-insight-button', 'index': ALL}, 'n_clicks'),
    State("insights-data", "data"),
    State("total-insights-loaded", "data"),
    State("search-query", "data"),
    State("insights-search", "value"),
)
def combined_fetch_delete_callback(
    load_clicks,
    search_clicks,
    search_submit,
    delete_clicks,
    current_data,
    total_loaded,
    search_query,
    search_value,
):
    ctx = dash.callback_context

    # Determine which input triggered the callback.
    if ctx.triggered:
        triggered_prop = ctx.triggered[0]["prop_id"]
        trigger_id = triggered_prop.split(".")[0]
    else:
        # On initial page load, treat as a search load.
        trigger_id = "initial"

    # ----- Deletion Branch -----
    if ctx.triggered and "delete-insight-button" in triggered_prop:
        try:
            # Extract the insight id from the triggered delete button.
            triggered_id = json.loads(triggered_prop.split(".")[0])
            insight_id = str(triggered_id["index"])
        except Exception:
            raise PreventUpdate

        updated_insights = []
        insight_found = None

        # Remove the deleted insight from the current store.
        for insight_json in current_data:
            insight = json.loads(insight_json)
            if str(insight.get("id")) == insight_id:
                insight_found = insight
            else:
                updated_insights.append(insight_json)

        # Attempt deletion in the backend if the insight was found.
        if insight_found:
            try:
                print(insight_found)
                # Example deletion call – adjust as needed.
                Insight.find_one(Insight.id == ObjectId(insight_found.get("id"))).delete().run()
            except Exception as e:
                print(f"Error deleting insight with id {insight_id}: {e}")

        new_total = total_loaded - 1 if total_loaded > 0 else 0
        # For deletion, we leave the search query unchanged.
        return updated_insights, new_total, dash.no_update

    # ----- Fetch/Load/Search Branch -----
    # For initial load, search-button, or search submission, reset the data.
    if trigger_id in ["search-button", "insights-search", "initial"]:
        search_query = search_value or ""
        skip = 0
    elif trigger_id == "load-more-insights":
        skip = total_loaded or 0
    else:
        skip = 0

    limit = 10
    new_insights = get_insights(search=search_query, skip=skip, limit=limit)

    if not new_insights:
        if trigger_id == "load-more-insights":
            raise PreventUpdate
        new_serialized = []
    else:
        new_serialized = [insight.model_dump_json() for insight in new_insights]

    if trigger_id in ["search-button", "insights-search", "initial"]:
        updated_data = new_serialized
        new_total = len(new_serialized)
    else:
        updated_data = current_data + new_serialized
        new_total = total_loaded + len(new_insights)

    return updated_data, new_total, search_query

# ----------------------------------------------------------------------
# Callback: Update Insight Cards
# ----------------------------------------------------------------------
@callback(
    Output("insights-container-wrapper", "children"),
    Input("insights-data", "data"),
)
def update_insights_cards(insights_data):
    if not insights_data:
        return dbc.Alert(
            "No insights available.", color="info", className="text-center"
        )
    try:
        cards = [create_insight_card(json.loads(insight)) for insight in insights_data]
        return [dbc.Row(dbc.Col(card, width=12)) for card in cards]
    except Exception as e:
        return dbc.Alert(
            f"Error processing insights: {str(e)}",
            color="danger",
            className="text-center",
        )

# ----------------------------------------------------------------------
# Callback: PDF Upload Processing
# ----------------------------------------------------------------------
@callback(
    Output("output-pdf-upload", "children"),
    Output("upload-pdf", "contents"),
    Input("upload-pdf", "contents"),
    State("upload-pdf", "filename"),
    State("upload-pdf", "last_modified"),
    prevent_initial_call=True,
)
def process_pdf_upload(content, filename, last_modified):
    if content is None:
        raise PreventUpdate
    try:
        content_type, content_string = content.split(",")
        decoded = base64.b64decode(content_string)
        if not filename.lower().endswith(".pdf"):
            return html.Div("Only PDF files are allowed.", style={"color": "red"}), None
        if not decoded.startswith(b"%PDF-"):
            return html.Div("Invalid PDF file.", style={"color": "red"}), None
        try:
            published_date_str, issuer, name = filename.rsplit("_", 2)
            name = name.rsplit(".", 1)[0]
            published_date = datetime.strptime(published_date_str, "%Y%m%d").date()
        except ValueError:
            return (
                html.Div(
                    "Filename must be in the format 'YYYYMMDD_issuer_name.pdf'",
                    style={"color": "red"},
                ),
                None,
            )
        insight = Insight(
            published_date=published_date, issuer=issuer, name=name
        ).create()
        filename_pdf = f"{insight.id}.pdf"
        Boto().save_pdf(pdf_content=decoded, filename=filename_pdf)
        insight.set(
            {
                "summary": PDFSummarizer(Settings.openai_secret_key).process_insights(
                    Boto().get_pdf(filename=filename_pdf)
                )
            }
        )
        return (
            html.Div(
                [
                    html.H5(
                        f"File '{filename_pdf}' uploaded successfully",
                        style={"color": "green"},
                    ),
                    html.P(f"Published Date: {published_date}"),
                    html.P(f"Issuer: {issuer}"),
                    html.P(f"Name: {name}"),
                    html.P(f"Last modified: {datetime.fromtimestamp(last_modified)}"),
                    html.P(f"Insight ID: {insight.id}"),
                    html.P(f"File size: {len(decoded) / 1024:.2f} KB"),
                ]
            ),
            None,
        )
    except Exception as e:
        return (
            html.Div(
                [
                    html.H5("Error processing file", style={"color": "red"}),
                    html.P(str(e)),
                ]
            ),
            None,
        )

# ----------------------------------------------------------------------
# Callback: Modal Display
# ----------------------------------------------------------------------
@callback(
    Output("insight-modal", "is_open"),
    Output("modal-body-content", "children"),
    Input({"type": "insight-card-clickable", "index": ALL}, "n_clicks"),
    Input("close-modal", "n_clicks"),
    State("insight-modal", "is_open"),
    State("insights-data", "data"),
)
def display_modal(n_clicks_list, close_n, is_open, insights_data):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    triggered = ctx.triggered[0]
    if "close-modal" in triggered["prop_id"]:
        return False, dash.no_update

    if not any(n_clicks_list):
        raise PreventUpdate

    try:
        triggered_id = json.loads(triggered["prop_id"].split(".")[0])
        card_index = triggered_id["index"]
    except Exception:
        return is_open, dash.no_update

    summary_text = "No summary available."
    for insight_json in insights_data:
        insight = json.loads(insight_json)
        if str(insight.get("id")) == str(card_index):
            summary_text = insight.get("summary", "No summary available.")
            break

    return True, summary_text
