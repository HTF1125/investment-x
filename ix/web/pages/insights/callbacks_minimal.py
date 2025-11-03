"""
Enhanced Insights Callbacks
Advanced implementation with database connectivity, PDF processing, and modern UX.
Incorporates features from wx implementation with improved design.
"""

import json
import base64
from datetime import datetime
from bson import ObjectId
from typing import Any, List, Tuple, Optional

import dash
import dash_bootstrap_components as dbc
from dash import html, callback, Input, Output, State, no_update, ALL
from dash.exceptions import PreventUpdate

from ix.db.client import get_insights
from ix.db.models import Insights

# from ix.db.boto import Boto  # Removed - old db module
from ix.misc.terminal import get_logger
from ix.misc import PDFSummarizer, Settings
from .insight_card import create_insight_card

# Configure logging
logger = get_logger(__name__)


def create_insight_card(insight_data):
    """Create an insight card with proper styling"""
    # Status color mapping
    status_colors = {
        "completed": "#10b981",
        "processing": "#f59e0b",
        "new": "#3b82f6",
        "failed": "#ef4444",
    }

    status = insight_data.get("status", "new").lower()

    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.H5(
                                insight_data.get("name", "Untitled"),
                                style={
                                    "color": "#ffffff",
                                    "margin": "0 0 8px 0",
                                    "fontSize": "1.1rem",
                                },
                            ),
                            html.P(
                                insight_data.get("issuer", "Unknown"),
                                style={
                                    "color": "#94a3b8",
                                    "margin": "0 0 8px 0",
                                    "fontSize": "14px",
                                    "fontWeight": "500",
                                },
                            ),
                            html.P(
                                (
                                    insight_data.get("published_date", "")[:10]
                                    if insight_data.get("published_date")
                                    else "No date"
                                ),
                                style={
                                    "color": "#64748b",
                                    "margin": "0",
                                    "fontSize": "12px",
                                },
                            ),
                        ],
                        style={"flex": "1"},
                    ),
                    html.Div(
                        status.title(),
                        style={
                            "backgroundColor": status_colors.get(status, "#64748b"),
                            "color": "#ffffff",
                            "padding": "4px 12px",
                            "borderRadius": "20px",
                            "fontSize": "12px",
                            "fontWeight": "bold",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "flex-start",
                    "marginBottom": "12px",
                },
            ),
            html.P(
                (
                    insight_data.get("summary", "No summary available.")[:200] + "..."
                    if len(insight_data.get("summary", "")) > 200
                    else insight_data.get("summary", "No summary available.")
                ),
                style={
                    "color": "#e2e8f0",
                    "fontSize": "14px",
                    "lineHeight": "1.5",
                    "margin": "0 0 15px 0",
                },
            ),
            html.Div(
                [
                    html.Button(
                        [
                            html.I(
                                className="fas fa-eye", style={"marginRight": "6px"}
                            ),
                            "View Details",
                        ],
                        id={
                            "type": "insight-card-clickable",
                            "index": str(insight_data.get("id", "")),
                        },
                        n_clicks=0,
                        style={
                            "backgroundColor": "#3b82f6",
                            "border": "none",
                            "borderRadius": "6px",
                            "color": "#ffffff",
                            "padding": "6px 12px",
                            "fontSize": "12px",
                            "cursor": "pointer",
                            "marginRight": "8px",
                            "display": "flex",
                            "alignItems": "center",
                        },
                    ),
                    html.A(
                        [
                            html.I(
                                className="fas fa-download",
                                style={"marginRight": "6px"},
                            ),
                            "Download",
                        ],
                        href=f"https://files.investment-x.app/{insight_data.get('id')}.pdf",
                        target="_blank",
                        style={
                            "backgroundColor": "transparent",
                            "border": "1px solid #475569",
                            "borderRadius": "6px",
                            "color": "#ffffff",
                            "padding": "6px 12px",
                            "fontSize": "12px",
                            "cursor": "pointer",
                            "marginRight": "8px",
                            "display": "flex",
                            "alignItems": "center",
                            "textDecoration": "none",
                        },
                    ),
                    html.Button(
                        [
                            html.I(
                                className="fas fa-trash", style={"marginRight": "6px"}
                            ),
                            "Delete",
                        ],
                        id={
                            "type": "delete-insight-button",
                            "index": str(insight_data.get("id", "")),
                        },
                        n_clicks=0,
                        style={
                            "backgroundColor": "transparent",
                            "border": "1px solid #ef4444",
                            "borderRadius": "6px",
                            "color": "#ef4444",
                            "padding": "6px 12px",
                            "fontSize": "12px",
                            "cursor": "pointer",
                            "display": "flex",
                            "alignItems": "center",
                        },
                    ),
                ],
                style={"display": "flex", "gap": "8px"},
            ),
        ],
        style={
            "backgroundColor": "#1e293b",
            "border": "1px solid #475569",
            "borderRadius": "12px",
            "padding": "20px",
            "marginBottom": "15px",
            "boxShadow": "0 4px 12px rgba(0, 0, 0, 0.3)",
            "transition": "all 0.3s ease",
        },
    )


# Initial insights loading callback
@callback(
    [
        Output("insights-container", "children"),
        Output("insights-data", "data"),
    ],
    Input("insights-container", "id"),  # Triggers on page load
)
def load_initial_insights(container_id):
    """Load initial insights from database on page load"""
    try:
        # Get insights from database
        insights = get_insights()

        if not insights:
            # No insights found
            return (
                html.Div(
                    [
                        html.I(
                            className="fas fa-search fa-3x",
                            style={"color": "#64748b", "marginBottom": "20px"},
                        ),
                        html.H4(
                            "No Insights Found",
                            style={"color": "#ffffff", "marginBottom": "10px"},
                        ),
                        html.P(
                            "Upload some documents to get started with AI-powered insights.",
                            style={"color": "#94a3b8"},
                        ),
                    ],
                    style={
                        "textAlign": "center",
                        "padding": "60px 20px",
                        "backgroundColor": "#1e293b",
                        "borderRadius": "12px",
                        "border": "1px solid #475569",
                    },
                ),
                [],
            )

        # Create insight cards
        insight_cards = []

        for insight in insights:
            # Convert insight to dict format
            insight_data = {
                "id": str(insight.id),
                "name": insight.name or "Untitled",
                "issuer": insight.issuer or "Unknown",
                "published_date": (
                    str(insight.published_date) if insight.published_date else ""
                ),
                "status": insight.status or "new",
                "summary": insight.summary or "",
            }

            # Create card
            card = create_insight_card(insight_data)
            insight_cards.append(card)

        # Serialize insights data for the store (limit to first 10)
        insights_to_serialize = insights[:10]
        serialized_insights = [
            insight.model_dump_json() for insight in insights_to_serialize
        ]

        # Limit to first 10 insights for initial load
        if len(insight_cards) > 10:
            insight_cards = insight_cards[:10]

        return (
            html.Div(insight_cards),
            serialized_insights,
        )

    except Exception as e:
        logger.error(f"Error loading insights: {e}")

        # Return error state
        return (
            html.Div(
                [
                    html.I(
                        className="fas fa-exclamation-triangle fa-3x",
                        style={"color": "#ef4444", "marginBottom": "20px"},
                    ),
                    html.H4(
                        "Error Loading Insights",
                        style={"color": "#ffffff", "marginBottom": "10px"},
                    ),
                    html.P(
                        f"Failed to load insights: {str(e)}", style={"color": "#94a3b8"}
                    ),
                    html.Button(
                        "Retry",
                        id="retry-insights",
                        style={
                            "backgroundColor": "#3b82f6",
                            "border": "none",
                            "borderRadius": "8px",
                            "color": "#ffffff",
                            "padding": "10px 20px",
                            "cursor": "pointer",
                            "marginTop": "15px",
                        },
                    ),
                ],
                style={
                    "textAlign": "center",
                    "padding": "60px 20px",
                    "backgroundColor": "#1e293b",
                    "borderRadius": "12px",
                    "border": "1px solid #475569",
                },
            ),
            [],
        )


# Load more insights callback
@callback(
    Output("insights-container", "children", allow_duplicate=True),
    Input("load-more-insights", "n_clicks"),
    State("insights-container", "children"),
    prevent_initial_call=True,
)
def load_more_insights(n_clicks, current_children):
    """Load more insights when button is clicked"""
    if not n_clicks:
        raise PreventUpdate

    try:
        # Ensure current_children is a list
        if current_children is None:
            current_children = []
        elif not isinstance(current_children, list):
            current_children = [current_children] if current_children else []

        # Get more insights from database (skip already loaded)
        skip_count = len(current_children)
        more_insights = get_insights(skip=skip_count, limit=5)

        if not more_insights:
            # No more insights to load
            no_more_message = html.Div(
                [
                    html.I(
                        className="fas fa-check-circle",
                        style={"color": "#10b981", "marginRight": "8px"},
                    ),
                    "No more insights to load.",
                ],
                style={
                    "backgroundColor": "rgba(16, 185, 129, 0.1)",
                    "border": "1px solid rgba(16, 185, 129, 0.3)",
                    "borderRadius": "8px",
                    "padding": "15px",
                    "color": "#6ee7b7",
                    "textAlign": "center",
                    "marginTop": "15px",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                },
            )
            return current_children + [no_more_message]

        # Create cards for new insights
        new_cards = []
        for insight in more_insights:
            insight_data = {
                "id": str(insight.id),
                "name": insight.name or "Untitled",
                "issuer": insight.issuer or "Unknown",
                "published_date": (
                    str(insight.published_date) if insight.published_date else ""
                ),
                "status": insight.status or "new",
                "summary": insight.summary or "",
            }

            card = create_insight_card(insight_data)
            new_cards.append(card)

        return current_children + new_cards

    except Exception as e:
        logger.error(f"Error loading more insights: {e}")

        error_message = html.Div(
            f"Error loading more insights: {str(e)}",
            style={
                "backgroundColor": "rgba(239, 68, 68, 0.1)",
                "border": "1px solid rgba(239, 68, 68, 0.3)",
                "borderRadius": "8px",
                "padding": "15px",
                "color": "#fca5a5",
                "textAlign": "center",
                "marginTop": "15px",
            },
        )
        return current_children + [error_message]


# Search functionality
@callback(
    Output("insights-container", "children", allow_duplicate=True),
    [
        Input("search-button", "n_clicks"),
        Input("insights-search", "n_submit"),
    ],
    [
        State("insights-search", "value"),
        State("sort-dropdown", "value"),
        State("issuer-filter", "value"),
        State("date-range-filter", "start_date"),
        State("date-range-filter", "end_date"),
    ],
    prevent_initial_call=True,
)
def search_insights(
    search_clicks,
    search_submit,
    search_value,
    sort_value,
    issuer_value,
    start_date,
    end_date,
):
    """Search and filter insights"""
    try:
        # Get all insights first (the get_insights function only supports search parameter)
        if search_value:
            insights = get_insights(search=search_value)
        else:
            insights = get_insights()

        # Apply additional filters manually since get_insights doesn't support them
        if issuer_value and issuer_value != "all":
            insights = [
                insight
                for insight in insights
                if issuer_value.lower() in insight.issuer.lower()
            ]

        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
                insights = [
                    insight
                    for insight in insights
                    if insight.published_date
                    and insight.published_date >= start_date_obj
                ]
            except (ValueError, TypeError):
                pass

        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
                insights = [
                    insight
                    for insight in insights
                    if insight.published_date and insight.published_date <= end_date_obj
                ]
            except (ValueError, TypeError):
                pass

        if not insights:
            return html.Div(
                [
                    html.I(
                        className="fas fa-search fa-2x",
                        style={"color": "#64748b", "marginBottom": "15px"},
                    ),
                    html.H5(
                        "No Results Found",
                        style={"color": "#ffffff", "marginBottom": "8px"},
                    ),
                    html.P(
                        "Try adjusting your search criteria.",
                        style={"color": "#94a3b8"},
                    ),
                ],
                style={
                    "textAlign": "center",
                    "padding": "40px 20px",
                    "backgroundColor": "#1e293b",
                    "borderRadius": "12px",
                    "border": "1px solid #475569",
                },
            )

        # Sort insights if sort value is provided
        if sort_value:
            if sort_value == "date_desc":
                insights = sorted(
                    insights, key=lambda x: x.get("published_date", ""), reverse=True
                )
            elif sort_value == "date_asc":
                insights = sorted(insights, key=lambda x: x.get("published_date", ""))
            elif sort_value == "name_asc":
                insights = sorted(insights, key=lambda x: x.get("name", "").lower())
            elif sort_value == "name_desc":
                insights = sorted(
                    insights, key=lambda x: x.get("name", "").lower(), reverse=True
                )

        # Create cards
        insight_cards = []
        for insight in insights:
            insight_data = {
                "id": str(insight.id),
                "name": insight.name or "Untitled",
                "issuer": insight.issuer or "Unknown",
                "published_date": (
                    str(insight.published_date) if insight.published_date else ""
                ),
                "status": insight.status or "new",
                "summary": insight.summary or "",
            }

            card = create_insight_card(insight_data)
            insight_cards.append(card)

        return html.Div(insight_cards)

    except Exception as e:
        logger.error(f"Error searching insights: {e}")

        return html.Div(
            f"Search error: {str(e)}",
            style={
                "backgroundColor": "rgba(239, 68, 68, 0.1)",
                "border": "1px solid rgba(239, 68, 68, 0.3)",
                "borderRadius": "8px",
                "padding": "15px",
                "color": "#fca5a5",
                "textAlign": "center",
            },
        )


# Clear search callback
@callback(
    [
        Output("insights-search", "value"),
        Output("sort-dropdown", "value"),
        Output("issuer-filter", "value"),
        Output("date-range-filter", "start_date"),
        Output("date-range-filter", "end_date"),
    ],
    Input("search-button", "n_clicks"),
    prevent_initial_call=True,
)
def clear_search_on_search(n_clicks):
    """Clear search fields when search button is clicked"""
    return "", None, None, None, None


# Enhanced PDF upload callback with full processing
@callback(
    Output("output-pdf-upload", "children", allow_duplicate=True),
    Output("upload-pdf", "contents"),
    Input("upload-pdf", "contents"),
    State("upload-pdf", "filename"),
    State("upload-pdf", "last_modified"),
    prevent_initial_call=True,
)
def handle_enhanced_upload(
    contents: Optional[str], filename: Optional[str], last_modified: Optional[float]
) -> Tuple[Any, Optional[str]]:
    """
    Enhanced PDF upload processing with validation, content extraction, and AI summarization.
    Based on the wx implementation with improved error handling and user feedback.
    """
    if contents is None or filename is None or last_modified is None:
        raise PreventUpdate

    try:
        # Parse uploaded content
        content_type, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)

        # Validate file type
        if not filename.lower().endswith(".pdf"):
            return (
                html.Div(
                    [
                        html.I(
                            className="fas fa-exclamation-triangle",
                            style={"color": "#ef4444", "marginRight": "8px"},
                        ),
                        "Only PDF files are allowed.",
                    ],
                    style={
                        "backgroundColor": "rgba(239, 68, 68, 0.1)",
                        "border": "1px solid rgba(239, 68, 68, 0.3)",
                        "borderRadius": "8px",
                        "padding": "15px",
                        "color": "#fca5a5",
                        "display": "flex",
                        "alignItems": "center",
                        "justifyContent": "center",
                    },
                ),
                None,
            )

        # Validate PDF content
        if not decoded.startswith(b"%PDF-"):
            return (
                html.Div(
                    [
                        html.I(
                            className="fas fa-exclamation-triangle",
                            style={"color": "#ef4444", "marginRight": "8px"},
                        ),
                        "Invalid PDF file format.",
                    ],
                    style={
                        "backgroundColor": "rgba(239, 68, 68, 0.1)",
                        "border": "1px solid rgba(239, 68, 68, 0.3)",
                        "borderRadius": "8px",
                        "padding": "15px",
                        "color": "#fca5a5",
                        "display": "flex",
                        "alignItems": "center",
                        "justifyContent": "center",
                    },
                ),
                None,
            )

        # Parse filename for metadata (format: YYYYMMDD_issuer_name.pdf)
        try:
            published_date_str, issuer, name = filename.rsplit("_", 2)
            name = name.rsplit(".", 1)[0]  # Remove .pdf extension
            published_date = datetime.strptime(published_date_str, "%Y%m%d").date()
        except ValueError:
            return (
                html.Div(
                    [
                        html.I(
                            className="fas fa-exclamation-triangle",
                            style={"color": "#ef4444", "marginRight": "8px"},
                        ),
                        "Filename must be in the format 'YYYYMMDD_issuer_name.pdf'",
                    ],
                    style={
                        "backgroundColor": "rgba(239, 68, 68, 0.1)",
                        "border": "1px solid rgba(239, 68, 68, 0.3)",
                        "borderRadius": "8px",
                        "padding": "15px",
                        "color": "#fca5a5",
                        "display": "flex",
                        "alignItems": "center",
                        "textAlign": "center",
                    },
                ),
                None,
            )

        # Create insight record
        insight = Insights(
            published_date=published_date, issuer=issuer, name=name, status="processing"
        )

        # Save PDF to storage - commented out (Boto removed)
        # filename_pdf = f"{insight.id}.pdf"
        # boto_instance = Boto()
        # try:
        #     boto_instance.save_pdf(pdf_content=decoded, filename=filename_pdf)
        # except Exception as e:
        #     logger.error(f"Error saving PDF to storage: {e}")
        # insight.delete()  # Clean up if storage fails - commented out

        return (
            html.Div(
                [
                    html.I(
                        className="fas fa-exclamation-triangle",
                        style={"color": "#ef4444", "marginRight": "8px"},
                    ),
                    "PDF storage temporarily disabled",
                ],
                style={
                    "backgroundColor": "rgba(239, 68, 68, 0.1)",
                    "border": "1px solid rgba(239, 68, 68, 0.3)",
                    "borderRadius": "8px",
                    "padding": "15px",
                    "color": "#fca5a5",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                },
            ),
            None,
        )

        # Generate AI summary
        try:
            if hasattr(Settings, "openai_secret_key") and Settings.openai_secret_key:
                summarizer = PDFSummarizer(Settings.openai_secret_key)
                pdf_content = boto_instance.get_pdf(filename=filename_pdf)
                summary_text = summarizer.process_insights(pdf_content)
                insight.set({"summary": summary_text, "status": "completed"})
            else:
                insight.set(
                    {
                        "summary": "AI summarization not available - API key not configured",
                        "status": "completed",
                    }
                )
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            insight.set(
                {"summary": f"Summary generation failed: {str(e)}", "status": "failed"}
            )

        # Return success message with details
        return (
            html.Div(
                [
                    html.Div(
                        [
                            html.I(
                                className="fas fa-check-circle",
                                style={
                                    "color": "#10b981",
                                    "fontSize": "24px",
                                    "marginBottom": "8px",
                                },
                            ),
                            html.H5(
                                "✅ File uploaded successfully!",
                                style={"color": "#10b981", "margin": "0 0 12px 0"},
                            ),
                        ],
                        style={"textAlign": "center", "marginBottom": "16px"},
                    ),
                    html.Div(
                        [
                            html.P(
                                [html.Strong("📄 Name: "), name],
                                style={"margin": "4px 0"},
                            ),
                            html.P(
                                [html.Strong("🏢 Issuer: "), issuer],
                                style={"margin": "4px 0"},
                            ),
                            html.P(
                                [
                                    html.Strong("📅 Published: "),
                                    published_date.strftime("%B %d, %Y"),
                                ],
                                style={"margin": "4px 0"},
                            ),
                            html.P(
                                [
                                    html.Strong("📁 File size: "),
                                    f"{len(decoded) / 1024:.2f} KB",
                                ],
                                style={"margin": "4px 0"},
                            ),
                            html.P(
                                [
                                    html.Strong("🆔 Insight ID: "),
                                    html.Code(
                                        str(insight.id),
                                        style={
                                            "backgroundColor": "#374151",
                                            "padding": "2px 6px",
                                            "borderRadius": "4px",
                                        },
                                    ),
                                ],
                                style={"margin": "4px 0"},
                            ),
                        ],
                        style={
                            "backgroundColor": "rgba(16, 185, 129, 0.05)",
                            "padding": "12px",
                            "borderRadius": "8px",
                            "border": "1px solid rgba(16, 185, 129, 0.2)",
                        },
                    ),
                ],
                style={
                    "backgroundColor": "rgba(16, 185, 129, 0.1)",
                    "border": "1px solid rgba(16, 185, 129, 0.3)",
                    "borderRadius": "12px",
                    "padding": "20px",
                    "color": "#6ee7b7",
                },
            ),
            None,  # Clear the upload component
        )

    except Exception as e:
        logger.exception("Error processing PDF upload")
        return (
            html.Div(
                [
                    html.I(
                        className="fas fa-exclamation-triangle",
                        style={
                            "color": "#ef4444",
                            "fontSize": "24px",
                            "marginBottom": "8px",
                        },
                    ),
                    html.H5(
                        "❌ Error processing file",
                        style={"color": "#ef4444", "margin": "0 0 12px 0"},
                    ),
                    html.P(
                        str(e),
                        style={
                            "margin": "0",
                            "fontFamily": "monospace",
                            "fontSize": "14px",
                        },
                    ),
                ],
                style={
                    "backgroundColor": "rgba(239, 68, 68, 0.1)",
                    "border": "1px solid rgba(239, 68, 68, 0.3)",
                    "borderRadius": "12px",
                    "padding": "20px",
                    "color": "#fca5a5",
                    "textAlign": "center",
                },
            ),
            None,
        )


# Delete insight callback
@callback(
    Output("insights-container", "children", allow_duplicate=True),
    Input({"type": "delete-insight-button", "index": ALL}, "n_clicks"),
    State("insights-container", "children"),
    prevent_initial_call=True,
)
def delete_insight(n_clicks_list, current_children):
    """Handle insight deletion"""
    if not any(n_clicks_list):
        raise PreventUpdate

    try:
        # Find which button was clicked
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        insight_id = json.loads(button_id)["index"]

        # Delete from database
        insight_to_delete = Insight.find_one(Insight.id == ObjectId(insight_id)).run()
        if insight_to_delete:
            insight_to_delete.delete()

        # Show success message
        success_message = html.Div(
            [
                html.I(
                    className="fas fa-check-circle",
                    style={"color": "#10b981", "marginRight": "8px"},
                ),
                "Insight deleted successfully.",
            ],
            style={
                "backgroundColor": "rgba(16, 185, 129, 0.1)",
                "border": "1px solid rgba(16, 185, 129, 0.3)",
                "borderRadius": "8px",
                "padding": "15px",
                "color": "#6ee7b7",
                "textAlign": "center",
                "marginBottom": "15px",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
            },
        )

        # Reload insights
        insights = get_insights()
        insight_cards = []

        for insight in insights:
            insight_data = {
                "id": str(insight.id),
                "name": insight.name or "Untitled",
                "issuer": insight.issuer or "Unknown",
                "published_date": (
                    str(insight.published_date) if insight.published_date else ""
                ),
                "status": insight.status or "new",
                "summary": insight.summary or "",
            }

            card = create_insight_card(insight_data)
            insight_cards.append(card)

        return [success_message] + insight_cards

    except Exception as e:
        logger.error(f"Error deleting insight: {e}")

        error_message = html.Div(
            f"Delete failed: {str(e)}",
            style={
                "backgroundColor": "rgba(239, 68, 68, 0.1)",
                "border": "1px solid rgba(239, 68, 68, 0.3)",
                "borderRadius": "8px",
                "padding": "15px",
                "color": "#fca5a5",
                "textAlign": "center",
                "marginBottom": "15px",
            },
        )

        return [error_message] + (current_children if current_children else [])


# Modal display callback for enhanced summary viewing
@callback(
    Output("insight-modal", "is_open"),
    Output("modal-body-content", "children"),
    Input({"type": "insight-card-clickable", "index": ALL}, "n_clicks"),
    Input("close-modal", "n_clicks"),
    State("insight-modal", "is_open"),
    State("insights-data", "data"),
    prevent_initial_call=True,
)
def display_enhanced_modal(
    n_clicks_list: List[Optional[int]],
    close_n: Optional[int],
    is_open: bool,
    insights_data: List[str],
) -> Tuple[bool, Any]:
    """
    Enhanced modal display with improved summary viewing.
    Shows detailed insight summary with better formatting.
    """
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    triggered = ctx.triggered[0]

    # Handle close modal
    if "close-modal" in triggered["prop_id"]:
        return False, no_update

    # Handle card click to open modal
    if not any(n_clicks_list):
        raise PreventUpdate

    try:
        triggered_id = json.loads(triggered["prop_id"].split(".")[0])
        insight_id = triggered_id["index"]
    except Exception:
        return is_open, no_update

    # Get insight details from insights_data store (following wx pattern)
    insight_data = None
    for insight_json in insights_data or []:
        try:
            parsed_insight = json.loads(insight_json)
            if str(parsed_insight.get("id")) == str(insight_id):
                insight_data = parsed_insight
                break
        except Exception:
            continue

    # Fallback to database query if not found in store
    if not insight_data:
        try:
            insight = Insight.find_one(Insight.id == ObjectId(insight_id)).run()
            if not insight:
                return False, html.Div(
                    "Insight not found.",
                    style={
                        "color": "#ef4444",
                        "textAlign": "center",
                        "padding": "20px",
                    },
                )
            # Convert to dict format
            insight_data = {
                "id": str(insight.id),
                "name": insight.name or "Untitled",
                "issuer": insight.issuer or "Unknown",
                "published_date": (
                    str(insight.published_date) if insight.published_date else ""
                ),
                "summary": insight.summary or "No summary available.",
                "status": insight.status or "new",
            }
        except Exception as e:
            logger.error(f"Error fetching insight {insight_id}: {e}")
            return False, html.Div(
                "Error loading insight.",
                style={"color": "#ef4444", "textAlign": "center", "padding": "20px"},
            )

    # Format summary content with enhanced styling
    summary_content = html.Div(
        [
            # Header with insight details
            html.Div(
                [
                    html.H4(
                        insight_data.get("name", "Untitled"),
                        style={
                            "color": "#ffffff",
                            "marginBottom": "8px",
                            "borderBottom": "2px solid #3b82f6",
                            "paddingBottom": "8px",
                        },
                    ),
                    html.Div(
                        [
                            html.Span(
                                f"📅 {insight_data.get('published_date', 'Unknown Date')}",
                                style={
                                    "color": "#94a3b8",
                                    "marginRight": "16px",
                                    "fontSize": "14px",
                                },
                            ),
                            html.Span(
                                f"🏢 {insight_data.get('issuer', 'Unknown Issuer')}",
                                style={
                                    "color": "#3b82f6",
                                    "fontSize": "14px",
                                    "fontWeight": "500",
                                },
                            ),
                        ],
                        style={"marginBottom": "20px"},
                    ),
                ]
            ),
            # Summary content
            html.Div(
                [
                    html.H6(
                        "📋 Summary",
                        style={
                            "color": "#ffffff",
                            "marginBottom": "12px",
                            "fontSize": "16px",
                            "fontWeight": "600",
                        },
                    ),
                    html.Div(
                        insight_data.get("summary", "No summary available."),
                        style={
                            "color": "#e2e8f0",
                            "lineHeight": "1.7",
                            "fontSize": "15px",
                            "backgroundColor": "#1e293b",
                            "padding": "16px",
                            "borderRadius": "8px",
                            "border": "1px solid #475569",
                            "whiteSpace": "pre-wrap",
                        },
                    ),
                ]
            ),
            # Metadata section
            html.Div(
                [
                    html.Hr(style={"borderColor": "#475569", "margin": "20px 0"}),
                    html.H6(
                        "📊 Metadata",
                        style={
                            "color": "#ffffff",
                            "marginBottom": "12px",
                            "fontSize": "14px",
                            "fontWeight": "600",
                        },
                    ),
                    html.Div(
                        [
                            html.P(
                                [
                                    html.Strong("Status: "),
                                    html.Span(
                                        insight_data.get("status", "unknown").title(),
                                        style={
                                            "color": (
                                                "#10b981"
                                                if insight_data.get("status")
                                                == "completed"
                                                else (
                                                    "#f59e0b"
                                                    if insight_data.get("status")
                                                    == "processing"
                                                    else (
                                                        "#ef4444"
                                                        if insight_data.get("status")
                                                        == "failed"
                                                        else "#3b82f6"
                                                    )
                                                )
                                            ),
                                            "fontWeight": "500",
                                        },
                                    ),
                                ],
                                style={"margin": "4px 0", "fontSize": "13px"},
                            ),
                            html.P(
                                [
                                    html.Strong("Document ID: "),
                                    html.Code(
                                        str(insight_data.get("id", "unknown")),
                                        style={
                                            "backgroundColor": "#374151",
                                            "padding": "2px 6px",
                                            "borderRadius": "4px",
                                            "fontSize": "12px",
                                        },
                                    ),
                                ],
                                style={"margin": "4px 0", "fontSize": "13px"},
                            ),
                        ]
                    ),
                ]
            ),
        ]
    )

    return True, summary_content
