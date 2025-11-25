"""PDF upload callback."""

import base64
from datetime import datetime, date
from typing import Any, Optional, Tuple

from dash import html, callback, Input, Output, State, no_update
from dash.exceptions import PreventUpdate
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from ix.db.conn import Session
from ix.db.models import Insights
from ix.misc.terminal import get_logger
from ix.misc import PDFSummarizer, Settings

logger = get_logger(__name__)


@callback(
    Output("output-pdf-upload", "children", allow_duplicate=True),
    Output("upload-pdf-dragdrop", "contents", allow_duplicate=True),
    Input("upload-pdf-dragdrop", "contents"),
    State("upload-pdf-dragdrop", "filename"),
    State("upload-pdf-dragdrop", "last_modified"),
    prevent_initial_call=True,
)
def handle_pdf_upload(
    dragdrop_contents: Optional[Any],
    dragdrop_filename: Optional[Any],
    dragdrop_last_modified: Optional[Any],
) -> Tuple[Any, Optional[str]]:
    """Handle PDF upload with validation and AI summarization (drag-drop only)."""
    # Check if upload was triggered
    if dragdrop_contents is None or dragdrop_filename is None:
        raise PreventUpdate

    contents = dragdrop_contents
    filename = dragdrop_filename
    last_modified = dragdrop_last_modified

    if contents is None or filename is None:
        raise PreventUpdate

    contents_list = contents if isinstance(contents, list) else [contents]
    filenames_list = filename if isinstance(filename, list) else [filename]
    modified_list = (
        last_modified if isinstance(last_modified, list)
        else [last_modified] * len(contents_list)
    )

    def process_file(content_item: str, file_name: str, modified_item: Optional[float]) -> Tuple[html.Div, bool]:
        """Process a single PDF file."""
        try:
            if modified_item is None:
                raise ValueError("Missing last modified timestamp.")

            content_type, content_string = content_item.split(",", 1)
            decoded = base64.b64decode(content_string)

            if not file_name.lower().endswith(".pdf"):
                return create_error_message(f"{file_name}: Only PDF files are allowed."), False

            if not decoded.startswith(b"%PDF-"):
                return create_error_message(f"{file_name}: Invalid PDF format."), False

            # Parse filename metadata
            try:
                published_date_str, issuer, name = file_name.rsplit("_", 2)
                name = name.rsplit(".", 1)[0]
                published_date = datetime.strptime(published_date_str, "%Y%m%d").date()
                needs_metadata = False
            except ValueError:
                needs_metadata = True
                name = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
                published_date = date.today()
                issuer = "Unnamed"

            # Save to database
            with Session() as session:
                insight = Insights(
                    published_date=published_date,
                    issuer=issuer or "Unnamed",
                    name=name or "Unnamed",
                    status="processing",
                    pdf_content=decoded,
                )
                session.add(insight)
                session.flush()

                # Generate AI summary
                try:
                    if hasattr(Settings, "openai_secret_key") and Settings.openai_secret_key:
                        summarizer = PDFSummarizer(Settings.openai_secret_key)
                        summary_text = summarizer.process_insights(decoded)
                        insight.summary = summary_text
                        insight.status = "completed"
                    else:
                        insight.status = "completed"
                except Exception as e:
                    logger.error(f"Error generating summary: {e}")
                    insight.status = "failed"

                session.commit()
                insight_id = str(insight.id)

            success_card = create_success_message(file_name, name, issuer, published_date, insight_id, len(decoded))
            if needs_metadata:
                warning = create_warning_message(file_name)
                return html.Div([success_card, warning]), True

            return success_card, True

        except Exception as e:
            logger.exception(f"Error processing {file_name}")
            return create_error_message(f"Error: {str(e)}"), False

    results = [
        process_file(content_item, file_name, modified_item)
        for content_item, file_name, modified_item in zip(contents_list, filenames_list, modified_list)
    ]

    message_cards = [card for card, _ in results]
    success_count = sum(1 for _, success in results if success)
    total_files = len(results)

    summary = create_upload_summary(success_count, total_files)

    # Clear upload component
    return html.Div([summary] + message_cards, style={"display": "grid", "gap": "20px"}), None


def create_error_message(message: str) -> html.Div:
    """Create error message component."""
    return html.Div(
        [
            html.I(className="fas fa-exclamation-triangle", style={"color": "#ef4444", "marginRight": "8px"}),
            message,
        ],
        style={
            "backgroundColor": "rgba(239, 68, 68, 0.1)",
            "border": "1px solid rgba(239, 68, 68, 0.3)",
            "borderRadius": "8px",
            "padding": "15px",
            "color": "#fca5a5",
            "display": "flex",
            "alignItems": "center",
        },
    )


def create_success_message(file_name: str, name: str, issuer: str, published_date: date, insight_id: str, file_size: int) -> html.Div:
    """Create success message component."""
    return html.Div(
        [
            html.I(className="fas fa-check-circle", style={"color": "#10b981", "fontSize": "24px"}),
            html.H5(f"✅ {file_name} uploaded successfully!", style={"color": "#10b981"}),
            html.Div(
                [
                    html.P([html.Strong("📄 Name: "), name or "Unnamed"]),
                    html.P([html.Strong("🏢 Issuer: "), issuer or "Unnamed"]),
                    html.P([html.Strong("📅 Published: "), published_date.strftime("%B %d, %Y")]),
                    html.P([html.Strong("📁 Size: "), f"{file_size / 1024:.2f} KB"]),
                ],
                style={
                    "backgroundColor": "rgba(16, 185, 129, 0.05)",
                    "padding": "12px",
                    "borderRadius": "8px",
                    "marginTop": "12px",
                },
            ),
        ],
        style={
            "backgroundColor": "rgba(16, 185, 129, 0.1)",
            "border": "1px solid rgba(16, 185, 129, 0.3)",
            "borderRadius": "12px",
            "padding": "20px",
            "textAlign": "center",
        },
    )


def create_warning_message(file_name: str) -> html.Div:
    """Create warning message for incorrect filename format."""
    return html.Div(
        [
            html.I(className="fas fa-exclamation-circle", style={"color": "#f59e0b"}),
            html.P(
                f"Filename '{file_name}' doesn't match expected format (YYYYMMDD_issuer_title.pdf). "
                "File uploaded with default values. You can edit metadata later.",
                style={"color": "#fde68a", "margin": 0},
            ),
        ],
        style={
            "backgroundColor": "rgba(245, 158, 11, 0.1)",
            "border": "1px solid rgba(245, 158, 11, 0.3)",
            "borderRadius": "8px",
            "padding": "12px",
            "marginTop": "12px",
            "display": "flex",
            "alignItems": "center",
            "gap": "8px",
        },
    )


def create_upload_summary(success_count: int, total_files: int) -> dmc.Paper:
    """Create upload summary panel."""
    progress = int((success_count / total_files) * 100) if total_files > 0 else 0
    color = "teal" if success_count == total_files else "yellow" if success_count > 0 else "red"
    status = "All successful" if success_count == total_files else f"{success_count}/{total_files} successful"

    return dmc.Paper(
        [
            dmc.Group(
                [
                    DashIconify(icon="carbon:time", width=24, color="#38bdf8"),
                    dmc.Stack(
                        [
                            dmc.Text("Processing complete", fw=600, size="sm"),
                            dmc.Text(status, size="xs", c="gray"),
                        ],
                        gap=0,
                    ),
                ],
                gap="md",
            ),
            dmc.Progress(value=progress, color=color, size="sm", mt="sm"),
        ],
        radius="md",
        withBorder=True,
        p="md",
        style={"backgroundColor": "#0f172a"},
    )
