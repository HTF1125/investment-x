import json
import base64
from datetime import datetime
from bson import ObjectId
from typing import Any, List, Tuple, Optional

import dash
import dash_bootstrap_components as dbc
from dash import html, callback, Input, Output, State, ALL, no_update
from dash.exceptions import PreventUpdate

from ix.db.client import get_insights
from ix.db.conn import Insight
from ix.db.boto import Boto
from ix.misc.terminal import get_logger
from ix.misc import PDFSummarizer, Settings
from .insight_card import InsightCard



# Configure logging.
logger = get_logger(__name__)


def remove_deleted_insight(current_data: List[str], insight_id: str) -> List[str]:
    """Removes the deleted insight from the current data list."""
    updated_insights = []
    for insight_json in current_data:
        insight = json.loads(insight_json)
        if str(insight.get("id")) != insight_id:
            updated_insights.append(insight_json)
    return updated_insights


def delete_insight_backend(insight: dict) -> None:
    """Attempts deletion in the backend for a given insight."""
    try:
        Insight.find_one(Insight.id == ObjectId(insight.get("id"))).delete().run()
    except Exception as e:
        logger.error(f"Error deleting insight with id {insight.get('id')}: {e}")


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
    Input({"type": "delete-insight-button", "index": ALL}, "n_clicks"),
    State("insights-data", "data"),
    State("total-insights-loaded", "data"),
    State("search-query", "data"),
    State("insights-search", "value"),
)
def combined_fetch_delete_callback(
    load_clicks: Optional[int],
    search_clicks: Optional[int],
    search_submit: Optional[int],
    delete_clicks: List[Optional[int]],
    current_data: List[str],
    total_loaded: int,
    search_query: str,
    search_value: Optional[str],
):
    """
    Depending on which input triggered the callback, either fetch new insights, load more insights,
    or delete an insight.
    """
    ctx = dash.callback_context
    if ctx.triggered:
        triggered_prop = ctx.triggered[0]["prop_id"]
    else:
        triggered_prop = "initial"

    # ----- Deletion Branch -----
    if "delete-insight-button" in triggered_prop:
        try:
            triggered_id = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])
            insight_id = str(triggered_id["index"])
        except Exception:
            raise PreventUpdate

        # Remove the insight from the current data.
        updated_insights = remove_deleted_insight(current_data, insight_id)

        # Find the insight to delete in the current data.
        for insight_json in current_data:
            insight = json.loads(insight_json)
            if str(insight.get("id")) == insight_id:
                delete_insight_backend(insight)
                break

        new_total = total_loaded - 1 if total_loaded > 0 else 0
        return updated_insights, new_total, no_update

    # ----- Fetch/Load/Search Branch -----
    if (
        triggered_prop.startswith("search-button")
        or triggered_prop.startswith("insights-search")
        or triggered_prop == "initial"
    ):
        search_query = search_value or ""
        skip = 0
    elif triggered_prop.startswith("load-more-insights"):
        skip = total_loaded or 0
    else:
        skip = 0

    limit = 10
    new_insights = get_insights(search=search_query, skip=skip, limit=limit)

    if not new_insights:
        if triggered_prop.startswith("load-more-insights"):
            raise PreventUpdate
        new_serialized: List[str] = []
    else:
        new_serialized = [insight.model_dump_json() for insight in new_insights]

    if (
        triggered_prop.startswith("search-button")
        or triggered_prop.startswith("insights-search")
        or triggered_prop == "initial"
    ):
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
def update_insights_cards(insights_data: List[str]) -> Any:
    """Updates the UI cards based on insights data."""
    if not insights_data:
        return dbc.Alert(
            "No insights available.", color="info", className="text-center"
        )
    try:
        cards = [InsightCard().layout(json.loads(insight)) for insight in insights_data]
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
def process_pdf_upload(
    content: Optional[str], filename: Optional[str], last_modified: Optional[float]
) -> Tuple[Any, Optional[str]]:
    """
    Processes a PDF upload, validates the file format and filename,
    uploads the PDF, and returns a success or error message.
    """
    if content is None or filename is None or last_modified is None:
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
        boto_instance = Boto()
        boto_instance.save_pdf(pdf_content=decoded, filename=filename_pdf)
        summarizer = PDFSummarizer(Settings.openai_secret_key)
        pdf_content = boto_instance.get_pdf(filename=filename_pdf)
        summary_text = summarizer.process_insights(pdf_content)
        insight.set({"summary": summary_text})
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
        logger.exception("Error processing PDF upload")
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
def display_modal(
    n_clicks_list: List[Optional[int]],
    close_n: Optional[int],
    is_open: bool,
    insights_data: List[str],
) -> Tuple[bool, Any]:
    """
    Opens the modal to display an insight summary when a card is clicked,
    and closes the modal when the close button is clicked.
    """
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    triggered = ctx.triggered[0]
    if "close-modal" in triggered["prop_id"]:
        return False, no_update

    if not any(n_clicks_list):
        raise PreventUpdate

    try:
        triggered_id = json.loads(triggered["prop_id"].split(".")[0])
        card_index = triggered_id["index"]
    except Exception:
        return is_open, no_update

    summary_text = "No summary available."
    for insight_json in insights_data:
        insight = json.loads(insight_json)
        if str(insight.get("id")) == str(card_index):
            summary_text = insight.get("summary", "No summary available.")
            break

    return True, summary_text
