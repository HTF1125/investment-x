from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go
import json
import traceback
import concurrent.futures
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import utils
import textwrap
import sys

from ix.db.conn import get_session
from ix.db.models import CustomChart, User
from ix.api.dependencies import get_current_user
from ix.misc import get_logger

# Import process manager functions (ensure no circular deps)
try:
    from ix.api.routers.task import start_process, update_process, ProcessStatus
except ImportError:
    # Use dummy functions if import fails (e.g. during circular import check)
    def start_process(name, user_id=None):
        return "dummy"

    def update_process(pid, status=None, message=None, progress=None):
        pass

    class ProcessStatus:
        RUNNING = "running"
        COMPLETED = "completed"
        FAILED = "failed"


logger = get_logger(__name__)

router = APIRouter()

# --- Pydantic Models ---


class CustomChartCreate(BaseModel):
    name: str = "Untitled Analysis"
    code: str
    category: Optional[str] = "Personal"
    description: Optional[str] = None
    tags: List[str] = []
    export_pdf: bool = True


class CustomChartUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    export_pdf: Optional[bool] = None


class ExportPdfToggle(BaseModel):
    """Toggle export_pdf flag for one or more charts."""

    ids: List[str]
    export_pdf: bool


class CustomChartResponse(BaseModel):
    id: str
    name: Optional[str]
    code: str
    category: Optional[str]
    description: Optional[str]
    tags: List[str]
    figure: Optional[Dict[str, Any]]
    export_pdf: bool = True
    rank: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CodePreviewRequest(BaseModel):
    code: str


class ChartReorderItem(BaseModel):
    id: str


class ReorderRequest(BaseModel):
    items: List[ChartReorderItem]


class PDFExportRequest(BaseModel):
    items: List[str]  # List of IDs in order


# --- Helper Functions ---


def execute_custom_code(code: str):
    """
    Executes user-provided Python code.
    Expected contract: The code must define a 'fig' variable OR return a Plotly figure.
    WE ARE INJECTING 'df_plot' into the scope.
    """

    # 1. Define the safe/standard plotting helper
    def df_plot(df: pd.DataFrame, x=None, y=None, kind="line", title=None, **kwargs):
        """
        Generic plotter for DataFrames.
        """
        if kind == "line":
            return px.line(df, x=x, y=y, title=title, **kwargs)
        elif kind == "bar":
            return px.bar(df, x=x, y=y, title=title, **kwargs)
        elif kind == "scatter":
            return px.scatter(df, x=x, y=y, title=title, **kwargs)
        # Fallback
        return px.line(df, title=title)

    # 2. Prepare execution context
    import logging

    logger = logging.getLogger("backend")

    from ix.db.conn import conn
    from ix.db.query import (
        Series as OriginalSeries,
        MultiSeries,
        MonthEndOffset,
        StandardScalar,
        Offset,
        Resample,
        PctChange,
        Diff,
        MovingAverage,
        Clip,
        Ffill,
    )
    from ix.cht.style import (
        get_value_label,
        get_color,
        apply_academic_style,
        add_zero_line,
    )

    # Create a single session for all queries in this execution
    # This dramatically improves performance for charts with many tickers
    db_session = None
    try:
        from ix.db.conn import ensure_connection

        ensure_connection()
        db_session = conn.SessionLocal()
    except Exception as e:
        logger.error(f"Error creating DB session for custom chart: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database Error",
                "message": "Could not establish a database session for chart execution.",
                "traceback": str(e),
            },
        )

    # Optimized Series that reuses the session
    def Series_wrapped(code, freq=None, ccy=None):
        return OriginalSeries(code, freq=freq, ccy=ccy, session=db_session)

    # Pre-import common libraries used in Investment-X charts
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    global_scope = {
        "pd": pd,
        "px": px,
        "go": go,
        "make_subplots": make_subplots,
        "Series": Series_wrapped,
        "MultiSeries": MultiSeries,
        "MonthEndOffset": MonthEndOffset,
        "StandardScalar": StandardScalar,
        "Offset": Offset,
        "Resample": Resample,
        "PctChange": PctChange,
        "Diff": Diff,
        "MovingAverage": MovingAverage,
        "Clip": Clip,
        "Ffill": Ffill,
        "get_value_label": get_value_label,
        "get_color": get_color,
        "apply_academic_style": apply_academic_style,
        "apply_theme": apply_academic_style,  # Alias for easier usage
        "add_zero_line": add_zero_line,
        "df_plot": df_plot,
        "__name__": "__main__",
    }

    # 3. Import common modules for convenience
    try:
        import numpy as np

        global_scope["np"] = np
    except ImportError:
        pass

    try:
        from ix import cht

        global_scope["cht"] = cht
    except ImportError:
        pass

    # 4. Execute
    try:
        # Wrap in a function to allow 'return' statements
        # or just exec.
        # Use single scope for globals/locals to ensure function closures work as expected
        logger.info("Starting exec() for custom chart code...")

        # Enable shared session context for imports
        from ix.db.conn import custom_chart_session

        token = custom_chart_session.set(db_session)
        try:
            exec(code, global_scope)
        finally:
            custom_chart_session.reset(token)

        logger.info("exec() completed successfully.")

        # 5. Extract Figure from the modified scope
        # Check if 'fig' variable is defined
        if "fig" in global_scope:
            logger.info("Found 'fig' variable in scope.")
            fig_result = global_scope["fig"]
        else:
            # Check for any go.Figure in the scope if 'fig' is missing
            fig_result = None
            for key, value in global_scope.items():
                if isinstance(value, go.Figure):
                    logger.info(f"Using alternative figure found in scope: {key}")
                    fig_result = value
                    break

            if fig_result is None:
                logger.error("No figure found in scope after execution.")
                raise ValueError(
                    "The code must define a variable named 'fig' containing the Plotly figure."
                )
        return fig_result

    except BaseException as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Error executing custom chart code: {e}")
            logger.error(traceback.format_exc())

            # Determine error details
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb = traceback.format_exception(exc_type, exc_value, exc_traceback)

            # Provide a more descriptive error message to the frontend as a dict
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Execution Error",
                    "message": str(e),
                    "traceback": "".join(tb),
                },
            )
        else:
            raise e
    finally:
        if db_session:
            db_session.close()
            logger.info("Custom chart DB session closed.")


def render_chart_image(figure_data: Dict[str, Any]) -> Optional[bytes]:
    """Helper to render a signle chart figure to PNG bytes."""
    try:
        # Optimization: Create Figure directly from dict instead of round-tripping JSON
        fig = go.Figure(figure_data)

        # Convert to image bytes (CPU intensive)
        img_bytes = fig.to_image(format="png", width=1000, height=550, scale=2)
        return img_bytes
    except Exception as e:
        logger.error(f"Error rendering chart image: {e}")
        return None


def generate_pdf_buffer(charts: List[CustomChart]) -> BytesIO:
    buffer = BytesIO()
    # Use landscape for charts usually
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)

    # 1. Pre-fetch/Filter valid charts
    valid_charts = []
    for chart in charts:
        if chart.figure:
            valid_charts.append(chart)

    if not valid_charts:
        return buffer

    # 2. Render images in parallel
    # Use ThreadPoolExecutor to run IO/C-extension bound tasks in parallel
    # Kaleido (if used) runs in a separate process, so threads work well here.
    chart_images = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        # Submit all render tasks
        future_to_index = {
            executor.submit(render_chart_image, chart.figure): i
            for i, chart in enumerate(valid_charts)
        }

        # Initialize results array with None
        results = [None] * len(valid_charts)

        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_index):
            index = future_to_index[future]
            try:
                data = future.result()
                results[index] = data
            except Exception as e:
                logger.error(
                    f"Parallel rendering failed for chart at index {index}: {e}"
                )

    # 3. Construct PDF page by page
    for i, chart in enumerate(valid_charts):
        try:
            # 1. Render title
            c.setFont("Helvetica-Bold", 18)
            title = chart.name or "Untitled Analysis"
            c.drawString(50, height - 50, title)

            # 2. Render meta
            c.setFont("Helvetica", 10)
            meta = f"Category: {chart.category} | Updated: {chart.updated_at.strftime('%Y-%m-%d')}"
            c.drawString(50, height - 70, meta)

            # 3. Render description (wrapped)
            if chart.description:
                c.setFont("Helvetica-Oblique", 10)
                desc_lines = textwrap.wrap(chart.description, width=120)
                y_desc = height - 90
                for line in desc_lines[:3]:  # Limit lines
                    c.drawString(50, y_desc, line)
                    y_desc -= 12

            # 4. Render Chart Image
            img_bytes = results[i]

            if img_bytes:
                img_buffer = BytesIO(img_bytes)
                img = utils.ImageReader(img_buffer)

                # Draw image
                # Provide space below header
                c.drawImage(
                    img,
                    40,
                    50,
                    width=width - 80,
                    height=height - 200,
                    preserveAspectRatio=True,
                )
            else:
                # Fallback for failed render
                c.setFont("Helvetica", 12)
                c.drawString(50, height / 2, "Error: Could not render chart image.")

            c.showPage()

        except Exception as e:
            logger.error(f"Failed to add chart {chart.id} page to PDF: {e}")
            # Ensure we don't break the whole PDF generation for one page error if possible
            # But usually showPage() resets context.
            continue

    c.save()
    buffer.seek(0)
    return buffer


# --- Endpoints ---


@router.post("/custom/preview")
def preview_custom_chart(
    request: CodePreviewRequest, current_user: User = Depends(get_current_user)
):
    """
    Executes code and returns the figure JSON without saving.
    """
    import time
    from fastapi.responses import Response

    start_time = time.time()
    logger.info(f"Previewing custom chart. Code length: {len(request.code)}")
    try:
        fig = execute_custom_code(request.code)
    except BaseException as e:
        if isinstance(e, HTTPException):
            raise e

        logger.error(f"Execution failed in preview: {e}")
        # Determine error details
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb = traceback.format_exception(exc_type, exc_value, exc_traceback)

        # Return as 400 Bad Request with details
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Execution Error",
                "message": str(e),
                "traceback": "".join(tb),
            },
        )

    try:
        logger.info("Serializing figure to JSON string (Plotly native)...")
        json_str = pio.to_json(fig)

        duration = time.time() - start_time
        logger.info(
            f"Serialization complete. Duration: {duration:.2f}s. Response size: {len(json_str)} bytes"
        )

        # Return directly as JSON response to avoid double serialization
        return Response(content=json_str, media_type="application/json")
    except Exception as e:
        logger.error(f"Failed to serialize figure: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Failed to serialize figure to JSON: {str(e)}"
        )


@router.post("/custom", response_model=CustomChartResponse)
def create_custom_chart(
    chart_data: CustomChartCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new custom chart."""
    logger.info(f"Creating new chart with name: '{chart_data.name}'")

    # Optional: Validate code by running it once?
    # Let's render it to get the initial figure cache
    try:
        fig = execute_custom_code(chart_data.code)
        figure_json = json.loads(pio.to_json(fig))
    except Exception:
        figure_json = None

    # Determine next rank
    max_rank = db.query(func.max(CustomChart.rank)).scalar() or 0
    next_rank = max_rank + 1

    new_chart = CustomChart(
        name=chart_data.name,
        code=chart_data.code,
        category=chart_data.category,
        description=chart_data.description,
        tags=chart_data.tags,
        figure=figure_json,
        export_pdf=chart_data.export_pdf,
        rank=next_rank,
    )

    db.add(new_chart)
    db.commit()
    db.refresh(new_chart)
    logger.info(f"New chart created with ID: {new_chart.id}, Name: '{new_chart.name}'")
    return new_chart


@router.get("/custom", response_model=List[CustomChartResponse])
def list_custom_charts(
    db: Session = Depends(get_session), current_user: User = Depends(get_current_user)
):
    """List all custom charts (shared across admins)."""
    return (
        db.query(CustomChart)
        .order_by(CustomChart.rank.asc(), CustomChart.created_at.desc())
        .all()
    )


@router.put("/custom/reorder")
def reorder_custom_charts(
    order_data: ReorderRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Reorder custom charts based on list of IDs."""

    ids = [item.id for item in order_data.items]

    # Fetch all relevant charts to update
    charts = db.query(CustomChart).filter(CustomChart.id.in_(ids)).all()
    chart_map = {str(c.id): c for c in charts}

    for index, chart_id in enumerate(ids):
        if str(chart_id) in chart_map:
            chart_map[str(chart_id)].rank = index

    db.commit()
    return {"message": "Reordered successfully"}


@router.patch("/custom/export-pdf")
def toggle_export_pdf(
    data: ExportPdfToggle,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Toggle the export_pdf flag for one or more charts."""
    db.query(CustomChart).filter(CustomChart.id.in_(data.ids)).update(
        {CustomChart.export_pdf: data.export_pdf}, synchronize_session="fetch"
    )
    db.commit()
    return {"message": f"Updated {len(data.ids)} chart(s)"}


@router.post("/custom/pdf")
def export_custom_charts_pdf(
    request: PDFExportRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Generate a PDF of charts marked for export, in rank order.

    If request.items is provided, use that order.
    If request.items is empty, auto-select all charts with export_pdf=True.
    """
    user_identifier = getattr(current_user, "email", "unknown")
    pid = start_process("Export PDF Report", user_id=user_identifier)

    try:
        if request.items:
            # Explicit list — preserve caller order
            charts = (
                db.query(CustomChart).filter(CustomChart.id.in_(request.items)).all()
            )
            chart_map = {str(c.id): c for c in charts}
            ordered_charts = [
                chart_map[cid] for cid in request.items if cid in chart_map
            ]
        else:
            # Auto-select all charts flagged for export
            ordered_charts = (
                db.query(CustomChart)
                .filter(CustomChart.export_pdf == True)
                .order_by(CustomChart.rank.asc())
                .all()
            )

        if not ordered_charts:
            update_process(pid, ProcessStatus.FAILED, "No charts found")
            raise HTTPException(
                status_code=404, detail="No charts marked for PDF export"
            )

        pdf_buffer = generate_pdf_buffer(ordered_charts)

        filename = f"InvestmentX_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
        update_process(pid, ProcessStatus.COMPLETED, "PDF Generated")

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        logger.error(f"PDF Export failed: {e}")
        update_process(pid, ProcessStatus.FAILED, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/custom/{chart_id}", response_model=CustomChartResponse)
def get_custom_chart(
    chart_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get a specific custom chart."""
    chart = db.query(CustomChart).filter(CustomChart.id == chart_id).first()

    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    return chart


@router.put("/custom/{chart_id}", response_model=CustomChartResponse)
def update_custom_chart(
    chart_id: str,
    update_data: CustomChartUpdate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update a custom chart."""
    logger.info(f"Updating chart {chart_id}. Received name: '{update_data.name}'")
    chart = db.query(CustomChart).filter(CustomChart.id == chart_id).first()

    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")

    # Update fields if provided
    if update_data.name is not None:
        logger.info(f"Setting chart name from '{chart.name}' to '{update_data.name}'")
        chart.name = update_data.name
    if update_data.category is not None:
        chart.category = update_data.category
    if update_data.description is not None:
        chart.description = update_data.description
    if update_data.tags is not None:
        chart.tags = update_data.tags
    if update_data.export_pdf is not None:
        chart.export_pdf = update_data.export_pdf

    # If code changes, re-render
    if update_data.code is not None:
        chart.code = update_data.code
        try:
            fig = execute_custom_code(update_data.code)
            chart.figure = json.loads(pio.to_json(fig))
        except Exception:
            pass

    db.commit()
    db.refresh(chart)
    logger.info(
        f"Chart {chart.id} updated successfully. Final name in DB: '{chart.name}'"
    )
    return chart


@router.delete("/custom/{chart_id}")
def delete_custom_chart(
    chart_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Delete a custom chart."""
    chart = db.query(CustomChart).filter(CustomChart.id == chart_id).first()

    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")

    db.delete(chart)
    db.commit()
    return {"message": "Chart deleted successfully"}
